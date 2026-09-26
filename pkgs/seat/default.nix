{
  writeShellApplication,
  python3,
}:
# sb3 + sb1 (plan 2026-09-05-seat-behind-broker): the operator-side tools for
# the seat lane. Both are stdlib-only Python, so python3 is the only runtime
# input for each.
#
#   seat-submit -- SB3. Writes /var/lib/seat/jobs/<id>/job.json and starts the
#   seat@<id> unit that runs it (or, for headless, polls for its result) --
#   see seat-submit.py.
#   seat-run    -- SB1. The unit's own entry: reads the job, exports DSH_HOME,
#   cd's to the workspace and runs `dsh-openrouter --broker` behind the seat's
#   egress broker -- see seat-run.py. nixosModules/seatLane.nix wires it into
#   seat@.service's ExecStart.
let
  seatSubmit = writeShellApplication {
    name = "seat-submit";
    runtimeInputs = [ python3 ];
    text = ''
      exec python3 ${./seat-submit.py} "$@"
    '';
  };
  seatRun = writeShellApplication {
    name = "seat-run";
    runtimeInputs = [ python3 ];
    text = ''
      exec python3 ${./seat-run.py} "$@"
    '';
  };
  # SD6 (plan 2026-09-06-seat-driver): the spool -- the one host-side actor
  # the seat may reach. stdlib-only Python like its siblings; seatLane.nix
  # wires it into seat-spool.service (root, oneshot).
  seatSpool = writeShellApplication {
    name = "seat-spool";
    runtimeInputs = [ python3 ];
    text = ''
      exec python3 ${./seat-spool.py} "$@"
    '';
  };
in
{
  seat-submit = seatSubmit;
  seat-run = seatRun;
  seat-spool = seatSpool;
}
