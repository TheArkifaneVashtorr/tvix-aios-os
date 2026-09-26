# Opus gate round 4 (closing) — `integ/b3` @ c7e6fe7 (BFIX4)

**Verdict: approve.** 87/87 green. M1 and all four round-3 minors close, each
reverse-applying to a red test. Scope is exactly the claimed 5 files: `84bd8bc^{tree}`
equals round-3's `990cbab^{tree}`, so BFIX4 is the whole delta and nothing else moved.

## Major

None. `factory/dark-factory.js:354` now derives `overlapsAll` from the judge's own
answer, the same expression the `touches` branch uses; the new f9 test stubs label
`judge:B` returning `{paths:[...]}`, which is the real dispatch shape (`:584`, `:590`),
so it exercises the live path, not a fiction. Both `['**']` and `['*.md']` beside a
`parallelSafe: true` peer now serialise and note `writes everything`.

## Minors

- `:84` `fixPath` is not reserved the way `integration` now is (`:244`): a task keyed
  `fix-w0` shares a directory with the wave-0 fix clone — its retry `rm -rf`s that clone
  and the fix agent's `git clone` (`:556`) then fails on a non-empty destination. Same
  class as the closed collision, bounded (recreatable clone); reserve `/^fix-w\d+$/`.
- `:640` `envError` still short-circuits the fix task — unchanged, accepted as M-e.
- Docs verified true: `AGENTS.md:33-35` now reproduces `CHECK_CMD` (`:92`) character for
  character including the `XDG_CACHE_HOME` prefix; `README.md:96-99` states the charset,
  all-dot and reserved-key rules; `README.md:136-138` names all three note reasons, which
  are exactly the three strings at `:403-405`. No false statement remains.

## Mutations (scratch clone, deleted)

| # | mutation | result |
|---|---|---|
| M1 | `:354` judge `overlapsAll` → `false` | red — f9 judge leading-glob |
| M2 | `:241` drop `/^\.+$/` clause | red — x0 all-dot keys (asserts 0 dispatches) |
| M3 | `:244` delete reserved-key guard | red — x0 reserved `integration` |
| M4 | `:403` note reason → always `touches overlap` | red — both `writes everything` tests |
