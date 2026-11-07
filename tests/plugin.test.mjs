import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, copyFileSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { projectRoot, packageFiles, parseFrontmatter, validatePlugin } from '../scripts/validate.mjs';
import { stagePlugin } from '../scripts/stage-plugin.mjs';
import { planTurboRename } from '../scripts/install-global.mjs';
import { createHash } from 'node:crypto';

// Intentionally no recursive deletion. Small, unique test fixtures are left in OS temp.
function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'op-lead-test-'));
  for (const file of packageFiles) {
    mkdirSync(dirname(join(root, file)), { recursive: true });
    copyFileSync(join(projectRoot, file), join(root, file));
  }
  return root;
}
function rewrite(root, file, fn) {
  const path = join(root, file);
  writeFileSync(path, fn(readFileSync(path, 'utf8')));
}

test('source plugin validates', () => assert.equal(validatePlugin().checks.length, 10));
test('CRLF frontmatter is supported', () => {
  const source = readFileSync(join(projectRoot, 'agents/agy-researcher.md'), 'utf8').replace(/\r?\n/g, '\r\n');
  assert.equal(parseFrontmatter(source).metadata.model, 'flash');
});
test('duplicate YAML fields are rejected', () => {
  assert.throws(() => parseFrontmatter(`---\nname: one\nname: two\n---\n${'body '.repeat(30)}`), /duplicate key/);
});
test('unknown manifest properties are rejected', () => {
  const root = fixture();
  rewrite(root, 'plugin.json', s => JSON.stringify({ ...JSON.parse(s), version: '0.1.0' }));
  assert.throws(() => validatePlugin(root), /unsupported or missing keys/);
});
test('worker must not inherit expensive main model', () => {
  const root = fixture();
  rewrite(root, 'agents/agy-implementer.md', s => s.replace('model: flash', 'model: inherit'));
  assert.throws(() => validatePlugin(root), /unexpected model routing/);
});
test('lead must not be callable as a subagent', () => {
  const root = fixture();
  rewrite(root, 'agents/op-lead-with-us.md', s => s.replace('subagent: false', 'subagent: true'));
  assert.throws(() => validatePlugin(root), /wrong delegation flag/);
});
test('unknown tool names are rejected', () => {
  const root = fixture();
  rewrite(root, 'agents/agy-reviewer.md', s => s.replace('  - run_command', '  - made_up_tool'));
  assert.throws(() => validatePlugin(root), /unverified tool/);
});
test('researcher cannot acquire shell access', () => {
  const root = fixture();
  rewrite(root, 'agents/agy-researcher.md', s => s.replace('  - grep_search', '  - grep_search\n  - run_command'));
  assert.throws(() => validatePlugin(root), /tool capabilities changed/);
});
test('invalid rule trigger is rejected', () => {
  const root = fixture();
  rewrite(root, 'rules/op-lead-with-us.md', s => s.replace('trigger: always_on', 'trigger: alwaysOn'));
  assert.throws(() => validatePlugin(root));
});
test('rule without frontmatter is rejected', () => {
  const root = fixture();
  rewrite(root, 'rules/op-lead-with-us.md', s => s.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, ''));
  assert.throws(() => validatePlugin(root), /missing frontmatter/);
});
test('unsafe shell auto-execution policy is rejected', () => {
  const root = fixture();
  rewrite(root, 'agents/agy-implementer.md', s => s.replace('commandExecutionPolicy: sandbox', 'commandExecutionPolicy: eager'));
  assert.throws(() => validatePlugin(root), /unsafe command policy/);
});
test('stage creates a byte-identical workspace install and is idempotent', () => {
  const root = fixture();
  const target = stagePlugin(root);
  for (const file of packageFiles) assert.deepEqual(readFileSync(join(target, file)), readFileSync(join(root, file)));
  assert.equal(validatePlugin(target).checks.length, 10);
  assert.equal(stagePlugin(root), target);
  assert(!existsSync(join(root, '.gemini')));
});
test('stage refuses to overwrite local edits before writing anything', () => {
  const root = fixture();
  const target = stagePlugin(root);
  const path = join(target, 'agents/agy-researcher.md');
  writeFileSync(path, `${readFileSync(path, 'utf8')}\nLocal user edit.\n`);
  rewrite(root, 'plugin.json', s => JSON.stringify({ ...JSON.parse(s), description: 'new description' }));
  const manifestBefore = readFileSync(join(target, 'plugin.json'));
  assert.throws(() => stagePlugin(root), /locally changed staged file/);
  assert.deepEqual(readFileSync(join(target, 'plugin.json')), manifestBefore);
  assert.match(readFileSync(path, 'utf8'), /Local user edit/);
});
test('stage updates managed files after source edits', () => {
  const root = fixture();
  const target = stagePlugin(root);
  rewrite(root, 'README.md', s => `${s}\nSource update.\n`);
  stagePlugin(root);
  assert.match(readFileSync(join(target, 'README.md'), 'utf8'), /Source update/);
});
test('stage rejects unexpected assets without deleting them', () => {
  const root = fixture();
  const target = stagePlugin(root);
  writeFileSync(join(target, 'hooks.json'), '{}');
  assert.throws(() => stagePlugin(root), /Unexpected staged file/);
  assert(existsSync(join(target, 'hooks.json')));
});

