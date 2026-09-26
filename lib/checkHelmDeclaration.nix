# A declaration's offers checked against a flake's real outputs at eval time.
# `helmDeclarationErrors` returns the list of rule violations; an empty list is
# a valid declaration. `checkHelmDeclaration` turns that into a passing
# derivation or a throw naming every violation.
{
  pkgs,
  lib,
  system ? "x86_64-linux",
}:

let
  requiredFields = [
    "name"
    "summary"
    "why"
    "created"
    "owner"
    "writtenAgainst"
    "state"
    "updated"
    "offers"
    "card"
  ];
  stringFields = [
    "name"
    "summary"
    "why"
    "owner"
    "state"
  ];
  offerFields = [
    "profiles"
    "run"
    "seats"
  ];
  runEntryFields = [
    "label"
    "command"
  ];
  cardFields = [
    "blocks"
    "notes"
  ];
  allowedSeats = [
    "claude"
    "deepseek"
  ];
  allowedBlocks = [
    "why"
    "state"
    "do"
    "notes"
    "cost"
    "lastRun"
    "terminal"
  ];

  dateRe = "[0-9]{4}-[0-9]{2}-[0-9]{2}";
  hexRe = "^[0-9a-f]{40}$";

  helmDeclarationErrors =
    declaration: flakeOutputs:
    let
      d = declaration;
      fields = builtins.attrNames d;

      nixosModules = flakeOutputs.nixosModules or { };
      nixosConfigurations = flakeOutputs.nixosConfigurations or { };
      packages = flakeOutputs.packages.${system} or { };
      apps = flakeOutputs.apps.${system} or { };
      packageNames = builtins.attrNames packages;
      appNames = builtins.attrNames apps;

      # F1: every required field present.
      f1 = map (f: "missing field ${f}") (lib.filter (f: !(builtins.hasAttr f d)) requiredFields);

      # F2: nothing beyond the required fields.
      f2 = map (f: "unknown field ${f}") (lib.filter (f: !(lib.elem f requiredFields)) fields);

      # F3: the string fields must be strings.
      f3 = lib.concatMap (
        f: if builtins.hasAttr f d && !(builtins.isString d.${f}) then [ "${f} must be a string" ] else [ ]
      ) stringFields;

      # F4: name is a lowercase-dash name.
      f4 =
        if
          builtins.hasAttr "name" d
          && builtins.isString d.name
          && builtins.match "^[a-z][a-z0-9-]{0,31}$" d.name == null
        then
          [ "name must match ^[a-z][a-z0-9-]{0,31}$" ]
        else
          [ ];

      # F5: created/updated are YYYY-MM-DD.
      dateOk = v: builtins.isString v && builtins.match dateRe v != null;
      f5 =
        (
          if builtins.hasAttr "created" d && !(dateOk d.created) then
            [ "created must be YYYY-MM-DD" ]
          else
            [ ]
        )
        ++ (
          if builtins.hasAttr "updated" d && !(dateOk d.updated) then
            [ "updated must be YYYY-MM-DD" ]
          else
            [ ]
        );

      # F6: writtenAgainst is null or a 40-hex commit.
      writtenOk = v: v == null || (builtins.isString v && builtins.match hexRe v != null);
      f6 =
        if builtins.hasAttr "writtenAgainst" d && !(writtenOk d.writtenAgainst) then
          [ "writtenAgainst must be null or a 40-hex commit" ]
        else
          [ ];

      hasOffers = builtins.hasAttr "offers" d && builtins.isAttrs d.offers;
      hasCard = builtins.hasAttr "card" d && builtins.isAttrs d.card;

      # O1: offers carries exactly profiles, run, seats.
      o1 =
        if !hasOffers then
          [ ]
        else
          let
            ofields = builtins.attrNames d.offers;
            missing = lib.filter (f: !(builtins.hasAttr f d.offers)) offerFields;
            extra = lib.filter (f: !(lib.elem f offerFields)) ofields;
          in
          if missing == [ ] && extra == [ ] then [ ] else [ "offers carries exactly profiles, run, seats" ];

      # O2: each profile name is exported by the flake.
      o2 =
        if !hasOffers || !(builtins.hasAttr "profiles" d.offers) then
          [ ]
        else
          lib.concatMap (
            p:
            if
              lib.elem p (builtins.attrNames nixosModules) || lib.elem p (builtins.attrNames nixosConfigurations)
            then
              [ ]
            else
              [
                "offers.profiles names ${p}, which the flake does not export (nixosModules or nixosConfigurations)"
              ]
          ) d.offers.profiles;

      # O3: each run entry carries exactly label and command; a non-empty
      # command whose first token is neither a package nor an app is refused.
      checkRunEntry =
        entry:
        let
          isAttrs = builtins.isAttrs entry;
          entryFields = if isAttrs then builtins.attrNames entry else [ ];
          missing = lib.filter (f: !(builtins.hasAttr f entry)) runEntryFields;
          extra = lib.filter (f: !(lib.elem f runEntryFields)) entryFields;
          label =
            if isAttrs && builtins.hasAttr "label" entry && builtins.isString entry.label then
              entry.label
            else
              "?";
          command =
            if isAttrs && builtins.hasAttr "command" entry && builtins.isString entry.command then
              entry.command
            else
              "";
          tokMatch = builtins.match "[[:space:]]*([^[:space:]]+).*" command;
          tok = if tokMatch == null then "" else builtins.elemAt tokMatch 0;
        in
        (
          if missing != [ ] || extra != [ ] then
            [ "offers.run entries carry exactly label and command" ]
          else
            [ ]
        )
        ++ (
          if command == "" then
            [ "offers.run \"${label}\" has an empty command" ]
          else if tok == "" || lib.elem tok packageNames || lib.elem tok appNames then
            [ ]
          else
            [ "offers.run \"${label}\" runs ${tok}, which is not a package or app of the flake" ]
        );
      o3 =
        if !hasOffers || !(builtins.hasAttr "run" d.offers) then
          [ ]
        else
          lib.concatMap checkRunEntry d.offers.run;

      # O4: seats are claude/deepseek without repeats.
      o4 =
        if !hasOffers || !(builtins.hasAttr "seats" d.offers) then
          [ ]
        else
          let
            ss = d.offers.seats;
            holds = lib.concatMap (
              s:
              if lib.elem s allowedSeats then [ ] else [ "offers.seats holds ${s}, not one of claude, deepseek" ]
            ) ss;
            repeats = lib.unique (
              lib.concatMap (
                s: if lib.length (lib.filter (x: x == s) ss) > 1 then [ "offers.seats repeats ${s}" ] else [ ]
              ) ss
            );
          in
          holds ++ repeats;

      # C1: card carries exactly blocks, notes.
      c1 =
        if !hasCard then
          [ ]
        else
          let
            cfields = builtins.attrNames d.card;
            missing = lib.filter (f: !(builtins.hasAttr f d.card)) cardFields;
            extra = lib.filter (f: !(lib.elem f cardFields)) cfields;
          in
          if missing == [ ] && extra == [ ] then [ ] else [ "card carries exactly blocks, notes" ];

      # C2: each block is known and not repeated.
      c2 =
        if !hasCard || !(builtins.hasAttr "blocks" d.card) then
          [ ]
        else
          lib.concatMap (
            b:
            if !(lib.elem b allowedBlocks) then
              [
                "card.blocks holds ${b}, not one of why, state, do, notes, cost, lastRun, terminal"
              ]
            else if lib.length (lib.filter (x: x == b) d.card.blocks) > 1 then
              [ "card.blocks repeats ${b}" ]
            else
              [ ]
          ) d.card.blocks;

      # C3: card.notes is a string.
      c3 =
        if !hasCard || !(builtins.hasAttr "notes" d.card) || builtins.isString d.card.notes then
          [ ]
        else
          [ "card.notes must be a string" ];
    in
    f1 ++ f2 ++ f3 ++ f4 ++ f5 ++ f6 ++ o1 ++ o2 ++ o3 ++ o4 ++ c1 ++ c2 ++ c3;

  checkHelmDeclaration =
    declaration: flakeOutputs:
    let
      errs = helmDeclarationErrors declaration flakeOutputs;
      name = declaration.name or "?";
    in
    if errs == [ ] then
      pkgs.runCommand "helm-declaration-${name}-ok" { } "touch $out"
    else
      throw "helm declaration ${name}: ${lib.concatStringsSep "; " errs}";
in
{
  inherit helmDeclarationErrors checkHelmDeclaration;
}
