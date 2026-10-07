import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync, rmSync, copyFileSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { homedir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { projectRoot, packageFiles, validatePlugin, agentNames } from './validate.mjs';

const hash = data => createHash('sha256').update(data).digest('hex');
const marker = '.op-lead-with-us-installed.json';

const globalConfigDir = join(homedir(), '.gemini', 'config');
const globalPluginDir = join(globalConfigDir, 'plugins', 'op-lead-with-us');
const legacyPluginDir = join(globalConfigDir, 'plugins', 'opus-staff');
const globalAgentsDir = join(globalConfigDir, 'agents');

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
    const candidateNames = [...agentNames, 'opus-staff-lead'];
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

  // 写入安装清单标记
  writeFileSync(
    join(globalPluginDir, marker),
    JSON.stringify({ format: 1, installedAt: new Date().toISOString(), files: fileHashes }, null, 2) + '\n'
  );
  console.log(`✅ 插件核心已安装至: ${globalPluginDir}`);

  // 2. 将 op-lead-with-us 部署到 ~/.gemini/config/agents/，确保 Antigravity 主下拉框全局可见
  mkdirSync(globalAgentsDir, { recursive: true });
  const leadSrc = join(projectRoot, 'agents', 'op-lead-with-us.md');
  const leadDest = join(globalAgentsDir, 'op-lead-with-us.md');
  copyFileSync(leadSrc, leadDest);
  console.log(`✅ 主 Agent 已注册至全局 Agent 列表: ${leadDest}`);

  // 验证全局安装副本
  validatePlugin(globalPluginDir);
  console.log('PASS 全局副本静态校验通过');

  console.log('\n=========================================');
  console.log('🎉 op-lead-with-us 全局安装成功！');
  console.log('使用方法：');
  console.log('1. 重启或在 Antigravity 桌面端新建对话 (Ctrl+N)');
  console.log('2. Agent 选择器选择: op-lead-with-us');
  console.log('3. 模型选择器按会话类型选择: Claude Opus 5.5（复杂规划/验收）或 Gemini 3.8 Flash（简单任务/Execute PLAN.md）');
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
