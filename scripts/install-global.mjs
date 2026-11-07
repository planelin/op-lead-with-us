import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync, rmSync, copyFileSync, lstatSync } from 'node:fs';
import { join, resolve, dirname, relative, sep, isAbsolute } from 'node:path';
import { homedir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { projectRoot, packageFiles, validatePlugin, agentNames, leadAgentNames } from './validate.mjs';

const hash = data => createHash('sha256').update(data).digest('hex');
const marker = '.op-lead-with-us-installed.json';

const globalConfigDir = join(homedir(), '.gemini', 'config');
const globalPluginDir = join(globalConfigDir, 'plugins', 'op-lead-with-us');
const legacyPluginDir = join(globalConfigDir, 'plugins', 'opus-staff');
const globalAgentsDir = join(globalConfigDir, 'agents');

// Only retire the known renamed agent, and only when installation hashes prove
// its contents are unchanged. Merely finding an unrecognised .md is not ownership.
export function planTurboRename(pluginDir, agentsDir) {
  const retiredRelative = 'agents/op-lead-with-crychic.md';
  const retiredName = 'op-lead-with-crychic.md';
  const paths = [];
  const manifestPath = join(pluginDir, marker);
  const prior = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, 'utf8')) : null;
  if (prior) assert(prior.format === 1 && prior.files && typeof prior.files === 'object', 'Invalid installation manifest');
  const expectedHash = prior?.files[retiredRelative];
  function checkTarget(root, destination) {
    root = resolve(root);
    destination = resolve(destination);
    const rel = relative(root, destination);
    assert(rel && rel !== '..' && !rel.startsWith(`..${sep}`) && !isAbsolute(rel), 'Rename target must stay within installation directory');
    // Check ancestors too: an installation directory reached through a junction
    // must not redirect migration outside the named target tree.
    let current = destination;
    while (true) {
      if (existsSync(current)) assert(!lstatSync(current).isSymbolicLink(), `Refusing symlink/junction: ${current}`);
      const parent = dirname(current);
      if (parent === current) break;
      current = parent;
    }
    assert(lstatSync(destination).isFile(), `Expected retired agent file: ${destination}`);
    assert(typeof expectedHash === 'string' && hash(readFileSync(destination)) === expectedHash,
      `Refusing to remove modified or untracked legacy Turbo agent; back it up and reconcile manually: ${destination}`);
    paths.push(destination);
  }
  if (existsSync(join(pluginDir, 'agents'))) {
    for (const name of readdirSync(join(pluginDir, 'agents'))) {
      if (name.endsWith('.md') && !agentNames.includes(name.slice(0, -3))) {
        assert(name === retiredName, `Unexpected deployed agent; preserving it: ${name}`);
        checkTarget(pluginDir, join(pluginDir, 'agents', name));
      }
    }
  }
  const standalone = join(agentsDir, retiredName);
  if (existsSync(standalone)) checkTarget(agentsDir, standalone);
  return paths;
}

function uninstall() {
  console.log('--- op-lead-with-us 全局卸载 ---');
  let removedAny = false;

  for (const dir of [globalPluginDir, legacyPluginDir]) {
    if (existsSync(dir)) {
      console.log(`正在移除全局插件目录: ${dir}`);
      rmSync(dir, { recursive: true, force: true });
      removedAny = true;
    }
  }

  // 检查并清理全局 agents 中的 lead 与 worker 副本
  if (existsSync(globalAgentsDir)) {
    // 'op-lead-with-crychic' was renamed to 'op-lead-with-cry'; keep removing its leftover file.
    const candidateNames = [...agentNames, 'opus-staff-lead', 'op-lead-with-crychic'];
    for (const name of candidateNames) {
      const agentFile = join(globalAgentsDir, `${name}.md`);
      if (existsSync(agentFile)) {
        console.log(`正在移除全局 Agent: ${agentFile}`);
        rmSync(agentFile, { force: true });
        removedAny = true;
      }
    }
  }

  if (removedAny) {
    console.log('✅ 全局卸载完成。');
  } else {
    console.log('未检测到已安装的全局组件，无需操作。');
  }
}

