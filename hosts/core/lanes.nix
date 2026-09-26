_: {
  # OpenRouter -> DeepSeek V4 Flash, Tier B only (permitted data), key
  # injected by the broker from /var/lib/secrets/openrouter-key -- see
  # docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md and
  # docs/superpowers/specs/2026-09-03-data-and-models-system-design.md §8.
  # 10.100.2.x is reserved for the media instance; this lane's address block
  # is 10.100.3.x. Not started by this switch: nothing here is wantedBy
  # anything -- the operator starts jobs one at a time, gated by the polkit
  # rule this module renders.
  services.model-lanes.openrouter = {
    host = "openrouter.ai";
    model = "deepseek/deepseek-v4-flash";
    keyFile = "/var/lib/secrets/openrouter-key";
    hostAddress = "10.100.3.1";
    namespaceAddress = "10.100.3.2";
    listenPort = 3131;
  };
}
