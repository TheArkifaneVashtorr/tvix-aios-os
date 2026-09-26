// Executes the REAL rendered security.polkit.extraConfig text (T2, plan
// docs/superpowers/plans/2026-09-03-lane-fix-round.md) -- not a hand-copied
// re-implementation of the rule. flake.nix's `lanePolkitRules` writeText
// exports the text produced by evaluating the actual host `core` config
// (nixosModules/modelLane.nix wired through hosts/core/lanes.nix, the
// "openrouter" lane), the same source checks.host-core already reads for
// the same instance -- so this proves the grant polkitd will actually load,
// not an intention. Path comes in via LANE_POLKIT_RULES (set by
// checks.lane-polkit-unit).
import fs from 'node:fs'
import assert from 'node:assert/strict'

const rulesPath = process.env.LANE_POLKIT_RULES
if (!rulesPath) {
  throw new Error(
    'polkit.test.mjs: LANE_POLKIT_RULES must point at the rendered extraConfig text ' +
      '(checks.lane-polkit-unit sets this; for local runs: ' +
      'nix eval --raw .#nixosConfigurations.core.config.security.polkit.extraConfig > /tmp/rules.js ' +
      '&& LANE_POLKIT_RULES=/tmp/rules.js node tests/lane/polkit.test.mjs)',
  )
}
const text = fs.readFileSync(rulesPath, 'utf8')

// security.polkit.extraConfig runs under polkitd's bundled duktape engine:
// ES5 only (security.md reference). Any of these constructs compiles fine
// under node (which is why this must be a text scan, not a run-and-hope)
// but throws at polkitd startup -- catch it here, not in the field.
const es6Patterns = [
  [/=>/, 'arrow function ("=>")'],
  [/\blet\s/, '"let"'],
  [/\bconst\s/, '"const"'],
  [/\.includes\s*\(/, '.includes('],
  [/\.endsWith\s*\(/, '.endsWith('],
  [/\.startsWith\s*\(/, '.startsWith('],
  [/`/, 'template literal (backtick)'],
]
for (const [pattern, label] of es6Patterns) {
  assert.ok(!pattern.test(text), `polkit rule text must be ES5 -- found ${label}`)
}

// Stub polkit global: addRule collects the function; Result.YES is the only
// sentinel these rules ever return; log is unused by modelLane.nix's rule
// but polkit.addRule callers are free to call it.
const rules = []
const polkitStub = {
  addRule: function (fn) {
    rules.push(fn)
  },
  Result: { YES: 'yes' },
  log: function () {},
}

// The rendered text is `polkit.addRule(function (action, subject) {...});`
// repeated once per services.model-lanes.<name> -- run it with the stub
// global exactly as polkitd's duktape sandbox would provide `polkit`.
new Function('polkit', text)(polkitStub)

assert.ok(rules.length > 0, 'the rendered text must call polkit.addRule at least once')

function actionId(id) {
  return id === undefined ? 'org.freedesktop.systemd1.manage-units' : id
}

// First rule to return a Result wins (security.md); mirror that here so a
// module contributing multiple rules is tested the way polkitd combines
// them, not just each rule read in isolation.
function decide({ verb, unit, id } = {}, { user } = {}) {
  const action = {
    id: actionId(id),
    lookup: function (key) {
      return { verb: verb, unit: unit }[key]
    },
  }
  // isInGroup: the rendered text on host `core` is the WHOLE
  // security.polkit.extraConfig (types.lines concatenates every module's
  // contribution -- see module-system.md) -- NetworkManager/CUPS default
  // rules land here too, and each checks subject.isInGroup() before its own
  // action.id, so the stub needs the method even though none of this
  // test's subjects are ever in those groups.
  const subject = {
    user: user,
    isInGroup: function () {
      return false
    },
  }
  for (const rule of rules) {
    const result = rule(action, subject)
    if (result !== undefined) return result
  }
  return undefined
}

const UNIT = 'lane-openrouter@abc.service'
const OPERATOR = 'dalhaka'

assert.equal(
  decide({ verb: 'start', unit: UNIT }, { user: OPERATOR }),
  'yes',
  'operator starting their own lane job must be granted',
)

for (const verb of ['stop', 'restart', 'kill']) {
  assert.equal(
    decide({ verb, unit: UNIT }, { user: OPERATOR }),
    undefined,
    `verb "${verb}" on the lane unit must NOT be granted (start-only)`,
  )
}

assert.equal(
  decide({ verb: 'start', unit: UNIT }, { user: 'eve' }),
  undefined,
  'a non-operator subject must NOT be granted',
)

assert.equal(
  decide({ verb: 'start', unit: 'lane-openrouterx@a.service' }, { user: OPERATOR }),
  undefined,
  'a unit whose prefix merely starts with the lane name minus the "@" must NOT be granted (prefix must include "@")',
)

assert.equal(
  decide({ verb: 'start', unit: 'lane-openrouter@a.service.d' }, { user: OPERATOR }),
  undefined,
  'a unit name with a trailing ".d" (not truly ending ".service") must NOT be granted',
)

assert.equal(
  decide({ verb: 'start', unit: UNIT, id: 'org.freedesktop.systemd1.reload-daemon' }, { user: OPERATOR }),
  undefined,
  'a different polkit action id must NOT be granted by this rule',
)

console.log('polkit.test.mjs: all assertions passed')
