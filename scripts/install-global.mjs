import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync, rmSync, copyFileSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { homedir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { projectRoot, packageFiles, validatePlugin, agentNames } from './validate.mjs';

const hash = data => createHash('sha256').update(data).digest('hex');
const marker = '.opus-staff-installed.json';

const globalConfigDir = join(homedir(), '.gemini', 'config');
const globalPluginDir = join(globalConfigDir, 'plugins', 'opus-staff');
const globalAgentsDir = join(globalConfigDir, 'agents');

function uninstall() {
  console.log('--- Opus Staff 全局卸载 ---');
  let removedAny = false;

  if (existsSync(globalPluginDir)) {
    console.log(`正在移除全局插件目录: ${globalPluginDir}`);
    rmSync(globalPluginDir, { recursive: true, force: true });
    removedAny = true;
  }

  // 检查并清理全局 agents 中的 lead 与 worker 副本
  if (existsSync(globalAgentsDir)) {
    for (const name of agentNames) {
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
  console.log('--- Opus Staff 全局安装 ---');
  validatePlugin(projectRoot);
  console.log('PASS 静态配置校验通过');

  // 1. 部署到 ~/.gemini/config/plugins/opus-staff
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

  // 2. 将 opus-staff-lead 部署到 ~/.gemini/config/agents/，确保 Antigravity 主下拉框全局可见
  mkdirSync(globalAgentsDir, { recursive: true });
  const leadSrc = join(projectRoot, 'agents', 'opus-staff-lead.md');
  const leadDest = join(globalAgentsDir, 'opus-staff-lead.md');
  copyFileSync(leadSrc, leadDest);
  console.log(`✅ 主 Agent 已注册至全局 Agent 列表: ${leadDest}`);

  // 验证全局安装副本
  validatePlugin(globalPluginDir);
  console.log('PASS 全局副本静态校验通过');

  console.log('\n=========================================');
  console.log('🎉 Opus Staff 全局安装成功！');
  console.log('使用方法：');
  console.log('1. 重启或在 Antigravity 桌面端新建对话');
  console.log('2. Agent 选择器选择: opus-staff-lead');
  console.log('3. 模型选择器选择: Claude Opus 5.5');
  console.log('4. 发送任务，Lead 将自动规划并委派 Flash 完成实现！');
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
