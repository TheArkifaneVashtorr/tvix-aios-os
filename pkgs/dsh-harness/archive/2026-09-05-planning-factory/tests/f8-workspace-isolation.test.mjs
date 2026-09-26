import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// F8: every task runs in its own persistent clone under `${factoryRoot}/ws/<run-id>/<taskKey>`
// on a branch named by its key; the run-id is generated once at start and every path is
// listed on the return value for post-mortems. The base clone is shared read-only state
// refreshed from the real HEAD, and the integration clone is established up front so the
// integration branch tip exists before the first implementer clones from it.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

function makeRunner() {
  const state = { labels: [], prompts: new Map() }
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    state.labels.push(label)
    state.prompts.set(label, String(prompt))
    if (label === 'baseline:env') return { factoryRootOk: true, cwdUnderRoot: true }
    if (label.startsWith('guard:tree')) return 'clean'
    if (label.startsWith('impl:')) return 'done'
    if (label.startsWith('integrate:')) return { ok: true, merged: [] }
    if (label.startsWith('judge:')) return { paths: [] } // F9: parallel-safety judge (stubbed: writes nothing shared)
    if (label.startsWith('review:')) return { verdict: 'pass', findings: [] }
    throw new Error('unexpected label ' + label)
  }
  const parallel = async (thunks) => Promise.all(thunks.map((t) => t()))
  const pipeline = async () => []
  const log = () => {}
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

test('generates one run-id and lists every task workspace + branch on the return', async () => {
  const { run } = makeRunner()
  const result = await run({
    goal: 'g',
    mode: 'build',
    tasks: [T({ key: 'T1' }), T({ key: 'T2' })],
  })
  assert.match(result.runId, /^run-/, 'the run-id is generated once and returned')
  assert.equal(result.factoryRoot, '$HOME/factory', 'the default factory root is $HOME/factory')
  const byKey = Object.fromEntries(result.tasks.map((t) => [t.key, t]))
  assert.equal(byKey.T1.workspace, '$HOME/factory/ws/' + result.runId + '/T1')
  assert.equal(byKey.T1.branch, 'T1')
  assert.equal(byKey.T2.workspace, '$HOME/factory/ws/' + result.runId + '/T2')
  assert.equal(byKey.T2.branch, 'T2')
})

test('implementer prompt clones its own workspace from the base clone and checks out its branch', async () => {
  const { state, run } = makeRunner()
  const result = await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'T1' })] })
  const p = state.prompts.get('impl:T1')
  assert.ok(p, 'the implementer must be dispatched')
  assert.match(p, /git clone --local \$HOME\/factory\/base\/dsh-harness/, 'clones from the base clone, never the real repo')
  assert.ok(p.includes('$HOME/factory/ws/' + result.runId + '/T1'), 'the workspace path carries the run-id and task key')
  assert.match(p, /git checkout -B T1/, 'checks out a branch named by the task key')
  assert.match(p, /Commit only on branch T1/, 'the implementer commits only on its own branch')
})

test('baseline prompt checks the factory root, prepares the base clone, and establishes the integration clone', async () => {
  const { state, run } = makeRunner()
  await run({ goal: 'g', mode: 'build', tasks: [T()] })
  const p = state.prompts.get('baseline:env')
  assert.ok(p, 'the baseline gate must be dispatched')
  assert.ok(p.includes('test -d $HOME/factory'), 'checks the factory root exists')
  assert.ok(p.includes('git clone --local ~/flakes/dsh-harness $HOME/factory/base/dsh-harness'), 'clones the base from the real repo')
  assert.ok(p.includes('git checkout -B factory/integration'), 'establishes the integration branch tip up front')
  assert.ok(p.includes('factoryRootOk'), 'reports factoryRootOk')
  assert.ok(p.includes('cwdUnderRoot'), 'reports cwdUnderRoot')
})

test('schedule exposes groups (concurrency chunking) and the topological-then-key integration order', async () => {
  const { run } = makeRunner()
  // Two independent tasks + one dependent, listed out of key order, concurrency 1.
  const result = await run({
    goal: 'g',
    mode: 'plan',
    concurrency: 1,
    tasks: [
      T({ key: 'C', dependsOn: ['A'] }),
      T({ key: 'A' }),
      T({ key: 'B' }),
    ],
  })
  assert.deepEqual(result.schedule.waves, [['A', 'B'], ['C']], 'C is in wave 2 after A')
  assert.deepEqual(result.schedule.groups, [[['A'], ['B']], [['C']]], 'concurrency 1 chunks each wave into single-task groups')
  assert.deepEqual(result.schedule.integrationOrder, ['A', 'B', 'C'], 'topological, then key order')
})

test('plan-mode projection carries null workspace/branch (nothing executes yet)', async () => {
  const { run } = makeRunner()
  const result = await run({ goal: 'g', mode: 'plan', tasks: [T()] })
  assert.equal(result.tasks[0].workspace, null)
  assert.equal(result.tasks[0].branch, null)
})
