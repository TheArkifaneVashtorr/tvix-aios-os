import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// F8: after each wave, one integrator merges that wave's branches into the integration
// branch in topological-then-key order with `git merge --no-ff`, then runs the check
// surface — the self-test suite run through the sibling devShell's node, because a bare
// `node --check` on the script can never pass (it is an async-function body with
// top-level `await`/`return`). On a merge conflict or red check there is exactly ONE
// bounded fix task (deepseekPro) handed the failure verbatim; if it is still red the
// chain stops — the wave's tasks are marked `integration-failed`, dependents `blocked`,
// and no delivery recipe is printed. The factory never merges into the real repo; it
// prints the orchestrator's ff-only recipe.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

function makeRunner(respond = {}) {
  const state = { labels: [], prompts: new Map(), models: new Map(), logs: [] }
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    state.labels.push(label)
    state.prompts.set(label, String(prompt))
    state.models.set(label, opts.model || '')
    const r = respond[label]
    if (r !== undefined) return typeof r === 'function' ? r() : r
    if (label === 'baseline:env') return { factoryRootOk: true, cwdUnderRoot: true }
    if (label.startsWith('guard:tree')) return 'clean'
    if (label.startsWith('impl:')) return 'done'
    if (label.startsWith('integrate:')) return { ok: true, merged: [] }
    if (label.startsWith('fix:')) return { ok: true }
    if (label.startsWith('judge:')) return { paths: [] } // F9: parallel-safety judge (stubbed: writes nothing shared)
    if (label.startsWith('review:')) return { verdict: 'pass', findings: [] }
    throw new Error('unexpected label ' + label)
  }
  const parallel = async (thunks) => {
    const out = []
    for (const t of thunks) out.push(await t())
    return out
  }
  const pipeline = async () => []
  const log = (l) => state.logs.push(String(l))
  const phase = () => {}
  const run = (args) =>
    new AsyncFunction('agent', 'parallel', 'pipeline', 'log', 'phase', 'args', SCRIPT)(
      agent, parallel, pipeline, log, phase, args
    )
  return { state, run }
}

const T = (overrides = {}) => ({
  key: 'T1',
  title: 'One',
  role: 'glm',
  kind: 'routine',
  spec: 'do the thing',
  dependsOn: [],
  ...overrides,
})

test('runs one integrator per wave, merging the wave branches in key order with --no-ff and the check', async () => {
  const { state, run } = makeRunner()
  await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A' }), T({ key: 'B' })] })
  assert.deepEqual(state.labels.filter((l) => l.startsWith('integrate:')), ['integrate:wave:1'], 'one integrator for the one wave')
  const p = state.prompts.get('integrate:wave:1')
  assert.ok(p, 'the integrator prompt must exist')
  const a = p.indexOf('git merge --no-ff A')
  const b = p.indexOf('git merge --no-ff B')
  assert.ok(a >= 0 && b >= 0 && a < b, 'merges A before B (key order)')
  assert.match(p, /git fetch/, 'pulls each branch before merging')
  assert.match(p, /node --test factory\/tests\/\*\.test\.mjs/, 'names the test-suite check surface')
})

test('the check surface is the self-test suite, never a bare node --check', () => {
  const m = SCRIPT.match(/const CHECK_CMD = '([^']*)'/)
  assert.ok(m, 'CHECK_CMD is defined in the script')
  assert.doesNotMatch(m[1], /node --check/, 'CHECK_CMD no longer contains node --check (the script is an async-function body, so it can never pass)')
  assert.match(m[1], /node --test factory\/tests\/\*\.test\.mjs/, 'the check surface runs the tests that load the script as an AsyncFunction body')
})

test('the check surface prefixes XDG_CACHE_HOME=… so nix has a writable cache under a read-only HOME', () => {
  const m = SCRIPT.match(/const CHECK_CMD = '([^']*)'/)
  assert.ok(m, 'CHECK_CMD is defined in the script')
  assert.ok(
    m[1].startsWith('XDG_CACHE_HOME=${XDG_CACHE_HOME:-/tmp/dsh-factory-cache-$(id -u)} '),
    'CHECK_CMD prefixes the writable-cache env var so nix/cache/sandbox errors cannot poison the check under a read-only HOME'
  )
})

