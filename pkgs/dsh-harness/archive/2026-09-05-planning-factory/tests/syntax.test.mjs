import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = readFileSync(join(here, '..', 'dark-factory.js'), 'utf8')

// The workflow tool runs `factory/dark-factory.js` as an async-function body with the
// tool globals (`agent`, `parallel`, `pipeline`, `log`, `phase`, `args`) in scope, so a
// bare `node --check` on the file is not meaningful (top-level `await` + `return` are
// valid only in that async-function context, not in a script or module). The honest
// syntax gate is therefore to construct the AsyncFunction the way the tool does: a
// syntax error in the body throws here, which is exactly the signal we need.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

test('dark-factory.js parses as a workflow async-function body', () => {
  const fn = new AsyncFunction('agent', 'parallel', 'pipeline', 'log', 'phase', 'args', SCRIPT)
  assert.equal(typeof fn, 'function', 'the script body must construct a callable async function')
})
