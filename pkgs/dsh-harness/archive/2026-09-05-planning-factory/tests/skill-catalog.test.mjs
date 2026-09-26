import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname, resolve, relative, sep, basename } from "node:path";
import { fileURLToPath } from "node:url";

// F6 — re-sync the vendored `nixos` skill and fix what dsh cannot resolve in
// the skill catalog: the `superpowers:` prefix (dsh's skill-name grammar
// forbids a colon) and the cross-skill file paths. F6FIX: dsh resolves a
// skill's relative paths against that skill's OWN directory
// (dsh-skill-filesystem sets resourceBase to `<root>/<skill-name>`; dsh-skill
// tells the model to resolve relative paths against that base), so a
// cross-skill reference must be written `../<skill>/<path>` — the `../` walks
// out of the current skill into the sibling skill. The bare `<skill>/<path>`
// rewrite broke seven references. This test walks the `skills/` tree and
// asserts the three invariants the task names, plus the S1 re-sync markers.

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const SKILLS_DIR = join(REPO_ROOT, "skills");

/** Recursively list regular files under `dir`, in a stable order. */
function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir).sort()) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) out.push(...walk(full));
    else out.push(full);
  }
  return out;
}

function readTree() {
  return walk(SKILLS_DIR).map((file) => ({
    file,
    rel: relative(REPO_ROOT, file).split(sep).join("/"),
    text: readFileSync(file, "utf8"),
  }));
}

function countOccurrences(haystack, needle) {
  return haystack.split(needle).length - 1;
}

/** Names of the skills in the catalog (top-level dirs with a SKILL.md). */
function skillNames() {
  const names = new Set();
  for (const name of readdirSync(SKILLS_DIR).sort()) {
    if (
      statSync(join(SKILLS_DIR, name, "SKILL.md"), { throwIfNoEntry: false })
        ?.isFile()
    ) {
      names.add(name);
    }
  }
  return names;
}

function skillNameOf(file) {
  return basename(dirname(file));
}

function exists(path) {
  return statSync(path, { throwIfNoEntry: false }) !== undefined;
}

// A cross-skill reference is a relative path that points into another skill's
// directory. dsh resolves it against the SKILL.md's own directory, so:
//   - `../<skill>/<path>` is always cross-skill (the `../` leaves the current
//     skill's directory), and
//   - `<skill>/<path>` is cross-skill when the first segment names a different
//     skill in the tree (a bare reference resolves to
//     `<this-skill>/<skill>/<path>`, which cannot exist).
// A bare reference whose first segment is not a known skill name is
// indistinguishable from a same-skill subdirectory or repo-root path (e.g.
// `scripts/…`, `docs/…`), so it is not treated as cross-skill; a reference to
// a non-existent skill is caught in the unambiguous `../` form instead.
// Group 2 is the leading segment with its optional `../`; group 3 is that
// optional `../`; group 4 is the skill token; group 5 is the rest of the path.
const CROSS_SKILL_REF_RE =
  /(^|[^\w@/])((\.\.\/)?([a-z0-9][a-z0-9-]*))(\/[^\s"'`()<>{}\[\]]+)/g;

/**
 * Return the cross-skill references in `files` that do not resolve against the
 * directory of the SKILL.md that mentions them. `files` is [{file, text}] with
 * absolute file paths; `names` is the set of skill names in the tree.
 */
function findBrokenCrossSkillRefs(files, names) {
  const broken = [];
  for (const { file, text } of files) {
    const own = skillNameOf(file);
    for (const m of text.matchAll(CROSS_SKILL_REF_RE)) {
      const lead = m[2]; // "skill" or "../skill"
      const isUp = m[3] !== undefined; // "../" present
      const skill = m[4];
      if (!isUp && (skill === own || !names.has(skill))) continue;
      const ref = lead + m[5];
      const resolved = resolve(dirname(file), ref);
      if (!exists(resolved)) {
        broken.push({
          file: relative(REPO_ROOT, file).split(sep).join("/"),
          ref,
        });
      }
    }
  }
  return broken;
}

test("no superpowers: prefix remains anywhere in the skills tree", () => {
  const hits = [];
  let total = 0;
  for (const { rel, text } of readTree()) {
    const n = countOccurrences(text, "superpowers:");
    if (n > 0) hits.push(`${rel}: ${n}`);
    total += n;
  }
  assert.deepEqual(
    hits,
    [],
    `expected zero "superpowers:" prefixes, found ${total} across: ${hits.join(", ")}`
  );
});

test("every cross-skill relative path resolves against its own SKILL.md's directory", () => {
  const names = skillNames();
  const files = readTree().filter((f) => f.rel.endsWith("/SKILL.md"));
  const broken = findBrokenCrossSkillRefs(files, names);
  assert.deepEqual(
    broken,
    [],
    `cross-skill references that do not resolve against their SKILL.md: ${broken
      .map((b) => `${b.file} -> ${b.ref}`)
      .join("; ")}`
  );
});

test("a cross-skill reference to a non-existent skill is reported broken", () => {
  const names = skillNames();
  const files = [
    {
      file: join(SKILLS_DIR, "subagent-driven-development", "SKILL.md"),
      text: "see [code-reviewer.md](../no-such-skill/code-reviewer.md)",
    },
  ];
  assert.deepEqual(
    findBrokenCrossSkillRefs(files, names).map((b) => b.ref),
    ["../no-such-skill/code-reviewer.md"]
  );
});

test("a bare cross-skill path to a non-existent file is reported broken", () => {
  const names = skillNames();
  const files = [
    {
      file: join(SKILLS_DIR, "subagent-driven-development", "SKILL.md"),
      text: "see [code-reviewer.md](requesting-code-review/no-such-file.md)",
    },
  ];
  assert.deepEqual(
    findBrokenCrossSkillRefs(files, names).map((b) => b.ref),
    ["requesting-code-review/no-such-file.md"]
  );
});

test("a bare cross-skill path to an existing file still does not resolve (missing ../)", () => {
  const names = skillNames();
  const files = [
    {
      file: join(SKILLS_DIR, "subagent-driven-development", "SKILL.md"),
      text: "see [code-reviewer.md](requesting-code-review/code-reviewer.md)",
    },
  ];
  // Bare form resolves to subagent-driven-development/requesting-code-review/…
  // which does not exist; the correct form is ../requesting-code-review/…
  assert.deepEqual(
    findBrokenCrossSkillRefs(files, names).map((b) => b.ref),
    ["requesting-code-review/code-reviewer.md"]
  );
});

test("vendored nixos skill is re-synced from ~/flakes/nixos-skill (re-sync markers)", () => {
  const gotchas = readFileSync(
    join(SKILLS_DIR, "nixos", "references", "gotchas.md"),
    "utf8"
  );
  assert.match(gotchas, /Read-only nix cache under an agent sandbox/);
  assert.match(gotchas, /The bash tool and the file tool split \/tmp/);

  const skill = readFileSync(join(SKILLS_DIR, "nixos", "SKILL.md"), "utf8");
  // canonical master 962849d (two fix rounds) added the "What doc-tests prove"
  // section and dropped `--offline` from the hash-obtaining rule; an un-synced
  // copy still carries the older `nix hash path --offline` text.
  assert.match(skill, /## What doc-tests prove, and what they don't/);
  assert.doesNotMatch(skill, /nix hash path\s+--offline/);
});
