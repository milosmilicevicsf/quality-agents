import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { install, roles } from '../skills/setup-quality-agents/scripts/install-agents.mjs';
import { render, validate } from '../skills/quality-flow/scripts/render-report.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const example = () => JSON.parse(fs.readFileSync(path.join(root, 'skills/quality-flow/assets/example.json'), 'utf8'));
const temp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'qa-skills-test-'));

test('registration creates three native workers for each host and is idempotent', () => {
  const dir = temp();
  try {
    for (const host of ['claude-code', 'codex']) {
      const result = install(dir, host);
      assert.equal(result.length, 3);
      assert.ok(result.every(x => x.status === 'created' && fs.existsSync(x.path)));
      assert.ok(install(dir, host).every(x => x.status === 'unchanged'));
      for (const item of result) {
        const content = fs.readFileSync(item.path, 'utf8');
        assert.ok(!content.includes('bypassPermissions'));
        assert.ok(!content.includes('approval_policy'));
      }
    }
    assert.equal(roles.filter(x => x.readonly).length, 2);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('custom agent conflict does not partially install or overwrite', () => {
  const dir = temp();
  try {
    const folder = path.join(dir, '.claude/agents');
    fs.mkdirSync(folder, { recursive: true });
    const custom = path.join(folder, 'qa-test-engineer.md');
    fs.writeFileSync(custom, 'User custom agent');
    assert.throws(() => install(dir, 'claude-code'), /differs/);
    assert.deepEqual(fs.readdirSync(folder), ['qa-test-engineer.md']);
    assert.equal(fs.readFileSync(custom, 'utf8'), 'User custom agent');
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('dry run performs no writes', () => {
  const dir = temp();
  try {
    assert.ok(install(dir, 'codex', true).every(x => x.status === 'would-create'));
    assert.deepEqual(fs.readdirSync(dir), []);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('symlinked host configuration cannot redirect writes', () => {
  const dir = temp(), outside = temp();
  try {
    fs.symlinkSync(outside, path.join(dir, '.codex'), process.platform === 'win32' ? 'junction' : 'dir');
    assert.throws(() => install(dir, 'codex'), /symlink/);
    assert.deepEqual(fs.readdirSync(outside), []);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); fs.rmSync(outside, { recursive: true, force: true }); }
});

test('unknown host is rejected before writing', () => {
  const dir = temp();
  try { assert.throws(() => install(dir, 'invented')); assert.deepEqual(fs.readdirSync(dir), []); }
  finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('report escapes hostile findings and remains offline without scripts', () => {
  const data = example();
  data.summary = '<script>fetch("https://evil.invalid")</script> & "bad"';
  data.scenarios[0].evidence = '</pre><img src=x onerror=alert(1)>';
  const html = render(data);
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(!html.includes('<script'));
  assert.ok(!html.includes('<img'));
  assert.ok(!html.includes('<link'));
  assert.ok(!html.includes('{{TASK}}'));
  assert.ok(html.includes('No agents ran.'));
  assert.ok(html.includes('Not run'));
});

test('delegated execution requires three distinct host identities', () => {
  const data = example();
  data.execution_model = 'delegated';
  assert.throws(() => validate(data), /three worker/);
  data.agents = ['risk-analyst', 'test-engineer', 'quality-reviewer'].map((role, i) => ({
    role, session_id: 'host-' + i, status: 'completed', summary: 'Inspected task'
  }));
  validate(data);
  data.agents[2].session_id = 'host-1';
  assert.throws(() => validate(data), /distinct/);
});

test('partial delegation is explicitly blocked', () => {
  const data = example(); data.execution_model = 'blocked';
  assert.throws(() => validate(data), /shown as blocked/);
  data.status = 'blocked';
  assert.ok(render(data).includes('No worker was started'));
});

test('passed check requires a command and evidence', () => {
  const data = example(); data.checks[0].status = 'passed';
  assert.throws(() => validate(data), /command/);
  data.checks[0].command = 'python -m unittest'; data.checks[0].evidence = '';
  assert.throws(() => validate(data), /evidence/);
});

test('report rejects unknown scenario mapping and duplicate scenarios', () => {
  const data = example(); data.checks[0].scenario_ids = ['UNKNOWN'];
  assert.throws(() => validate(data), /Unknown scenario/);
  data.checks = []; data.scenarios.push(data.scenarios[0]);
  assert.throws(() => validate(data), /Duplicate scenario/);
});

test('installed skill copy renders without source checkout and preserves existing output', () => {
  const dir = temp();
  try {
    fs.cpSync(path.join(root, 'skills/quality-flow'), path.join(dir, 'skill'), { recursive: true });
    const script = path.join(dir, 'skill/scripts/render-report.mjs');
    const output = path.join(dir, 'saved report.html');
    const args = [script, '--example', '--output', output];
    const first = spawnSync(process.execPath, args, { cwd: os.tmpdir(), encoding: 'utf8' });
    assert.equal(first.status, 0, first.stderr);
    const before = fs.readFileSync(output, 'utf8');
    const second = spawnSync(process.execPath, args, { encoding: 'utf8' });
    assert.notEqual(second.status, 0);
    assert.equal(fs.readFileSync(output, 'utf8'), before);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
