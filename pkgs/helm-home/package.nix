# Helm Home (HH1): the raise-key probe package.
#
# A GTK4 application wrapped so that `helm-home-probe --self-check` can run
# headless (the installCheckPhase does exactly that). The entry point is a
# makeWrapper around the stdlib+gi interpreter: it adds the package's own
# lib dir (for probe.py/portal.py/probe_result.py) and pkgs/evidence (for
# HH10's `refresh.py`, which does `import evidence`) to PYTHONPATH, and
# spreads the wrapGAppsHook4 wrapper args so the GI typelibs
# (GTK 4 / libadwaita / vte / AT-SPI) resolve at runtime. `dontWrapGApps`
# keeps the hook from auto-wrapping an interpreter we wrap by hand.
#
# Two subtleties make the wrap happen in postFixup rather than installPhase:
#
# 1. The interpreter is `python.withPackages` so pygobject3 (the `gi` module)
#    and pyatspi land on the *runtime* PYTHONPATH. A bare
#    `python3Packages.python.interpreter` would only find `gi` during the
#    build (where the propagated inputs leak onto PYTHONPATH) and fail
#    headless with `ModuleNotFoundError: No module named 'gi'`.
#
# 2. `gappsWrapperArgs` is only fully populated by `gappsWrapperArgsHook`,
#    which runs in the preFixup phase — *after* installPhase. Wrapping in
#    installPhase captures an empty GI_TYPELIB_PATH, so the entry point
#    builds but `gi.require_version("Gtk", "4.0")` fails headless with
#    `ValueError: Namespace Gtk not available`. postFixup sees the whole
#    array.
{
  lib,
  python3Packages,
  wrapGAppsHook4,
  gobject-introspection,
  gtk4,
  libadwaita,
  vte-gtk4,
  at-spi2-core,
}:
let
  probePython = python3Packages.python.withPackages (ps: [
    ps.pygobject3
    ps.pyatspi
  ]);
in
python3Packages.buildPythonApplication {
  pname = "helm-home";
  version = "0.1";
  format = "other";
  src = ./.;
  nativeBuildInputs = [
    wrapGAppsHook4
    gobject-introspection
  ];
  buildInputs = [
    gtk4
    libadwaita
    vte-gtk4
    at-spi2-core
  ];
  propagatedBuildInputs = with python3Packages; [
    pygobject3
    pyatspi
  ];
  dontWrapGApps = true;
  installPhase = ''
    install -Dm644 *.py -t $out/lib/helm-home
  '';
  postFixup = ''
    makeWrapper ${probePython}/bin/python $out/bin/helm-home-probe \
      --add-flags $out/lib/helm-home/probe.py \
      --prefix PYTHONPATH : $out/lib/helm-home:${../evidence} \
      "''${gappsWrapperArgs[@]}"
  '';
  doInstallCheck = true;
  installCheckPhase = "$out/bin/helm-home-probe --self-check | grep -F 'Gtk 4.' ";
  meta = {
    mainProgram = "helm-home-probe";
    platforms = lib.platforms.linux;
  };
}
