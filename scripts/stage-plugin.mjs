import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync, rmSync } from 'node:fs';
import { join, resolve, relative, sep, dirname, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { projectRoot, packageFiles, validatePlugin } from './validate.mjs';

const hash = data => createHash('sha256').update(data).digest('hex');
const marker = '.op-lead-with-us-stage.json';

function guardPath(root, target) {
  const rel = relative(root, target);
  // `relative()` returns an absolute path when roots are on different drives.
  // Reject that escape, while allowing a valid UNC/WSL root such as
  // `\\wsl.localhost\Ubuntu\mnt\n\repo`.
  assert(rel && rel !== '..' && !rel.startsWith(`..${sep}`) && !isAbsolute(rel), 'Stage target must be below the workspace');
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
  const target = join(root, '.agents', 'plugins', 'op-lead-with-us');
  guardPath(root, target);
  const targetMarker = join(target, marker);
  let prior = null;
  if (existsSync(targetMarker)) {
    try {
      prior = JSON.parse(readFileSync(targetMarker, 'utf8'));
    } catch {
      assert(false, 'Invalid staging manifest');
    }
  }
  if (prior) assert(prior.format === 1 && prior.files && typeof prior.files === 'object', 'Invalid staging manifest');
  // Preflight retired files as well as current payloads before mutating anything.
  // A manifest entry proves prior ownership, not that the user left the file untouched.
  const previouslyManaged = new Set(prior ? Object.keys(prior.files) : []);
  const retired = [];
  for (const file of walkFiles(target)) {
    if (file === marker || packageFiles.includes(file)) continue;
    assert(previouslyManaged.has(file), `Unexpected staged file; not deleting it: ${file}`);
    const destination = join(target, file);
    guardPath(root, destination);
    assert(hash(readFileSync(destination)) === prior.files[file],
      `Refusing to delete locally changed retired staged file: ${file}`);
    retired.push(destination);
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
  // All conflicts have now been checked, including files that will be retired.
  for (const destination of retired) rmSync(destination);
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
