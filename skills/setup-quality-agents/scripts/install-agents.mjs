#!/usr/bin/env node
// Register project-scoped native agents without changing host permission settings.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const roles = JSON.parse(fs.readFileSync(path.join(root, 'assets/roles.json'), 'utf8'));

export function agentText(role, host) {
  if (host === 'claude-code') {
    const tools = role.readonly ? 'Read, Grep, Glob' : 'Read, Grep, Glob, Edit, Write, Bash';
    return `---\nname: ${role.name}\ndescription: ${JSON.stringify(role.description)}\ntools: ${tools}\nmodel: inherit\n---\n\n${role.prompt}\n`;
  }
  if (host === 'codex') {
    // JSON basic strings are valid TOML basic strings for these bundled values.
    return `name = ${JSON.stringify(role.name)}\ndescription = ${JSON.stringify(role.description)}\n${role.readonly ? 'sandbox_mode = "read-only"\n' : ''}developer_instructions = ${JSON.stringify(role.prompt)}\n`;
  }
  throw Error('Host must be claude-code or codex');
}

export function install(target, host, dryRun = false) {
  if (!['claude-code', 'codex'].includes(host)) throw Error('Choose --host claude-code or codex');
  const repo = fs.realpathSync(path.resolve(target));
  if (!fs.statSync(repo).isDirectory()) throw Error('Target must be a project directory');
  const relative = host === 'codex' ? '.codex/agents' : '.claude/agents';
  const dest = path.join(repo, relative);
  // Reject symlinked configuration paths, including dangling links.
  for (const item of [path.dirname(dest), dest]) {
    try { if (fs.lstatSync(item).isSymbolicLink()) throw Error(`Refusing symlink: ${item}`); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  const entries = roles.map(role => ({ path: path.join(dest, `${role.name}.${host === 'codex' ? 'toml' : 'md'}`), content: agentText(role, host) }));
  // Preflight all files before creating any: reruns preserve user customizations.
  for (const entry of entries) {
    try {
      const st = fs.lstatSync(entry.path);
      if (!st.isFile() || st.isSymbolicLink() || fs.readFileSync(entry.path, 'utf8') !== entry.content) {
        throw Error(`Existing custom agent differs; no files changed: ${entry.path}`);
      }
      entry.exists = true;
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  if (!dryRun) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of entries) if (!entry.exists) fs.writeFileSync(entry.path, entry.content, { flag: 'wx' });
  }
  return entries.map(entry => ({ path: entry.path, status: entry.exists ? 'unchanged' : dryRun ? 'would-create' : 'created' }));
}

export function main(args) {
  let target, host, dryRun = false;
  for (let i = 0; i < args.length; i++) {
    if (['--target', '--host'].includes(args[i])) {
      const key = args[i], value = args[++i];
      if (!value || value.startsWith('--')) throw Error(`Missing value for ${key}`);
      if (key === '--target') target = value; else host = value;
    } else if (args[i] === '--dry-run') dryRun = true;
    else throw Error(`Unknown argument: ${args[i]}`);
  }
  if (!target || !host) throw Error('Usage: --target PROJECT --host claude-code|codex [--dry-run]');
  console.log(JSON.stringify(install(target, host, dryRun), null, 2));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