test('the integrator prompt cd-s into the integration clone before merging', async () => {
  const { state, run } = makeRunner()
  const result = await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A' })] })
  const p = state.prompts.get('integrate:wave:1')
  assert.ok(p, 'the integrator prompt must exist')
  assert.ok(p.includes('cd ' + result.integrationClone), 'the integrator is told to cd into the integration clone')
})

test('the integrator prompt tells it to report environment failures distinctly from code failures', async () => {
  const { state, run } = makeRunner()
  await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A' })] })
  const p = state.prompts.get('integrate:wave:1')
  assert.ok(p, 'the integrator prompt must exist')
  assert.ok(p.includes('envError'), 'the prompt names the envError field')
  assert.ok(p.includes('environment') && p.includes('sandbox'), 'the prompt explains the nix/cache/sandbox distinction')
})

test('returns a delivery recipe (fetch + ff-only into the real repo) when integration is green', async () => {
  const { state, run } = makeRunner()
  const result = await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A' })] })
  assert.ok(result.delivery, 'a green integration must produce a delivery recipe')
  assert.match(result.delivery, /cd ~\/flakes\/dsh-harness/, 'recipe targets the real repo')
  assert.match(result.delivery, /git merge --ff-only factory\/integration/, 'recipe is the ff-only merge the orchestrator runs')
  assert.ok(state.logs.some((l) => l.includes('delivery')), 'the recipe is also logged to the durable journal')
})

test('on a conflict dispatches exactly one deepseekPro fix task with the verbatim failure', async () => {
  const { state, run } = makeRunner({
    'integrate:wave:1': { ok: false, conflict: 'CONFLICT (content): Merge conflict in factory/dark-factory.js line 42' },
    'fix:wave:1': { ok: true },
  })
  const result = await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A' })] })
  assert.deepEqual(state.labels.filter((l) => l.startsWith('fix:')), ['fix:wave:1'], 'exactly one fix task — no loop')
  assert.equal(state.models.get('fix:wave:1'), 'deepseek/deepseek-v4-pro-0813', 'the fix task is deepseekPro')
  const fp = state.prompts.get('fix:wave:1')
  assert.ok(fp.includes('CONFLICT (content): Merge conflict in factory/dark-factory.js line 42'), 'hands the conflict verbatim to the fix task')
  assert.deepEqual(result.integration, [{ wave: 1, ok: true, merged: ['A'], fixed: true }], 'the wave is recovered')
  assert.equal('status' in result.implementations[0], false, 'a recovered task is not integration-failed')
  assert.ok(result.delivery, 'a recovered integration still produces a delivery recipe')
})

test('the fix task carries each branch fetch line so "merge the wave branches in order" runs', async () => {
  const { state, run } = makeRunner({
    'integrate:wave:1': { ok: false, conflict: 'CONFLICT (content): Merge conflict in factory/dark-factory.js' },
    'fix:wave:1': { ok: true },
  })
  const result = await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A' }), T({ key: 'B' })] })
  const fp = state.prompts.get('fix:wave:1')
  assert.ok(fp, 'the fix task must be dispatched')
  assert.ok(fp.includes('git fetch $HOME/factory/ws/' + result.runId + '/A A:A'), 'the fix task fetches A from its workspace')
  assert.ok(fp.includes('git fetch $HOME/factory/ws/' + result.runId + '/B B:B'), 'the fix task fetches B from its workspace')
  assert.ok(fp.includes('git merge --no-ff A'), 'the fix task merges A')
  assert.ok(fp.includes('git merge --no-ff B'), 'the fix task merges B')
})

