_: {
  # The operator's interactive seat behind its own egress broker (instance
  # 'seat', netns egress-seat, seat@<job> units as dalhaka) -- same key file
  # the openrouter lane injects, injected at egress; no seat process ever
  # holds a key (docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md).
  # 10.100.2.x is media's, 10.100.3.x the openrouter lane's; the seat takes
  # 10.100.4.x. Not started by this switch: like the lane, nothing here is
  # wantedBy anything -- the operator starts jobs one at a time, gated by the
  # polkit rule this module renders.
  services.seat-lane = {
    enable = true;
    keyFile = "/var/lib/secrets/openrouter-key";
    hostAddress = "10.100.4.1";
    namespaceAddress = "10.100.4.2";
    listenPort = 3141;
    operatorUser = "dalhaka";
  };
}