test('lead has explicit native delegation and lifecycle tools', () => {
  const { metadata } = parseFrontmatter(readFileSync(join(projectRoot, 'agents/op-lead-with-us.md'), 'utf8'));
  assert.deepEqual(metadata.tools, ['view_file', 'grep_search', 'invoke_subagent', 'manage_subagents', 'send_message']);
});
test('lead missing invoke_subagent is rejected', () => {
  const root = fixture();
  rewrite(root, 'agents/op-lead-with-us.md', s => s.replace('  - invoke_subagent\n', ''));
  assert.throws(() => validatePlugin(root), /Lead must explicitly request/);
});
test('lead missing lifecycle management is rejected', () => {
  const root = fixture();
  rewrite(root, 'agents/op-lead-with-us.md', s => s.replace('  - manage_subagents\n', ''));
  assert.throws(() => validatePlugin(root), /Lead must explicitly request/);
});
test('lead cannot regress to implicit default tools', () => {
  const root = fixture();
  rewrite(root, 'agents/op-lead-with-us.md', s => s.replace(/tools:\n(?:  - [a-z_]+\n)+/, ''));
  assert.throws(() => validatePlugin(root), /unsupported or missing keys/);
});
test('worker cannot gain native delegation tools', () => {
  const root = fixture();
  rewrite(root, 'agents/agy-implementer.md', s => s.replace('  - run_command', '  - run_command\n  - invoke_subagent'));
  assert.throws(() => validatePlugin(root), /tool capabilities changed/);
});
test('lead cannot gain shell tools as implementation fallback', () => {
  const root = fixture();
  rewrite(root, 'agents/op-lead-with-us.md', s => s.replace('  - send_message', '  - send_message\n  - run_command'));
  assert.throws(() => validatePlugin(root), /Lead must explicitly request/);
});
test('lead must define PLAN_ONLY two-phase planning', () => {
  const root = fixture();
  rewrite(root, 'agents/op-lead-with-us.md', s => s.split('PLAN_ONLY').join('TWO_PHASE'));
  assert.throws(() => validatePlugin(root), /PLAN_ONLY two-phase planning/);
});
test('worker report budgets are required', () => {
  const root = fixture();
  rewrite(root, 'agents/agy-researcher.md', s => s.replace('Report budget: 40 lines maximum.', ''));
  assert.throws(() => validatePlugin(root), /missing report budget/);
});
test('two-model policy is pinned in rules', () => {
  const root = fixture();
  rewrite(root, 'rules/op-lead-with-us.md', s => s.replace('Only two models participate', 'Two models participate'));
  assert.throws(() => validatePlugin(root), /two-model policy/);
});

