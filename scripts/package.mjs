import { lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { deflateRawSync } from 'node:zlib';
import assert from 'node:assert/strict';
import { projectRoot, validatePlugin } from './validate.mjs';
import { stagePlugin } from './stage-plugin.mjs';

function computeSha256(filePath) {
  const content = readFileSync(filePath);
  return createHash('sha256').update(content).digest('hex');
}

// Use the same archive implementation on every host. The small ZIP writer
// uses only Node built-ins, so packaging works without PowerShell or `zip`.
const crcTable = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < table.length; n += 1) {
    let value = n;
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value & 1) ? (value >>> 1) ^ 0xedb88320 : value >>> 1;
    }
    table[n] = value >>> 0;
  }
  return table;
})();

function crc32(data) {
  let value = 0xffffffff;
  for (const byte of data) value = (value >>> 8) ^ crcTable[(value ^ byte) & 0xff];
  return (value ^ 0xffffffff) >>> 0;
}

function dosDateTime(date) {
  const year = Math.max(1980, Math.min(2107, date.getFullYear()));
  return {
    time: (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2),
    date: ((year - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate(),
  };
}

function collectFiles(root, excludedPath) {
  const files = [];
  function visit(directory, prefix) {
    for (const entry of readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (!prefix && entry.name === '.op-lead-with-us-stage.json') continue;
      const path = join(directory, entry.name);
      if (path === excludedPath) continue;
      const relativeName = `${prefix}${entry.name}`;
      const stat = lstatSync(path);
      assert(!stat.isSymbolicLink(), `Refusing symlink in package source: ${path}`);
      if (stat.isDirectory()) {
        visit(path, `${relativeName}/`);
      } else if (stat.isFile()) {
        files.push({ path, name: relativeName, modified: stat.mtime });
      } else {
        throw new Error(`Unsupported package source entry: ${path}`);
      }
    }
  }
  visit(root, '');
  return files;
}

function zipHeader(entry, central = false) {
  const name = Buffer.from(entry.name, 'utf8');
  assert(name.length <= 0xffff, `ZIP file name is too long: ${entry.name}`);
  const header = Buffer.alloc(central ? 46 + name.length : 30 + name.length);
  const { time, date } = dosDateTime(entry.modified);
  if (central) {
    header.writeUInt32LE(0x02014b50, 0);
    header.writeUInt16LE(20, 4); // made by
    header.writeUInt16LE(20, 6); // version needed
    header.writeUInt16LE(0x800, 8); // UTF-8 names
    header.writeUInt16LE(8, 10); // deflate
    header.writeUInt16LE(time, 12);
    header.writeUInt16LE(date, 14);
    header.writeUInt32LE(entry.crc, 16);
    header.writeUInt32LE(entry.compressed.length, 20);
    header.writeUInt32LE(entry.data.length, 24);
    header.writeUInt16LE(name.length, 28);
    header.writeUInt32LE(entry.offset, 42);
    name.copy(header, 46);
  } else {
    header.writeUInt32LE(0x04034b50, 0);
    header.writeUInt16LE(20, 4); // version needed
    header.writeUInt16LE(0x800, 6); // UTF-8 names
    header.writeUInt16LE(8, 8); // deflate
    header.writeUInt16LE(time, 10);
    header.writeUInt16LE(date, 12);
    header.writeUInt32LE(entry.crc, 14);
    header.writeUInt32LE(entry.compressed.length, 18);
    header.writeUInt32LE(entry.data.length, 22);
    header.writeUInt16LE(name.length, 26);
    name.copy(header, 30);
  }
  return header;
}

export function writeZipArchive(sourceDir, destination) {
  sourceDir = resolve(sourceDir);
  destination = resolve(destination);
  const entries = collectFiles(sourceDir, destination).map(file => {
    const data = readFileSync(file.path);
    const compressed = deflateRawSync(data);
    assert(data.length <= 0xffffffff && compressed.length <= 0xffffffff,
      `Package file is too large for ZIP32: ${file.path}`);
    return { ...file, data, compressed, crc: crc32(data) };
  });
  assert(entries.length <= 0xffff, 'Too many files for ZIP32 archive');

  const parts = [];
  let offset = 0;
  for (const entry of entries) {
    entry.offset = offset;
    const header = zipHeader(entry);
    parts.push(header, entry.compressed);
    offset += header.length + entry.compressed.length;
  }
  const centralOffset = offset;
  const central = entries.map(entry => zipHeader(entry, true));
  const centralSize = central.reduce((total, part) => total + part.length, 0);
  assert(centralOffset <= 0xffffffff && centralSize <= 0xffffffff,
    'Package is too large for ZIP32 archive');
  parts.push(...central);

  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(centralSize, 12);
  end.writeUInt32LE(centralOffset, 16);
  parts.push(end);
  writeFileSync(destination, Buffer.concat(parts));
  return destination;
}

function createArchive(stagedDir, zipFile) {
  writeZipArchive(stagedDir, zipFile);
}

export function packagePlugin() {
  console.log('--- op-lead-with-us 打包流水线 ---');
  
  // 1. 静态验证
  console.log('[1/4] 运行静态规则与格式校验...');
  validatePlugin(projectRoot);
  console.log('PASS 静态校验通过');

  // 2. 运行单元测试
  console.log('[2/4] 执行回归测试套件...');
  execFileSync(process.execPath, ['--test', join(projectRoot, 'tests', 'plugin.test.mjs')], {
    stdio: 'inherit',
    cwd: projectRoot,
  });
  console.log('PASS 全部单元测试通过');

  // 3. Staging 工作区插件
  console.log('[3/4] 校验并同步 Staging 副本...');
  const stagedDir = stagePlugin(projectRoot);
  console.log(`PASS 成功同步至 ${stagedDir}`);

  // 4. 打包 ZIP 与生成 SHA256
  console.log('[4/4] 生成发行版 ZIP 与哈希校验和...');
  const pkg = JSON.parse(readFileSync(join(projectRoot, 'package.json'), 'utf8'));
  const version = pkg.version || '0.1.1';
  const outputsDir = join(projectRoot, 'outputs');
  mkdirSync(outputsDir, { recursive: true });

  const zipFile = join(outputsDir, `op-lead-with-us-${version}.zip`);
  const shaFile = join(outputsDir, `op-lead-with-us-${version}.sha256.txt`);

  createArchive(stagedDir, zipFile);

  const hashValue = computeSha256(zipFile).toUpperCase();
  const shaContent = `\nAlgorithm : SHA256\nHash      : ${hashValue}\nPath      : ${zipFile}\n\n`;
  writeFileSync(shaFile, shaContent, 'utf8');

  console.log(`\n✅ 打包完成！`);
  console.log(`ZIP 文件: ${zipFile}`);
  console.log(`SHA256:   ${hashValue}`);
  console.log(`校验文件: ${shaFile}`);
  return { zipFile, shaFile, hashValue };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    packagePlugin();
  } catch (error) {
    console.error(`FAIL 打包失败: ${error.message}`);
    process.exitCode = 1;
  }
}
