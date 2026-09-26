import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// F11 — trailer drift. Commits in this repo used to mix a bare `Generated-By`
// line with an also-present `Co-Authored-By` line (the F4-era convention), so
// the record is inconsistent. The convention is now: exactly ONE
// `Generated-By: <harness> / <model> (<context>)` trailer, machine-set from the
// run's args (harness identity + context) and the task's role→model id, and no
// `Co-Authored-By` line at all. This test asserts the commit-message template
// the factory renders through its implementer prompt carries exactly that.
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
    if (label.startsWith('judge:')) return { paths: [] }
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

test('the commit template carries exactly one Generated-By trailer and no Co-Authored-By', async () => {
  const { state, run } = makeRunner()
  await run({ goal: 'g', mode: 'build', tasks: [TASK()] })
  const prompt = state.prompts.get('impl:T1')
  assert.ok(prompt, 'the implementer must be dispatched')
  // A real Co-Authored-By trailer is a line that STARTS with the key; the prompt
  // may legitimately tell the implementer to add "no Co-Authored-By line", so the
  // assertion targets the trailer key at line start, not the bare word.
  assert.doesNotMatch(prompt, /^Co-Authored-By:/m, 'no Co-Authored-By trailer line may remain')
  const count = (prompt.match(/Generated-By:/g) || []).length
  assert.equal(count, 1, 'exactly one Generated-By trailer must be stated')
})

test('the Generated-By trailer is machine-set: harness, model id, and context, no placeholder', async () => {
  const { state, run } = makeRunner()
  await run({
    goal: 'g',
    mode: 'build',
    harness: 'dsh X.Y.Z',
    factoryContext: 'seat test, factory run bX',
    tasks: [TASK({ role: 'deepseekPro' })],
  })
  const prompt = state.prompts.get('impl:T1')
  assert.match(
    prompt,
    /Generated-By: dsh X\.Y\.Z \/ deepseek\/deepseek-v4-pro-0813 \(seat test, factory run bX\)/,
    'the harness, model id, and context are all substituted verbatim'
  )
  assert.doesNotMatch(
    prompt,
    /<harness>|<model>|<context>|<model id>/,
    'no placeholder remains for the implementer to fill in'
  )
})

test('the trailer model id follows the task role, not a fixed string', async () => {
  const { state, run } = makeRunner()
  await run({ goal: 'g', mode: 'build', tasks: [TASK({ role: 'glm' })] })
  const prompt = state.prompts.get('impl:T1')
  assert.match(
    prompt,
    /Generated-By: [^/]+ \/ z-ai\/glm-5\.3 \(/,
    'a glm task carries the glm model id'
  )
})