test('cry lead has explicit native delegation and lifecycle tools', () => {
  const { metadata } = parseFrontmatter(readFileSync(join(projectRoot, 'agents/op-lead-with-cry.md'), 'utf8'));
  assert.deepEqual(metadata.tools, ['view_file', 'grep_search', 'invoke_subagent', 'manage_subagents', 'send_message']);
  assert.equal(metadata.model, 'flash');
  assert.equal(metadata.mainAgent, true);
  assert.equal(metadata.subagent, false);
});
test('cry lead must not inherit expensive model', () => {
  const root = fixture();
  rewrite(root, 'agents/op-lead-with-cry.md', s => s.replace('model: flash', 'model: inherit'));
  assert.throws(() => validatePlugin(root), /unexpected model routing/);
});
test('cry lead must not be callable as subagent', () => {
  const root = fixture();
  rewrite(root, 'agents/op-lead-with-cry.md', s => s.replace('subagent: false', 'subagent: true'));
  assert.throws(() => validatePlugin(root), /wrong delegation flag/);
});
// Protocol regressions only: live overlap/refill acceptance is in docs/SMOKE-TEST.md.
test('Turbo rejects unconditional channel or runtime-model guarantees', () => {
  for (const claim of ['strictly reserve 1 channel', 'every participant runs on fast Flash quota']) {
    const root = fixture();
    rewrite(root, 'agents/op-lead-with-cry.md', s => s + '\n' + claim);
    assert.throws(() => validatePlugin(root), /must not guarantee/);
  }
});
test('Turbo cannot silently lose its concurrency-unavailable diagnostic', () => {
  const root = fixture();
  rewrite(root, 'agents/op-lead-with-cry.md', s => s.replaceAll('CONCURRENCY_UNAVAILABLE', 'SERIAL'));
  assert.throws(() => validatePlugin(root), /must disclose unavailable concurrency/);
});
test('Turbo cannot silently lose its scheduler revision marker', () => {
  const root = fixture();
  rewrite(root, 'agents/op-lead-with-cry.md', s => s.replaceAll('CRY_SCHEDULER_V5', 'TURBO_SCHEDULER'));
  assert.throws(() => validatePlugin(root), /must expose its scheduler revision/);
});
test('Turbo fast-track and single-worker disclosure cannot be silently removed', () => {
  for (const [token, pattern] of [
    ['Fast-track exception', /reviewer fast-track/],
    ['user-facing status message', /single-worker reasons/],
    ['LEAD_AUDIT', /scheduling audit/],
  ]) {
    const root = fixture();
    rewrite(root, 'agents/op-lead-with-cry.md', s => s.replaceAll(token, 'REMOVED_TOKEN'));
    assert.throws(() => validatePlugin(root), pattern, token);
  }
});
test('lead preflight diagnostics cannot be silently removed', () => {
  for (const marker of ['LEAD_CONFIG_V2', 'LEAD_TOOLCHECK', 'MISSING_INVOKE_TOOL', 'WORKER_NOT_DISCOVERED']) {
    const root = fixture();
    rewrite(root, 'agents/op-lead-with-us.md', s => s.replaceAll(marker, 'REMOVED_MARKER'));
    assert.throws(() => validatePlugin(root), /capability preflight|capability from discovery failure/, marker);
  }
});
test('shared Turbo protocol rejects missing mode, ownership, dependency and budget fields', () => {
  for (const file of ['agents/op-lead-with-cry.md', 'agents/agy-implementer.md',
    'rules/op-lead-with-us.md', 'skills/op-lead-with-us/SKILL.md']) {
    for (const field of ['orchestration_mode', 'depends_on', 'ready_when', 'shared_resources',
      'repair_budget_total', 'repair_cycles_remaining', 'repair_cycles_used']) {
      const root = fixture();
      rewrite(root, file, s => s.replaceAll(field, 'REMOVED_FIELD'));
      assert.throws(() => validatePlugin(root), /missing Turbo packet field|must track repairs/, file + ': ' + field);
    }
  }
});
test('shared implementer cannot restore the unconditional two-repair cap', () => {
  const root = fixture();
  rewrite(root, 'agents/agy-implementer.md', s => s + '\nnever more than two across the overall task');
  assert.throws(() => validatePlugin(root), /legacy repair cap conflicts with Turbo/);
});
test('staging updates Turbo and shared protocol together without changing other lead', () => {
  const root = fixture();
  const target = stagePlugin(root);
  const originalLead = readFileSync(join(target, 'agents/op-lead-with-us.md'));
  const changed = ['agents/op-lead-with-cry.md', 'agents/agy-implementer.md',
    'rules/op-lead-with-us.md', 'skills/op-lead-with-us/SKILL.md', 'docs/TASK-PACKET.md'];
  for (const file of changed) rewrite(root, file, s => s + '\nUpdated protocol evidence.\n');
  stagePlugin(root);
  for (const file of changed) assert.deepEqual(readFileSync(join(target, file)), readFileSync(join(root, file)));
  assert.deepEqual(readFileSync(join(target, 'agents/op-lead-with-us.md')), originalLead);
});
test('staging preserves edited Turbo before updating any shared instruction', () => {
  const root = fixture();
  const target = stagePlugin(root);
  rewrite(target, 'agents/op-lead-with-cry.md', s => s + '\nUser local Turbo edit.\n');
  const before = new Map(packageFiles.map(file => [file, readFileSync(join(target, file))]));
  rewrite(root, 'agents/agy-implementer.md', s => s + '\nSource worker update.\n');
  assert.throws(() => stagePlugin(root), /locally changed staged file/);
  for (const [file, content] of before) assert.deepEqual(readFileSync(join(target, file)), content);
});
test('stage prunes previously managed staged files that are no longer distributed', () => {
  const root = fixture();
  const target = stagePlugin(root);
  const stalePath = join(target, 'agents/op-lead-with-crychic.md');
  writeFileSync(stalePath, readFileSync(join(root, 'agents/op-lead-with-cry.md')));
  const markerPath = join(target, '.op-lead-with-us-stage.json');
  const manifest = JSON.parse(readFileSync(markerPath, 'utf8'));
  manifest.files['agents/op-lead-with-crychic.md'] = manifest.files['agents/op-lead-with-cry.md'];
  writeFileSync(markerPath, `${JSON.stringify(manifest, null, 2)}\n`);
  stagePlugin(root);
  assert(!existsSync(stalePath));
  assert(!readFileSync(markerPath, 'utf8').includes('crychic'));
});
test('stage still refuses unexpected files it never managed', () => {
  const root = fixture();
  const target = stagePlugin(root);
  writeFileSync(join(target, 'agents/rogue-agent.md'), 'Not staged by this tool.\n');
  assert.throws(() => stagePlugin(root), /Unexpected staged file/);
  assert(existsSync(join(target, 'agents/rogue-agent.md')));
});