function install() {
  console.log('--- op-lead-with-us 全局安装 ---');
  validatePlugin(projectRoot);
  console.log('PASS 静态配置校验通过');
  // Finish rename preflight before modifying the installed tree or global agents.
  const retiredTurboFiles = planTurboRename(globalPluginDir, globalAgentsDir);

  // 清理旧版 opus-staff 残留
  if (existsSync(legacyPluginDir)) {
    console.log(`清理旧版插件目录: ${legacyPluginDir}`);
    rmSync(legacyPluginDir, { recursive: true, force: true });
  }
  const legacyLead = join(globalAgentsDir, 'opus-staff-lead.md');
  if (existsSync(legacyLead)) {
    console.log(`清理旧版 Lead Agent: ${legacyLead}`);
    rmSync(legacyLead, { force: true });
  }
  // The exact absolute targets and hashes were checked above; never prune unknown agents.
  for (const file of retiredTurboFiles) {
    console.log(`清理已验证未修改的旧版 Turbo Agent: ${file}`);
    rmSync(file);
  }

  // 1. 部署到 ~/.gemini/config/plugins/op-lead-with-us
  mkdirSync(globalPluginDir, { recursive: true });
  const fileHashes = {};

  for (const file of packageFiles) {
    const src = join(projectRoot, file);
    const dest = join(globalPluginDir, file);
    mkdirSync(dirname(dest), { recursive: true });
    const content = readFileSync(src);
    writeFileSync(dest, content);
    fileHashes[file] = hash(content);
  }

  // 验证全局安装副本；在写入成功标记前执行，失败时不留下“已安装”的假象
  validatePlugin(globalPluginDir);
  console.log('PASS 全局副本静态校验通过');

  // 写入安装清单标记
  writeFileSync(
    join(globalPluginDir, marker),
    JSON.stringify({ format: 1, installedAt: new Date().toISOString(), files: fileHashes }, null, 2) + '\n'
  );
  console.log(`✅ 插件核心已安装至: ${globalPluginDir}`);

  // 2. 将主协调员（op-lead-with-us 与 op-lead-with-cry）部署到 ~/.gemini/config/agents/，确保 Antigravity 主下拉框全局可见
  mkdirSync(globalAgentsDir, { recursive: true });
  for (const leadName of leadAgentNames) {
    const leadSrc = join(projectRoot, 'agents', `${leadName}.md`);
    const leadDest = join(globalAgentsDir, `${leadName}.md`);
    copyFileSync(leadSrc, leadDest);
    console.log(`✅ 主 Agent 已注册至全局 Agent 列表: ${leadDest}`);
  }

  // 验证全局 agents 目录中的 Lead 副本存在
  for (const leadName of leadAgentNames) {
    const leadDest = join(globalAgentsDir, `${leadName}.md`);
    assert(existsSync(leadDest), `Lead agent missing after install: ${leadDest}`);
  }

  console.log('\n=========================================');
  console.log('🎉 op-lead-with-us 全局安装成功！');
  console.log('使用方法：');
  console.log('1. 重启或在 Antigravity 桌面端新建对话 (Ctrl+N)');
  console.log('2. Agent 选择器: op-lead-with-us（节省主模型额度）或 op-lead-with-cry（并发增速）');
  console.log('3. 手动选择主模型: US 推荐 Opus；CRY 推荐 Flash。插件不自动切换或验证主模型。');
  console.log('4. 省额度可先在 Opus 会话 PLAN_ONLY 生成 PLAN.md，再新开 Flash 会话执行 Execute PLAN.md');
  console.log('=========================================\n');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const isUninstall = process.argv.includes('--uninstall') || process.argv.includes('-u');
  try {
    if (isUninstall) {
      uninstall();
    } else {
      install();
    }
  } catch (error) {
    console.error(`FAIL 安装操作失败: ${error.message}`);
    process.exitCode = 1;
  }
}

export { install, uninstall };
