{ writeShellApplication, python3 }:
# T3 (Lane L round 1 plan): posts /var/lib/lanes/<name>/jobs/<job>.json to
# the broker-injected lane host (chat kind) or runs `claude -p` against it
# (agent kind), and writes /var/lib/lanes/<name>/results/<job>.json --
# see lane-run.py. Stdlib-only, so the only runtime input is python3
# itself; `claude` (agent kind) is deliberately NOT a runtime input here --
# see nixosModules/modelLane.nix for why the unit's own PATH carries it
# instead. This keeps `lane-<name>@.service`'s ExecStart path
# (${lane-run}/bin/lane-run <name> %i), set by T2, unchanged in shape.
writeShellApplication {
  name = "lane-run";
  runtimeInputs = [ python3 ];
  text = ''
    exec python3 ${./lane-run.py} "$@"
  '';
}
