{
  name = "nixos-agent-env";
  summary = "The host's own flake: baskets, the egress broker, Helm, the factory.";
  why = "core is built from this flake; every agent environment, the broker and the switch surface are declared here.";
  created = "2026-09-02";
  owner = "operator";
  writtenAgainst = null;
  state = "live: the host runs from this tree; Helm Home sub-project 1 in progress.";
  updated = "2026-09-09";
  offers = {
    profiles = [ "core" ];
    run = [
      {
        label = "Helm status";
        command = "helm-status --print";
      }
    ];
    seats = [
      "claude"
      "deepseek"
    ];
  };
  card = {
    blocks = [
      "why"
      "state"
      "do"
      "notes"
    ];
    notes = "Switch targets the host's base profile (services.helm.home.flakes). The card text is refreshed by an accepted proposal.";
  };
}
