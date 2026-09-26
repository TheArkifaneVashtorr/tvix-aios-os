{
  name,
  baskets,
  egress ? "none",
  placement ? "bubblewrap",
}:
{
  services.baskets.agents.${name} = {
    inherit baskets egress placement;
  };
}
