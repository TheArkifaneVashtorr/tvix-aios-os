# Integration checks for lib/patchSeries.nix (PL2).
#
#   eval     — patches/patch-series-eval: the good series, applied through
#              applySeries, yields exactly `hello, world\nsecond\n` and preserves
#              the upstream package's own postPatch; an empty series returns the
#              package derivation itself (Interface 6).
#   negative — patches/patch-series-negative: the duplicate-number and
#              stray-file refusals fire at eval time, a non-applying patch fails
#              under the `bash -eu` runner, and the good series applies under
#              that same runner (Interface 7, the control in arm (d)).
{
  pkgs,
  patchSeries,
}:

let
  fixture = ../fixtures/patch-series;
  srcDir = fixture + "/src";
  good = fixture + "/good";
  badDup = fixture + "/bad-dup";
  badApply = fixture + "/bad-apply";
  badStray = fixture + "/bad-stray";
  empty = fixture + "/empty";

  # The fixture source package: carries hello.txt ("hello\n") and an upstream
  # postPatch that writes a marker. applySeries must preserve the upstream
  # postPatch while appending the series after it (M5's probe).
  src = pkgs.stdenvNoCC.mkDerivation {
    name = "patch-series-src";
    src = srcDir;
    postPatch = "echo pre > marker\n";
    installPhase = ''
      mkdir -p $out
      cp hello.txt $out/
      if [ -f marker ]; then
        cp marker $out/marker
      fi
    '';
  };

  # The same source with NO postPatch at all: the empty-series guard's probe.
  # Dropping Interface 4's `if s == [ ] then pkg` branch adds `postPatch = ""`
  # to this package and changes its drv (A6), which the eval check detects.
  plainSrc = pkgs.stdenvNoCC.mkDerivation {
    name = "patch-series-plain-src";
    src = srcDir;
    installPhase = ''
      mkdir -p $out
      cp hello.txt $out/
    '';
  };

  applied = patchSeries.applySeries good src;

  eval = pkgs.runCommand "patch-series-eval" { } ''
    wanted=$(mktemp)
    printf 'hello, world\nsecond\n' > "$wanted"
    actual=$(cat ${applied}/hello.txt)
    expected=$(cat "$wanted")
    if ! cmp -s ${applied}/hello.txt "$wanted"; then
      echo "patch-series-eval: got '$actual', expected '$expected'" >&2
      exit 1
    fi
    if [ ! -f ${applied}/marker ]; then
      echo "patch-series-eval: upstream postPatch was dropped" >&2
      exit 1
    fi
    emptyApplied=${patchSeries.applySeries empty plainSrc}
    if [ "$emptyApplied" != "${plainSrc}" ]; then
      echo "patch-series-eval: an empty series changed the derivation" >&2
      exit 1
    fi
    touch $out
  '';

  badScript = pkgs.writeText "patch-series-bad-apply-postPatch" (
    patchSeries.renderPostPatch badApply
  );
  goodScript = pkgs.writeText "patch-series-good-postPatch" (patchSeries.renderPostPatch good);

  negative =
    let
      dup = builtins.tryEval (patchSeries.readSeries badDup);
      stray = builtins.tryEval (patchSeries.readSeries badStray);
    in
    if dup.success then
      throw "patch-series-negative: bad-dup was accepted"
    else if stray.success then
      throw "patch-series-negative: bad-stray was accepted"
    else
      pkgs.runCommand "patch-series-negative" { } ''
        set -u

        # (c) the non-applying series must fail under bash -eu with the
        # expected patch diagnostic against a copy of src.
        d=$(mktemp -d)
        cp ${srcDir}/hello.txt "$d/hello.txt"
        chmod u+w "$d/hello.txt"
        if ( cd "$d" && bash -eu ${badScript} ) >"$d/log" 2>&1; then
          echo "patch-series-negative: bad-apply was accepted" >&2
          exit 1
        fi
        if ! grep -Eq "Hunk #1 FAILED|find file to patch" "$d/log"; then
          echo "patch-series-negative: bad-apply failed with unexpected output" >&2
          cat "$d/log" >&2
          exit 1
        fi
        rm -rf "$d"

        # (d) control: the good series applies under the same runner.
        d=$(mktemp -d)
        cp ${srcDir}/hello.txt "$d/hello.txt"
        chmod u+w "$d/hello.txt"
        if ! ( cd "$d" && bash -eu ${goodScript} ) >"$d/log" 2>&1; then
          echo "patch-series-negative: good was rejected under the same runner" >&2
          cat "$d/log" >&2
          exit 1
        fi
        rm -rf "$d"

        touch $out
      '';
in
{
  inherit eval negative;
}
