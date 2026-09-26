import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// The workflow script has no filesystem, so the U1-kernel tree guard dispatches a
// cheap agent — ONCE per build run, not once per task — checking
// `git -C ~/flakes/dsh-harness status --porcelain` (the shared harness repo the
// operator and seat may both touch; NOT the factory-root cwd, which F8 requires not
// to be a checkout). A `fatal:` reply means "could not check" (no repo at that
// path), not a dirty tree; only a non-empty, non-clean reply warns.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

function makeRunner(guardOutput) {
  const state = { logs: [], labels: [], prompts: new Map() }
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    state.labels.push(label)
    state.prompts.set(label, String(prompt))
    if (label === 'guard:tree') return guardOutput
    if (label.startsWith('impl:')) return 'done'
    if (label === 'baseline:env') return { factoryRootOk: true, cwdUnderRoot: true }
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
  const log = (line) => { state.logs.push(String(line)) }
  const phase = () => {}
  const run = (args) =>
    new AsyncFunction('agent', 'parallel', 'pipeline', 'log', 'phase', 'args', SCRIPT)(
      agent, parallel, pipeline, log, phase, args
    )
  return { state, run }
}

const T = (overrides = {}) => ({
  key: 'A',
  title: 'A',
  role: 'glm',
  kind: 'routine',
  spec: 'do A',
  dependsOn: [],
  ...overrides,
})

test('runs the tree guard once per build and points it at the harness repo, not the session cwd', async () => {
  const { state, run } = makeRunner('clean')
  await run({ goal: 'g', mode: 'build', tasks: [T({ key: 'A' }), T({ key: 'B' })] })

  assert.deepEqual(
    state.labels.filter((l) => l.startsWith('guard:tree')),
    ['guard:tree'],
    'one guard agent for the whole run, not one per task'
  )
  const p = state.prompts.get('guard:tree')
  assert.ok(p, 'the guard must be dispatched')
  assert.ok(p.includes('git -C ~/flakes/dsh-harness status --porcelain'), 'the guard checks the harness repo')
  assert.doesNotMatch(p, /current workspace/, 'the guard no longer inspects the factory-root cwd')
})

test('logs a warning carrying the dirty paths when the harness tree is dirty', async () => {
  const { state, run } = makeRunner(' M src/api.mjs\n?? scratch.txt')
  await run({ goal: 'g', mode: 'build', tasks: [T()] })

  const warn = state.logs.find((l) => l.startsWith('WARNING: shared harness tree'))
  assert.ok(warn, 'a dirty harness tree must produce a warning')
  assert.ok(warn.includes('src/api.mjs'), 'the warning must carry the dirty paths')
})

test('does not warn when the guard reports a clean tree (or fails to report)', async () => {
  for (const out of ['clean', ' clean ', '', null]) {
    const { state, run } = makeRunner(out)
    await run({ goal: 'g', mode: 'build', tasks: [T()] })
    assert.equal(
      state.logs.some((l) => l.startsWith('WARNING:')),
      false,
      'guard output ' + JSON.stringify(out) + ' must not warn'
    )
  }
})

test('treats a fatal: reply as "could not check", not a dirty tree', async () => {
  const { state, run } = makeRunner('fatal: not a git repository (or any of the parent directories): .git')
  await run({ goal: 'g', mode: 'build', tasks: [T()] })

  assert.equal(
    state.logs.some((l) => l.startsWith('WARNING:')),
    false,
    'a fatal: reply must not be reported as a dirty tree'
  )
  assert.ok(
    state.logs.some((l) => l.startsWith('guard: could not check the harness tree')),
    'a fatal: reply is reported distinctly as "could not check"'
  )
})

test('matches fatal: anywhere, so a prefixed guard reply is still "could not check"', async () => {
  const { state, run } = makeRunner('note: fatal: not a git repository (or any of the parent directories): .git')
  await run({ goal: 'g', mode: 'build', tasks: [T()] })

  assert.equal(
    state.logs.some((l) => l.startsWith('WARNING:')),
    false,
    'a prefixed fatal: reply must not be reported as a dirty tree'
  )
  assert.ok(
    state.logs.some((l) => l.startsWith('guard: could not check the harness tree')),
    'a prefixed fatal: reply is reported distinctly as "could not check"'
  )
})
