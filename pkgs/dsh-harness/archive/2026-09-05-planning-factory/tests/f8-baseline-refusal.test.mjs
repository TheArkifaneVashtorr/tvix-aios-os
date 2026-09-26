import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// F8: before any implementer runs, a single baseline agent checks that the factory
// root exists and that the session's cwd is under it, and establishes the base clone
// + integration branch tip. If either check is false the script must throw a plain
// Error BEFORE dispatching any implementer — mirroring X0/F3's dispatch-path
// discipline (zero implementer agents on a refusal, even though the one baseline
// check already ran). We reproduce the workflow tool's async-function-body contract
// with stubbed globals and count dispatches by label.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

const T = (overrides = {}) => ({
  key: 'A',
  title: 'A',
  role: 'glm',
  kind: 'routine',
  spec: 'do A',
  dependsOn: [],
  ...overrides,
})

function makeRunner(baseline) {
  const state = { labels: [] }
  const agent = async (_prompt, opts = {}) => {
    const label = opts.label || ''
    state.labels.push(label)
    if (label === 'baseline:env') return baseline
    if (label.startsWith('guard:tree')) return 'clean'
    if (label.startsWith('impl:')) return 'done'
    if (label.startsWith('integrate:')) return { ok: true, merged: [] }
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
  const log = () => {}
  const phase = () => {}
  const run = (args) =>
    new AsyncFunction('agent', 'parallel', 'pipeline', 'log', 'phase', 'args', SCRIPT)(
      agent, parallel, pipeline, log, phase, args
    )
  return { state, run }
}

const OK = { factoryRootOk: true, cwdUnderRoot: true }

test('dispatches the baseline env gate first, before any implementer or integrator', async () => {
  const { state, run } = makeRunner(OK)
  await run({ goal: 'g', mode: 'build', tasks: [T()] })
  assert.equal(state.labels[0], 'baseline:env', 'the baseline gate must be the first dispatch')
  assert.ok(state.labels.includes('impl:A'), 'implementers still run after a clean baseline')
})

test('refuses before any implementer when factoryRootOk is false', async () => {
  const { state, run } = makeRunner({ factoryRootOk: false, cwdUnderRoot: true })
  await assert.rejects(
    run({ goal: 'g', mode: 'build', tasks: [T()] }),
    (err) => {
      assert.ok(err instanceof Error, 'must throw a plain Error')
      assert.match(err.message, /refusing before any implementer/)
      return true
    }
  )
  assert.deepEqual(state.labels, ['baseline:env'], 'only the baseline agent ran — zero implementers')
})

test('refuses before any implementer when cwdUnderRoot is false', async () => {
  const { state, run } = makeRunner({ factoryRootOk: true, cwdUnderRoot: false })
  await assert.rejects(
    run({ goal: 'g', mode: 'build', tasks: [T()] }),
    (err) => {
      assert.ok(err instanceof Error, 'must throw a plain Error')
      assert.match(err.message, /refusing before any implementer/)
      return true
    }
  )
  assert.deepEqual(state.labels, ['baseline:env'], 'only the baseline agent ran — zero implementers')
})

test('refuses before any implementer when the baseline agent reports nothing (null)', async () => {
  const { state, run } = makeRunner(null)
  await assert.rejects(
    run({ goal: 'g', mode: 'build', tasks: [T()] }),
    (err) => {
      assert.ok(err instanceof Error, 'must throw a plain Error')
      assert.match(err.message, /refusing before any implementer/)
      return true
    }
  )
  assert.deepEqual(state.labels, ['baseline:env'], 'only the baseline agent ran — zero implementers')
})

test('plan mode still dispatches zero agents, baseline included', async () => {
  const { state, run } = makeRunner(OK)
  const result = await run({ goal: 'g', mode: 'plan', tasks: [T()] })
  assert.equal(state.labels.length, 0, 'plan mode dispatches nothing at all')
  assert.equal(result.tasks.length, 1)
})