function addRetiredStage(target) {
  const rel = 'agents/op-lead-with-crychic.md';
  const content = 'An unchanged historical Turbo agent.\n';
  writeFileSync(join(target, rel), content);
  const markerPath = join(target, '.op-lead-with-us-stage.json');
  const prior = JSON.parse(readFileSync(markerPath, 'utf8'));
  prior.files[rel] = createHash('sha256').update(content).digest('hex');
  writeFileSync(markerPath, JSON.stringify(prior));
  return join(target, rel);
}
test('rename preflight preserves a locally modified retired staged agent', () => {
  const root = fixture();
  const target = stagePlugin(root);
  const retired = addRetiredStage(target);
  writeFileSync(retired, 'User custom Turbo instructions.');
  const manifestBefore = readFileSync(join(target, '.op-lead-with-us-stage.json'));
  const before = new Map(packageFiles.map(f => [f, readFileSync(join(target, f))]));
  assert.throws(() => stagePlugin(root), /locally changed retired staged file/);
  assert.equal(readFileSync(retired, 'utf8'), 'User custom Turbo instructions.');
  assert.deepEqual(readFileSync(join(target, '.op-lead-with-us-stage.json')), manifestBefore);
  for (const [f, data] of before) assert.deepEqual(readFileSync(join(target, f)), data);
});
test('retired files survive when any current payload fails preflight', () => {
  const root = fixture();
  const target = stagePlugin(root);
  const retired = addRetiredStage(target);
  const retiredBefore = readFileSync(retired);
  rewrite(target, 'README.md', s => s + '\nUser README edit.');
  assert.throws(() => stagePlugin(root), /locally changed staged file/);
  assert.deepEqual(readFileSync(retired), retiredBefore);
});
function installedRenameFixture() {
  const root = mkdtempSync(join(tmpdir(), 'op-rename-test-'));
  const plugin = join(root, 'plugins', 'op-lead-with-us');
  const agents = join(root, 'agents');
  mkdirSync(join(plugin, 'agents'), { recursive: true });
  mkdirSync(agents, { recursive: true });
  const content = 'Historical installed Turbo agent.\n';
  const rel = 'agents/op-lead-with-crychic.md';
  const oldPlugin = join(plugin, rel);
  const oldLead = join(agents, 'op-lead-with-crychic.md');
  writeFileSync(oldPlugin, content);
  writeFileSync(oldLead, content);
  const marker = join(plugin, '.op-lead-with-us-installed.json');
  writeFileSync(marker, JSON.stringify({format: 1, files: {[rel]: createHash('sha256').update(content).digest('hex')}}));
  return { plugin, agents, oldPlugin, oldLead, marker };
}
test('global rename plans only verified old names, without changing files', () => {
  const { plugin, agents, oldPlugin, oldLead } = installedRenameFixture();
  assert.deepEqual(planTurboRename(plugin, agents), [oldPlugin, oldLead]);
  assert(existsSync(oldPlugin));
  assert(existsSync(oldLead));
  const root = mkdtempSync(join(tmpdir(), 'op-clean-install-'));
  assert.deepEqual(planTurboRename(join(root, 'plugin'), join(root, 'agents')), []);
});
test('global rename refuses locally modified old plugin or standalone agent', () => {
  for (const field of ['oldPlugin', 'oldLead']) {
    const state = installedRenameFixture();
    writeFileSync(state[field], 'User modified legacy agent.');
    assert.throws(() => planTurboRename(state.plugin, state.agents), /modified or untracked legacy Turbo/);
    assert(existsSync(state.oldPlugin));
    assert(existsSync(state.oldLead));
    assert.equal(readFileSync(state[field], 'utf8'), 'User modified legacy agent.');
  }
});
test('global rename never deletes unrelated deployed agents', () => {
  const state = installedRenameFixture();
  const extra = join(state.plugin, 'agents', 'custom-agent.md');
  writeFileSync(extra, 'User custom agent.');
  assert.throws(() => planTurboRename(state.plugin, state.agents), /Unexpected deployed agent/);
  assert.equal(readFileSync(extra, 'utf8'), 'User custom agent.');
  assert(existsSync(state.oldPlugin));
  assert(existsSync(state.oldLead));
});
test('global rename requires valid ownership metadata', () => {
  for (const metadata of ['{}', '{invalid', JSON.stringify({format: 1, files: {}})]) {
    const state = installedRenameFixture();
    writeFileSync(state.marker, metadata);
    assert.throws(() => planTurboRename(state.plugin, state.agents));
    assert(existsSync(state.oldPlugin));
    assert(existsSync(state.oldLead));
  }
});
test('runtime and user entrypoints expose only the renamed Turbo identifier', () => {
  for (const file of [...packageFiles.filter(f => !f.startsWith('docs/')), 'docs/TASK-PACKET.md', 'docs/QUICKSTART.md', 'install.bat']) {
    assert.doesNotMatch(readFileSync(join(projectRoot, file), 'utf8'), /op-lead-with-crychic|CRYCHIC/, file);
  }
  assert(!existsSync(join(projectRoot, 'agents/op-lead-with-crychic.md')));
  const lead = parseFrontmatter(readFileSync(join(projectRoot, 'agents/op-lead-with-cry.md'), 'utf8'));
  assert.equal(lead.metadata.name, 'op-lead-with-cry');
});
