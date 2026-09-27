#!/usr/bin/env python3
"""tools/experiments/jaz/run_arm_c.py -- arm C's driver: the real jaz-lang
framework, configured with ClaudeGatewayLLM, drafting a plan from a spec
inside a fixture checkout.

Spec: docs/superpowers/specs/2026-09-25-jaz-planning-experiment-design.md
§6b. Meant to run under bubblewrap (see run-arm-c.sh), with `--fixture`
read-only, `--scratch` writable, and `--socket` the gateway's bind-mounted
Unix socket; this script itself never touches `claude` or the login.

Imports `jaz` (via the jaz-lang package, pkgs/jaz-lang) -- not exercised
by the bats suite; see the build report for how it is smoke-tested.

2026-09-27 Opus review revisions:
  - the drafter writes its own draft via the `write_scratch` REPL tool
    (confined_tools.py); `invoke()`'s return value is no longer written
    over `scratch/draft-0.md` -- it goes to `scratch/return.json` instead,
    since overwriting the file the agent itself was told to author with
    whatever string `invoke()` happens to return (which may not even be
    the draft -- ContextWindowWarning's own template has the agent
    delegate and return a DELEGATION, not necessarily draft text) would
    silently clobber real work;
  - the top-level `invoke()` inputs are renamed `instructions=`/
    `guidance=` (from `task=`/`spec_text=`) to match jaz-evals'
    StuLife config, whose ContextWindowWarning `warning_text` (used here
    VERBATIM -- see STULIFE_WARNING_TEXT's docstring) tells the agent to
    delegate by re-passing exactly these two variable names;
  - the confined tools are bound via `jaz.scope(**tools)`, not as
    `invoke()` kwargs: an explicit kwarg does NOT propagate to a nested
    `invoke()` a delegated sub-agent calls (jaz/scope.py's own module
    docstring), so without this a child spawned via the warning's own
    delegation template would have no tools at all.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import confined_tools  # noqa: E402
import extract_draft_prompt  # noqa: E402
from claude_llm import ClaudeGatewayLLM  # noqa: E402

# VERBATIM from jaz-lang/jaz-evals, configs/stulife_jaz.yaml, lines 17-45,
# commit 83dc51ebbd02c9299890b6db93ddc773f07b74b9 (fetched 2026-09-27,
# `curl -sSL https://raw.githubusercontent.com/jaz-lang/jaz-evals/main/configs/stulife_jaz.yaml`):
# the paper's own long-horizon ContextWindowWarning text and delegation
# template, at the same warn_fraction (0.7) the design's §6b specifies.
# Reproduced verbatim rather than paraphrased because the template's own
# variable names (`instructions`, `guidance`, `prev_history`,
# `__history__`) are exactly what this run's top-level `invoke()` inputs
# and jaz.scope binding must match for a delegated child to actually
# receive them.
STULIFE_WARNING_TEXT = (
    "Your context window is close to full. You must finish your REPL session now by delegating\n"
    "all remaining work to a subagent.\n"
    "\n"
    "IMPORTANT NOTES:\n"
    "- You must raise your code's timeout with a `# timeout: 86400` pragma on the FIRST line of\n"
    "  your code to prevent the subagent from timing out prematurely.\n"
    "- You must give the subagent both the previous agent's REPL history (`prev_history`) if available,\n"
    "  as well as your own REPL history (`__history__`), so that existing work is not lost.\n"
    "\n"
    "Follow this template exactly:\n"
    "\n"
    "# timeout: 86400\n"
    "return invoke(\n"
    "    # Give the subagent the input variables that you were given, `instructions` and `guidance`\n"
    "    instructions=instructions,  # give the subagent your `instructions` variable\n"
    "    guidance=guidance,  # give the subagent your `guidance` variable\n"
    "    # Give the subagent both the previous agent's REPL history (the `prev_history` variable)\n"
    "    # and your own REPL history (the `__history__` variable)\n"
    '    prev_history=globals().get("prev_history", []) + __history__,\n'
    "    # Hand over any state you've been tracking\n"
    "    state=...,\n"
    "    # Summarize what has been done and what remains (hard-coded string)\n"
    '    prev_progress_summary="So far, ...",\n'
    "    # Tell the subagent what the next steps are (hard-coded string)\n"
    '    next_steps="Your next step is to ...",\n'
    ")\n"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture", required=True, help="the fixture checkout root (read-only)"
    )
    parser.add_argument(
        "--spec", help="spec path, relative to --fixture (required unless --smoke)"
    )
    parser.add_argument("--name", help="short run name (required unless --smoke)")
    parser.add_argument("--date", help="today, YYYY-MM-DD (required unless --smoke)")
    parser.add_argument("--scratch", required=True, help="writable scratch directory")
    parser.add_argument(
        "--socket", required=True, help="the gateway's Unix socket path"
    )
    parser.add_argument("--model", default="claude-fable-5-1")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--calls-budget", type=int, default=40)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="run a toy tool+nested-invoke task instead of a draft",
    )
    return parser


def run_smoke(llm: "ClaudeGatewayLLM", tools: dict, calls_budget: int) -> dict:
    import jaz
    from jaz.hooks import BudgetPool, RecursionLimit, ReturnType

    smoke_instructions = (
        "This is a smoke test. First call list_dir('.') exactly once to see "
        "what is in the fixture root. Then call invoke(ReturnType(str), "
        'instructions="Reply with exactly the word: ok") exactly once as a '
        "nested sub-question, and return its result verbatim as your own "
        "final answer."
    )
    with jaz.scope(**tools):
        result = jaz.invoke(
            ReturnType(str),
            BudgetPool(calls_budget=calls_budget),
            RecursionLimit(max_depth=2),
            instructions=smoke_instructions,
            guidance="",
        )
    return {"result": result, "usage": llm.usage_summary()}


def run_draft(llm: "ClaudeGatewayLLM", tools: dict, args: argparse.Namespace) -> dict:
    import jaz
    from jaz.hooks import (
        BudgetPool,
        ContextWindowWarning,
        FileLogger,
        RecursionLimit,
        ReturnType,
        TrajectoryDirectoryRecorder,
    )

    if not (args.spec and args.name and args.date):
        raise SystemExit(
            "run_arm_c.py: --spec, --name and --date are required unless --smoke"
        )

    spec_full_path = os.path.join(args.fixture, args.spec)
    with open(spec_full_path, encoding="utf-8") as fh:
        spec_text = fh.read()

    # ${STORE} is draft-byref.js's own inherited "EVIDENCE_STORE=..." line
    # (outside the swapped paragraph); this basket only ever has the
    # fixture's own evidence/ mounted -- never /var/lib/evidence, which is
    # not reachable here at all.
    instructions_text = extract_draft_prompt.build_arm_c_prompt(
        args.fixture,
        scratch=args.scratch,
        store=os.path.join(args.fixture, "evidence"),
        spec=args.spec,
    )

    traj_dir = os.path.join(args.scratch, "trajectory")
    log_path = os.path.join(args.scratch, "jaz.log")
    os.makedirs(traj_dir, exist_ok=True)

    with jaz.scope(**tools):
        with FileLogger(log_path), TrajectoryDirectoryRecorder(traj_dir):
            result = jaz.invoke(
                ReturnType(str),
                BudgetPool(calls_budget=args.calls_budget),
                ContextWindowWarning(
                    warn_fraction=0.7, warning_text=STULIFE_WARNING_TEXT
                ),
                RecursionLimit(max_depth=2),
                instructions=instructions_text,
                guidance=spec_text,
            )

    # The agent writes its own draft via write_scratch("draft-0.md", ...)
    # (see the instructions paragraph); invoke()'s return value is NOT the
    # draft in general (a context-window delegation returns whatever the
    # LAST delegate returned, which the template above never promises is
    # draft text) -- it goes to its own file instead, never clobbering
    # scratch/draft-0.md.
    return_path = os.path.join(args.scratch, "return.json")
    with open(return_path, "w", encoding="utf-8") as fh:
        json.dump({"return_value": result}, fh, indent=2, default=str)

    draft_path = os.path.join(args.scratch, "draft-0.md")
    return {
        "draft": draft_path,
        "draft_exists": os.path.exists(draft_path),
        "return_value_path": return_path,
        "log": log_path,
        "trajectory": traj_dir,
        "queries_log": os.path.join(args.scratch, "queries.log"),
        "usage": llm.usage_summary(),
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    os.makedirs(args.scratch, exist_ok=True)

    import jaz  # imported here (not at module top) so an argv error above never needs jaz-lang installed

    llm = ClaudeGatewayLLM(
        socket_path=args.socket,
        model=args.model,
        effort=args.effort,
        warning_texts=[STULIFE_WARNING_TEXT],
    )
    jaz.configure(llm=llm)

    tools = confined_tools.make_tools(args.fixture, args.scratch)

    if args.smoke:
        output = run_smoke(llm, tools, args.calls_budget)
    else:
        output = run_draft(llm, tools, args)

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
