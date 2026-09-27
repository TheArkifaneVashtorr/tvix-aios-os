"""Assemble draft-0.md from the header and the part files (placeholders replaced)."""
import pathlib, sys

S = pathlib.Path("/tmp/draft-scratch")
P = S / "parts"
draft = (S / "draft-0.md").read_text()

def part(name, default=""):
    p = P / name
    return p.read_text().rstrip("\n") if p.exists() else default

repl = {
    "WAVES_PLACEHOLDER": part("waves.md", "_(filled after the draft check)_"),
    "OPERATOR_PLACEHOLDER": part("operator.md"),
    "DISPATCH_PLACEHOLDER": part("dispatch.md", "_(filled after the dry run)_"),
    "ANTICIPATION_PLACEHOLDER": part("anticipation.md"),
    "NOTIN_PLACEHOLDER": part("notin.md"),
    "TASKS_PLACEHOLDER": part("tasks-a.md") + "\n\n" + part("tasks-b.md"),
}
for k, v in repl.items():
    if k not in draft:
        print(f"assemble: placeholder {k} not in draft (already replaced?)", file=sys.stderr)
        continue
    draft = draft.replace(k, v)
(S / "draft-0.md").write_text(draft)
print("assembled", len(draft.split()), "words")
