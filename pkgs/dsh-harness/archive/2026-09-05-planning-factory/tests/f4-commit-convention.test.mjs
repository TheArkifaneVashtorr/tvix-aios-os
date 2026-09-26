import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// The workflow tool runs the script body as an async function body with the tool
// globals (`agent`, `parallel`, `pipeline`, `log`, `phase`, `args`) in scope. We
// reproduce that with an AsyncFunction + stubbed globals, and record the prompt
// each dispatch receives so we can assert the implementer prompt carries the exact
// commit convention (subject, WHY body, machine-set trailer) instead of leaving
// any implementer to invent or copy it from `git log`.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

function makeRunner() {
  const state = { prompts: new Map() }
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    state.prompts.set(label, String(prompt))
    if (label.startsWith('guard:tree')) return 'clean'
    if (label.startsWith('impl:')) return 'done'
    if (label === 'baseline:env') return { factoryRootOk: true, cwdUnderRoot: true }
    if (label.startsWith('integrate:')) return { ok: true, merged: [] }
    if (label.startsWith('fix:')) return { ok: true }
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

const TASK = (overrides = {}) => ({
  key: 'T1',
  title: 'A task',
  role: 'glm',
  kind: 'routine',
  spec: 'do the thing',
  dependsOn: [],
  ...overrides,
})

test('implementer prompt states the exact commit subject convention and a WHY body', async () => {
  const { state, run } = makeRunner()
  await run({ goal: 'g', mode: 'build', tasks: [TASK()] })
  const prompt = state.prompts.get('impl:T1')
  assert.ok(prompt, 'the implementer must be dispatched')
  assert.match(
    prompt,
    /<prefix>: <summary> \(test: <check names>\)/,
    'the subject convention is stated verbatim'
  )
  assert.match(prompt, /WHY/, 'the prompt requires a body stating the WHY')
})

test('implementer prompt carries the trailer filled in from the dispatching model id', async () => {
  const { state, run } = makeRunner()
  await run({ goal: 'g', mode: 'build', tasks: [TASK({ role: 'glm' })] })
  const prompt = state.prompts.get('impl:T1')
  assert.match(
    prompt,
    /Generated-By: .+ \/ z-ai\/glm-5\.3 \(/,
    'a glm task carries the glm trailer'
  )
  assert.doesNotMatch(
    prompt,
    /<model id>/,
    'no model has to know or guess its id — the script substitutes it'
  )
})

test('the trailer follows the task role, not a fixed string', async () => {
  const { state, run } = makeRunner()
  await run({ goal: 'g', mode: 'build', tasks: [TASK({ role: 'deepseekPro' })] })
  const prompt = state.prompts.get('impl:T1')
  assert.match(
    prompt,
    /Generated-By: .+ \/ deepseek\/deepseek-v4-pro-0813 \(/,
    'a deepseekPro task carries the deepseekPro trailer'
  )
})