test('when the single fix fails, marks the wave integration-failed, blocks dependents, and stops (no loop)', async () => {
  const { state, run } = makeRunner({
    'integrate:wave:1': { ok: false, check: 'SyntaxError: await is only valid in async functions' },
    'fix:wave:1': { ok: false, detail: 'still red' },
  })
  const result = await run({
    goal: 'g',
    mode: 'build',
    tasks: [T({ key: 'A' }), T({ key: 'B', dependsOn: ['A'] })],
  })
  const byKey = Object.fromEntries(result.implementations.map((r) => [r.key, r]))
  assert.equal(byKey.A.status, 'integration-failed', 'the wave task is integration-failed')
  assert.equal(byKey.A.model, 'z-ai/glm-5.3', 'the success record keeps its model')
  assert.equal(byKey.A.out, 'done', 'the success record keeps its output')
  assert.equal(byKey.A.wave, 1, 'the success record keeps its wave')
  assert.deepEqual(byKey.B, { key: 'B', status: 'blocked', wave: 2, blockedBy: ['A'] }, 'the dependent is blocked')
  assert.deepEqual(state.labels.filter((l) => l.startsWith('fix:')), ['fix:wave:1'], 'exactly one fix task — no retry loop')
  assert.equal(state.labels.filter((l) => l.startsWith('integrate:')).length, 1, 'no further integration after the hard stop')
  assert.equal(state.labels.includes('impl:B'), false, 'wave 2 never runs')
  assert.equal(state.labels.some((l) => l.startsWith('review:')), false, 'cross-review is skipped on a broken tree')
  assert.equal(result.delivery, null, 'no delivery recipe after a hard integration failure')
})

test('an environment failure (nix/cache/sandbox) does not consume the single fix task', async () => {
  const { state, run } = makeRunner({
    'integrate:wave:1': { ok: false, envError: 'error: attempting to write a readonly database (nix cache)' },
  })
  const result = await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A' })] })

  assert.equal(state.labels.filter((l) => l.startsWith('fix:')).length, 0, 'an environment failure never dispatches the fix task')
  assert.deepEqual(
    result.integration,
    [{ wave: 1, ok: false, envError: 'error: attempting to write a readonly database (nix cache)' }],
    'the environment failure is recorded distinctly'
  )
  assert.equal(result.implementations[0].status, 'integration-failed', 'the wave is still marked integration-failed')
  assert.equal(result.delivery, null, 'no delivery recipe after an environment stop')
})

test('the reviewer prompts carry the task→role table so a reviewer can skip its own work', async () => {
  const { state, run } = makeRunner()
  await run({
    goal: 'g',
    mode: 'build',
    tasks: [T({ key: 'A', role: 'deepseekPro' }), T({ key: 'B', role: 'kimi' })],
  })
  const tp = state.prompts.get('review:technical')
  assert.ok(tp, 'the technical reviewer must be dispatched')
  assert.ok(tp.includes('A: deepseekPro (deepseek/deepseek-v4-pro-0813)'), 'carries the deepseekPro task → model row')
  assert.ok(tp.includes('B: kimi (moonshotai/kimi-k3)'), 'carries the kimi task → model row')
  assert.ok(tp.includes('never approve your own work'), 'the reviewer is told how to use the table')
  assert.ok(state.prompts.get('review:visual').includes('A: deepseekPro'), 'the visual reviewer carries the table too')
  assert.ok(state.prompts.get('review:completeness').includes('A: deepseekPro'), 'the completeness reviewer carries the table too')
})

test('each reviewer prompt carries its own model id alongside the role table', async () => {
  const { state, run } = makeRunner()
  await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A' })] })
  assert.ok(state.prompts.get('review:technical').includes('YOUR MODEL ID: deepseek/deepseek-v4-pro-0813'), 'the technical reviewer is told its own model id')
  assert.ok(state.prompts.get('review:visual').includes('YOUR MODEL ID: moonshotai/kimi-k3'), 'the visual reviewer is told its own model id')
  assert.ok(state.prompts.get('review:completeness').includes('YOUR MODEL ID: z-ai/glm-5.3'), 'the completeness reviewer is told its own model id')
})

test('skips integration entirely for a wave with no green task', async () => {
  const { state, run } = makeRunner({ 'impl:A': null, 'impl:A:retry': null })
  const result = await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A' })] })
  assert.equal(state.labels.filter((l) => l.startsWith('integrate:')).length, 0, 'nothing to integrate when the only task failed')
  assert.equal(result.implementations[0].status, 'failed', 'the implementer failure is still recorded')
})

test('emits no delivery recipe and no cross-review when nothing was integrated', async () => {
  const { state, run } = makeRunner({ 'impl:A': null, 'impl:A:retry': null })
  const result = await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A' })] })
  assert.equal(result.delivery, null, 'no delivery recipe when no task was integrated green')
  assert.equal(state.labels.some((l) => l.startsWith('review:')), false, 'cross-review is skipped when no task was integrated green')
})
