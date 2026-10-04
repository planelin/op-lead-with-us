import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join, resolve, relative, sep, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { projectRoot, packageFiles, validatePlugin } from './validate.mjs';

const hash = data => createHash('sha256').update(data).digest('hex');
const marker = '.opus-staff-stage.json';

function guardPath(root, target) {
  const rel = relative(root, target);
  assert(rel && rel !== '..' && !rel.startsWith(`..${sep}`) && !resolve(target).startsWith('\\\\'), 'Stage target must be below the workspace');
  let current = root;
  assert(!lstatSync(current).isSymbolicLink(), 'Refusing symlink workspace');
  for (const segment of rel.split(sep)) {
    current = join(current, segment);
    if (existsSync(current)) assert(!lstatSync(current).isSymbolicLink(), `Refusing symlink/junction: ${current}`);
  }
}
function walkFiles(root, prefix = '') {
  if (!existsSync(root)) return [];
  const result = [];
  for (const name of readdirSync(root)) {
    const path = join(root, name);
    const stat = lstatSync(path);
    assert(!stat.isSymbolicLink(), `Refusing symlink/junction: ${path}`);
    const rel = prefix ? `${prefix}/${name}` : name;
    if (stat.isDirectory()) result.push(...walkFiles(path, rel));
    else result.push(rel);
  }
  return result;
}

export function stagePlugin(root = projectRoot) {
  root = resolve(root);
  validatePlugin(root);
  const target = join(root, '.agents', 'plugins', 'opus-staff');
  guardPath(root, target);
  const targetMarker = join(target, marker);
  const prior = existsSync(targetMarker) ? JSON.parse(readFileSync(targetMarker, 'utf8')) : null;
  if (prior) assert(prior.format === 1 && prior.files && typeof prior.files === 'object', 'Invalid staging manifest');
  for (const file of walkFiles(target)) {
    assert(file === marker || packageFiles.includes(file), `Unexpected staged file; not deleting it: ${file}`);
  }
  const payload = new Map();
  // Complete preflight before making any writes; never overwrite user-modified assets.
  for (const file of packageFiles) {
    guardPath(root, join(root, file));
    const source = readFileSync(join(root, file));
    payload.set(file, source);
    const destination = join(target, file);
    guardPath(root, destination);
    if (existsSync(destination)) {
      const existingHash = hash(readFileSync(destination));
      assert(existingHash === hash(source) || existingHash === prior?.files[file], `Refusing to overwrite locally changed staged file: ${file}`);
    }
  }
  mkdirSync(target, { recursive: true });
  const hashes = {};
  for (const [file, source] of payload) {
    const destination = join(target, file);
    mkdirSync(dirname(destination), { recursive: true });
    writeFileSync(destination, source);
    hashes[file] = hash(source);
  }
  writeFileSync(targetMarker, `${JSON.stringify({ format: 1, files: hashes }, null, 2)}\n`);
  validatePlugin(target);
  return target;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    console.log(`Staged workspace plugin: ${stagePlugin()}`);
    console.log('Global configuration was not changed. Start a new Antigravity chat in this workspace to test discovery.');
  } catch (error) {
    console.error(`FAIL ${error.message}`);
    process.exitCode = 1;
  }
}
