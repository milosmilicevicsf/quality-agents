#!/usr/bin/env node
// Standalone HTML renderer. It never runs tests, calls models, or loads remote assets.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const escape = (value) => String(value).replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[c]));
const text = (value, label, empty = false) => {
  if (typeof value !== 'string' || (!empty && !value.trim())) throw Error(`${label} must be text`);
};
const choice = (value, options, label) => {
  if (!options.includes(value)) throw Error(`Invalid ${label}: ${value}`);
};
const list = (value, label) => {
  if (!Array.isArray(value) || value.length > 500) throw Error(`${label} must be an array (maximum 500)`);
};

export function validate(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw Error('Report must be an object');
  for (const key of ['project', 'task', 'revision', 'summary', 'scope']) text(data[key], key);
  choice(data.mode, ['analyze', 'build', 'triage'], 'mode');
  choice(data.status, ['review-needed', 'blocked'], 'status');
  choice(data.execution_model, ['delegated', 'blocked', 'example'], 'execution_model');
  list(data.agents, 'agents');
  const workerIds = new Set(), workerRoles = new Set();
  for (const worker of data.agents) {
    choice(worker.role, ['risk-analyst', 'test-engineer', 'quality-reviewer'], 'agent role');
    choice(worker.status, ['completed', 'blocked', 'failed'], 'agent status');
    text(worker.session_id, 'Host agent id');
    text(worker.summary, 'Agent summary');
    if (workerIds.has(worker.session_id) || workerRoles.has(worker.role)) throw Error('Worker identities and roles must be distinct');
    workerIds.add(worker.session_id); workerRoles.add(worker.role);
  }
  if (data.execution_model === 'delegated' && data.agents.length !== 3) throw Error('Delegated workflow requires three worker identities');
  if ((data.execution_model === 'blocked' || data.agents.some(a => a.status !== 'completed')) && data.status !== 'blocked') {
    throw Error('Incomplete or failed delegation must be shown as blocked');
  }
  for (const key of ['scenarios', 'checks', 'findings', 'next_actions', 'limitations']) list(data[key], key);
  for (const item of [...data.next_actions, ...data.limitations]) text(item, 'Action/limitation');
  if (!data.next_actions.length) throw Error('At least one next action is required');
  const ids = new Set();
  for (const row of data.scenarios) {
    for (const key of ['id', 'behavior', 'oracle', 'evidence']) text(row[key], `Scenario ${key}`);
    if (ids.has(row.id)) throw Error('Duplicate scenario id');
    ids.add(row.id);
    choice(row.priority, ['critical', 'high', 'medium', 'low'], 'priority');
    choice(row.layer, ['unit', 'component', 'api', 'integration', 'e2e', 'manual', 'eval'], 'layer');
    choice(row.coverage, ['covered', 'partial', 'missing', 'unknown'], 'coverage');
  }
  for (const row of data.checks) {
    text(row.name, 'Check name');
    choice(row.status, ['passed', 'failed', 'timeout', 'not-run'], 'check status');
    text(row.command, 'Check command', row.status === 'not-run');
    text(row.evidence, 'Check evidence or reason not run');
    list(row.scenario_ids, 'Check scenario_ids');
    for (const id of row.scenario_ids) if (!ids.has(id)) throw Error(`Unknown scenario id: ${id}`);
  }
  for (const row of data.findings) {
    for (const key of ['title', 'evidence', 'next_action']) text(row[key], `Finding ${key}`);
    choice(row.classification, ['product', 'test', 'environment', 'data', 'suspected-flaky', 'unknown'], 'classification');
    choice(row.confidence, ['low', 'medium', 'high'], 'confidence');
  }
  return data;
}

const badge = (value) => `<span class="badge ${escape(value)}">${escape(value.replaceAll('-', ' '))}</span>`;
const bulletList = (items) => `<ul>${items.map(x => `<li>${escape(x)}</li>`).join('')}</ul>`;

