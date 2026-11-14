#!/usr/bin/env node
import { resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const isEntrypoint = Boolean(process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href);
let configureSystemOneMain;
try {
  ({ configureSystemOneMain } = await import('./scripts/configure-system1.mjs'));
} catch {
  if (!isEntrypoint) throw new Error('System 1: initialization_failed');
}

export { configureSystemOneMain };

export async function waitForSystemOneLauncherExit(input, output) {
  if (!input.isTTY || !output.isTTY || typeof input.setRawMode !== 'function' ||
      input.destroyed || input.readableEnded) return;
  const wasRaw = Boolean(input.isRaw);
  const wasFlowing = input.readableFlowing === true;
  let complete;
  const ended = new Promise(resolvePromise => { complete = resolvePromise; });
  function onData(chunk) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    if ([3, 4, 10, 13].some(character => bytes.includes(character))) complete();
  }
  try {
    input.setRawMode(true);
    input.on('data', onData);
    input.once('end', complete);
    input.once('close', complete);
    input.once('error', complete);
    output.write('\n\u6309 Enter \u7ee7\u7eed...');
    input.resume();
    await ended;
  } finally {
    input.removeListener('data', onData);
    input.removeListener('end', complete);
    input.removeListener('close', complete);
    input.removeListener('error', complete);
    try { input.setRawMode(wasRaw); }
    finally {
      if (wasFlowing) input.resume();
      else input.pause();
      output.write('\n');
    }
  }
}

export async function runSystemOneLauncher(argv, {
  input = process.stdin, output = process.stdout, errorOutput = process.stderr,
  env = process.env, main = configureSystemOneMain, waitForExit = waitForSystemOneLauncherExit
} = {}) {
  const json = Array.isArray(argv) && argv.includes('--json');
  let exitCode = 1;
  try {
    if (typeof main !== 'function') {
      if (json) output.write(`${JSON.stringify({ status: 'error', reason_code: 'initialization_failed' })}\n`);
      else errorOutput.write('System 1: initialization_failed\n' +
        '\u914d\u7f6e\u5de5\u5177\u542f\u52a8\u5931\u8d25\uff0c\u8bf7\u91cd\u65b0\u5b89\u88c5\u5b8c\u6574\u63d2\u4ef6\u540e\u518d\u8bd5\u3002\n');
    } else {
      exitCode = await main(argv, { input, output, errorOutput, env });
      // The Windows launcher is the single operator entry point. Replicate a
      // successfully saved configuration to each installed WSL runtime.
      const mutating = argv.length === 0 || argv.includes('menu') || argv.includes('configure') ||
        argv.includes('off') || argv.some(value => [
          '--mode', '--url', '--protocol', '--request-model', '--key-stdin', '--key-env',
          '--calibration-profile', '--profile', '--provider', '--provider-version',
          '--model', '--model-version'
        ].includes(value));
      const readOnly = !mutating;
      if (exitCode === 0 && main === configureSystemOneMain && !readOnly &&
          process.platform === 'win32' && env.OPLWU_SKIP_WSL_SYNC !== '1') {
        const { createSystemOneConfigStore } = await import('./mcp/systemone-config.mjs');
        const { syncWslConfig, formatWslSyncFailure } = await import('./scripts/wsl-runtime.mjs');
        const store = createSystemOneConfigStore({ home: env.ARGON_HOME });
        const config = store.read();
        let apiKey;
        if (config.credential_ref) apiKey = await store.readCredential(config);
        else if (config.allow_unauthenticated_loopback) apiKey = '';
        const wsl = syncWslConfig({
          sourceRoot: fileURLToPath(new URL('.', import.meta.url)),
          env,
          bundle: {
            api_url: config.api_url, protocol: config.protocol,
            request_model: config.request_model, wire_profile: config.wire_profile,
            mode: config.mode, remote_consent: config.remote_consent,
            service_identity: config.service_identity, apiKey
          }
        });
        if (wsl.failures.length) {
          if (argv.includes('--json')) {
            // Keep the local command's JSON contract to one stdout document.
            errorOutput.write('System 1: wsl_sync_failed\n');
          } else {
            errorOutput.write(`WSL 配置同步失败：${formatWslSyncFailure(wsl)}\n`);
          }
          exitCode = 1;
        } else if (wsl.attempted && !argv.includes('--json')) {
          output.write(`已同步 System 1 配置到 WSL：${wsl.distros.join('、')}\n`);
        }
      }
    }
  } catch {
    if (json) output.write(`${JSON.stringify({ status: 'error', reason_code: 'configuration_failed' })}\n`);
    else errorOutput.write('System 1: configuration_failed\n' +
      '\u914d\u7f6e\u5de5\u5177\u53d1\u751f\u9519\u8bef\uff0c\u8bf7\u91cd\u65b0\u6253\u5f00\u540e\u518d\u8bd5\u3002\n');
  }
  const menu = Array.isArray(argv) && (argv.length === 0 || argv.length === 1 && argv[0] === 'menu');
  if (!json && env.OPLWU_SYSTEM1_BATCH_LAUNCH === '1' && input.isTTY && output.isTTY &&
      (!menu || exitCode !== 0)) {
    // Waiting is a batch-window convenience, never part of the command's result.
    try { await waitForExit(input, output); } catch {}
  }
  return exitCode;
}

if (isEntrypoint) {
  process.exitCode = await runSystemOneLauncher(process.argv.slice(2));
}
