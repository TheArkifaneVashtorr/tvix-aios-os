# US1 (plan 2026-09-24-strict-user-spaces-1a.md): the operator's shell and
# CLI set. bash is the shell the operator already runs (bash-interactive);
# the five packages are exactly the ones the host's systemPackages already
# carries, so the user side changes no package version in the host closure.
# Left imperative (question 3 = none): ~/.claude/settings.json and every
# Claude Code skill directory -- files the tool rewrites; a later task
# declares them once the operator names the keys. This file is published and
# user-agnostic: it reads no config, names no user, and interpolates no
# source path.
{ pkgs, ... }:
{
  programs.bash.enable = true;
  home.packages = with pkgs; [
    git
    jq
    curl
    less
    socat
  ];
}
