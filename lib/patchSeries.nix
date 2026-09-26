# A numbered patch series applied in postPatch (decision 37a): patches live at
# `patches/<pkg>/NNNN-*.patch`, one per vendored upstream, and `applySeries`
# appends their `patch -p1` calls to a package's `postPatch` in sorted order.
#
# Interfaces (PL2):
#   1. `readSeries dir` — the paths of `dir`'s regular files matching
#      `^[0-9]{4}-.*\.patch$`, sorted by name.
#   2. `readSeries` throws on a duplicated `NNNN` and on any entry that is not
#      a patch or `README.md` (subdirectories included).
#   3. `renderPostPatch dir` — the `patch -p1 -F 0 --no-backup-if-mismatch`
#      shell text, one line per patch, no `|| true` (a re-applied patch already
#      exits non-zero, A30). `-F 0` pins ordering: GNU patch's default fuzz of
#      two lets a later patch apply without the earlier one's context, silently
#      — the exact thing decision 37a forbids.
#   4. `applySeries dir pkg` — appends the series to `pkg.postPatch`, preserving
#      any upstream `postPatch`; an empty series returns `pkg` itself so the drv
#      is unchanged (adding `postPatch = ""` to a package that has none would
#      change its drv, A6).
{
  lib,
}:

rec {
  readSeries =
    dir:
    let
      entries = builtins.readDir dir;
      isPatch = n: t: t == "regular" && builtins.match "^[0-9]{4}-.*\\.patch$" n != null;
      patchNames = builtins.attrNames (lib.filterAttrs isPatch entries);
      numOf = n: builtins.substring 0 4 n;
      # Anything neither a patch nor README.md is stray: a plain text file or a
      # subdirectory (readDir reports a directory as type "directory") both land
      # here and refuse.
      isStray = n: t: !(isPatch n t) && n != "README.md";
      strays = builtins.attrNames (lib.filterAttrs isStray entries);
      dupNums = lib.unique (
        lib.filter (n: lib.length (lib.filter (x: numOf x == n) patchNames) > 1) (map numOf patchNames)
      );
    in
    if strays != [ ] then
      throw "patchSeries: ${dir}: stray file ${builtins.head strays} (only NNNN-*.patch and README.md are allowed)"
    else if dupNums != [ ] then
      let
        n = builtins.head dupNums;
      in
      throw "patchSeries: ${dir}: duplicate number ${n} (${
        builtins.concatStringsSep ", " (lib.filter (p: numOf p == n) (lib.sort lib.lessThan patchNames))
      })"
    else
      map (name: dir + ("/" + name)) (lib.sort lib.lessThan patchNames);

  renderPostPatch =
    dir: lib.concatMapStrings (p: "patch -p1 -F 0 --no-backup-if-mismatch < ${p}\n") (readSeries dir);

  applySeries =
    dir: pkg:
    let
      s = readSeries dir;
    in
    if s == [ ] then
      pkg
    else
      pkg.overrideAttrs (old: {
        postPatch = (old.postPatch or "") + renderPostPatch dir;
      });
}