export function render(data) {
  validate(data);
  const run = data.checks.filter(x => x.status !== 'not-run');
  const failed = run.filter(x => ['failed', 'timeout'].includes(x.status));
  const gaps = data.scenarios.filter(x => ['missing', 'partial'].includes(x.coverage));
  const unknown = data.scenarios.filter(x => x.coverage === 'unknown');
  const scenarios = data.scenarios.length ? data.scenarios.map(row => `<article class="scenario">
    <div class="scenario-head"><span class="mono">${escape(row.id)}</span>${badge(row.priority)}${badge(row.layer)}${badge(row.coverage)}</div>
    <h3>${escape(row.behavior)}</h3><p><strong>Expected outcome</strong> ${escape(row.oracle)}</p>
    <details><summary>Inspect evidence</summary><pre>${escape(row.evidence)}</pre></details></article>`).join('')
    : '<p class="empty">No scenario map was produced for this task. This does not establish coverage.</p>';
  const checks = data.checks.length ? data.checks.map(row => `<article class="check">
    <div class="row">${badge(row.status)}<h3>${escape(row.name)}</h3></div>
    <p class="mono muted">${escape(row.scenario_ids.join(' · ') || 'No scenario mapping')}</p>
    ${row.command ? `<pre class="command">${escape(row.command)}</pre>` : ''}
    <details open><summary>${row.status === 'not-run' ? 'Why this was not run' : 'Execution evidence'}</summary><pre>${escape(row.evidence)}</pre></details></article>`).join('')
    : '<p class="empty">No commands were run or recorded. Analysis is not a test execution result.</p>';
  const findings = data.findings.length ? data.findings.map(row => `<article class="check">
    <div class="row">${badge(row.classification)}<span class="muted">${escape(row.confidence)} confidence</span></div>
    <h3>${escape(row.title)}</h3><pre>${escape(row.evidence)}</pre>
    <p><strong>Next investigation</strong> ${escape(row.next_action)}</p></article>`).join('')
    : '<p class="empty">No failure diagnosis recorded. This is not a claim that the feature is defect-free.</p>';
  const workerState = role => data.agents.find(a => a.role === role)?.status ?? 'Not started';
  const agents = data.agents.length ? data.agents.map(a => `<article class="check"><div class="row">${badge(a.role)}${badge(a.status)}</div>
    <p>${escape(a.summary)}</p><p class="mono muted">Host agent id: ${escape(a.session_id)}</p></article>`).join('')
    : `<p class="empty">${data.execution_model === 'example' ? 'Illustrative preview. No agents ran.' : 'No worker was started. See limitations for the delegation blocker.'}</p>`;
  const values = {
    TITLE: escape(`${data.project} — Quality Flow`), PROJECT: escape(data.project), TASK: escape(data.task),
    MODE: escape(data.mode), STATUS: escape(data.status.replaceAll('-', ' ')), SUMMARY: escape(data.summary),
    REVISION: escape(data.revision), SCOPE: escape(data.scope), DATE: escape(new Date().toISOString()),
    SCENARIO_COUNT: String(data.scenarios.length), GAP_COUNT: String(gaps.length), UNKNOWN_COUNT: String(unknown.length),
    RUN_COUNT: run.length ? String(run.length) : 'Not run', FAIL_COUNT: run.length ? String(failed.length) : '—',
    RISK_STATE: escape(workerState('risk-analyst')),
    BUILD_STATE: escape(workerState('test-engineer')),
    FAILURE_STATE: escape(workerState('quality-reviewer')),
    SCENARIOS: scenarios, CHECKS: checks, FINDINGS: findings, AGENTS: agents,
    EXECUTION_MODEL: escape(data.execution_model),
    ACTIONS: bulletList(data.next_actions), LIMITATIONS: data.limitations.length ? bulletList(data.limitations)
      : '<p>No additional limitations recorded. Human review is still required.</p>'
  };
  return fs.readFileSync(path.join(root, 'assets/report.html'), 'utf8')
    .replace(/\{\{([A-Z_]+)\}\}/g, (_, key) => {
      if (!(key in values)) throw Error(`Unknown template field: ${key}`);
      return values[key];
    });
}

export function main(args) {
  let input, output, example = false, open = false;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--input' || args[i] === '--output') {
      const key = args[i];
      const value = args[++i];
      if (!value || value.startsWith('--')) throw Error(`Missing value for ${key}`);
      if (key === '--input') input = value; else output = value;
    } else if (args[i] === '--example') example = true;
    else if (args[i] === '--open') open = true;
    else throw Error(`Unknown argument: ${args[i]}`);
  }
  if (Boolean(input) === example) throw Error('Choose --input report.json or --example');
  const source = example ? path.join(root, 'assets/example.json') : path.resolve(input);
  if (fs.statSync(source).size > 2_000_000) throw Error('Report input exceeds 2 MB');
  const data = JSON.parse(fs.readFileSync(source, 'utf8'));
  const html = render(data);
  const target = output ? path.resolve(output) : path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'quality-flow-')), 'report.html');
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, html, { encoding: 'utf8', flag: 'wx' });
  console.log(target);
  if (open) {
    const launcher = process.platform === 'win32' ? 'explorer.exe' : process.platform === 'darwin' ? 'open' : 'xdg-open';
    const result = spawnSync(launcher, [target], { stdio: 'ignore', timeout: 5000, shell: false });
    if (result.error || result.status !== 0) console.error('Report saved. Open the printed path in your browser.');
  }
  return target;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(`Report error: ${error.message}`); process.exitCode = 1; }
}
