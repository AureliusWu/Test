import { readFileSync, writeFileSync, mkdirSync, existsSync, realpathSync, lstatSync } from 'node:fs';
import { resolve, relative, dirname, sep, isAbsolute } from 'node:path';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';

export const MATERIALS_VERSION = '1.1.0';
const CATALOG = 'docs/production/REUSABLE-ASSETS.json';
const MANIFEST = 'docs/production/REUSE-MANIFEST.json';
const policies = new Set(['licensed', 'recipe', 'project-only']);
const kinds = new Set(['font', 'tool', 'template', 'art', 'audio', 'ui', 'voice']);

export function repoPath(root, name) {
  if (typeof name !== 'string' || !name || name.includes('\\') || name.includes(':') || name.includes('\0') || name.startsWith('/') || name.split('/').some(p => !p || p === '.' || p === '..')) {
    throw new Error(`Unsafe repository path: ${name}`);
  }
  const base = realpathSync(root), target = resolve(base, name);
  const inside = p => { const rel = relative(base, p); return !isAbsolute(rel) && rel !== '..' && !rel.startsWith(`..${sep}`) && !resolve(p).startsWith('\\\\'); };
  let existing = target;
  while (!existsSync(existing)) existing = dirname(existing);
  if (!inside(realpathSync(existing))) throw new Error(`Path escapes repository: ${name}`);
  return target;
}

export function encodedBytes(root, ref) {
  if (!ref || !['binary', 'text-lf'].includes(ref.encoding) || !/^[a-f0-9]{64}$/.test(ref.sha256 ?? '')) throw new Error('Invalid file reference');
  const file = repoPath(root, ref.path);
  if (!lstatSync(file).isFile()) throw new Error(`Expected regular file: ${ref.path}`);
  const raw = readFileSync(file);
  const bytes = ref.encoding === 'text-lf' ? Buffer.from(new TextDecoder('utf-8', { fatal: true }).decode(raw).replace(/\r\n/g, '\n')) : raw;
  const actual = createHash('sha256').update(bytes).digest('hex');
  if (actual !== ref.sha256) throw new Error(`SHA-256 mismatch: ${ref.path} (${actual})`);
  return bytes;
}

export function verifyCatalog(root, catalog) {
  if (catalog?.schema !== 1 || catalog.contractVersion !== MATERIALS_VERSION || typeof catalog.project !== 'string' || !catalog.project || !Array.isArray(catalog.entries) || !catalog.entries.length) throw new Error('Invalid materials catalog');
  const ids = new Set(), paths = new Map();
  const counts = { entries: catalog.entries.length, files: 0, licensed: 0, recipe: 0, 'project-only': 0, missingSources: 0 };
  for (const entry of catalog.entries) {
    if (!/^[a-zA-Z0-9_.-]+$/.test(entry.id ?? '') || ids.has(entry.id)) throw new Error(`Duplicate or invalid material ID: ${entry.id}`);
    ids.add(entry.id);
    if (!kinds.has(entry.kind) || !policies.has(entry.reuse) || typeof entry.origin !== 'string' || !entry.origin || !Array.isArray(entry.files) || !entry.files.length) throw new Error(`Invalid material: ${entry.id}`);
    if (!['present', 'not-in-repository', 'not-applicable'].includes(entry.sourceStatus)) throw new Error(`Missing source status: ${entry.id}`);
    if (entry.sourceStatus === 'present' && !entry.files.some(ref => ref.role === 'source')) throw new Error(`Missing source reference: ${entry.id}`);
    if (entry.sourceStatus === 'not-in-repository') {
      if (!entry.sourceNote || entry.reuse === 'licensed' && entry.kind === 'art') throw new Error(`Unresolved source provenance: ${entry.id}`);
      counts.missingSources++;
    }
    if (entry.reuse !== 'project-only' && (!entry.license?.name || !entry.license.file)) throw new Error(`Missing reusable license: ${entry.id}`);
    const refs = [...entry.files, ...(entry.license?.file ? [entry.license.file] : [])];
    for (const ref of refs) {
      const bytes = encodedBytes(root, ref);
      const previous = paths.get(ref.path);
      if (previous && (previous.sha256 !== ref.sha256 || previous.encoding !== ref.encoding)) throw new Error(`Conflicting reference: ${ref.path}`);
      paths.set(ref.path, ref);
      if (!bytes.length) throw new Error(`Empty material: ${ref.path}`);
    }
    counts[entry.reuse]++;
  }
  counts.files = paths.size;
  return counts;
}

export function verifyShared(root) {
  const manifest = JSON.parse(readFileSync(repoPath(root, MANIFEST), 'utf8'));
  if (manifest.version !== MATERIALS_VERSION || !Object.keys(manifest.files ?? {}).length) throw new Error('Invalid shared manifest');
  for (const [path, sha256] of Object.entries(manifest.files)) encodedBytes(root, { path, sha256, encoding: 'text-lf' });
  return Object.keys(manifest.files).length;
}

export function exportKit(root, catalog, output) {
  const counts = verifyCatalog(root, catalog);
  if (typeof output !== 'string' || !output.startsWith('.reuse-kit/')) throw new Error('Export must use a new .reuse-kit/<name> directory');
  const destination = repoPath(root, output);
  if (existsSync(destination)) throw new Error(`Export already exists: ${output}`);
  const entries = catalog.entries.filter(entry => entry.reuse !== 'project-only');
  const files = new Map();
  for (const entry of entries) for (const ref of [...entry.files, entry.license.file]) files.set(ref.path, { ref, bytes: encodedBytes(root, ref) });
  mkdirSync(dirname(destination), { recursive: true });
  repoPath(root, output);
  mkdirSync(destination);
  for (const { ref, bytes } of files.values()) {
    const target = repoPath(root, `${output}/files/${ref.path}`);
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, bytes, { flag: 'wx' });
  }
  const manifest = { schema: 1, contractVersion: MATERIALS_VERSION, project: catalog.project, sourceRepository: catalog.repository, sourceCommit: catalog.sourceCommit, entries, files: [...files.values()].map(({ ref }) => ref), excludedProjectOnly: counts['project-only'] };
  writeFileSync(resolve(destination, 'MANIFEST.json'), `${JSON.stringify(manifest, null, 2)}\n`, { flag: 'wx' });
  writeFileSync(resolve(destination, 'README.md'), `# ${catalog.project} reusable materials\n\nSee MANIFEST.json for pinned files, origins and per-entry licenses. Files are under files/ with their original repository paths. Text uses LF; binary bytes are unchanged. Project-specific characters, CG and voices are excluded. Recipes need the target engine and project settings; font subsets must be regenerated for the target text. sourceCommit records the inventory baseline; SHA-256 identifies the actual exported bytes.\n`, { flag: 'wx' });
  return { output, entries: entries.length, files: files.size, excludedProjectOnly: counts['project-only'] };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    const root = process.cwd(), command = process.argv[2] ?? 'verify';
    const catalog = JSON.parse(readFileSync(repoPath(root, CATALOG), 'utf8'));
    const sharedFiles = verifyShared(root);
    if (command === 'verify') console.log(JSON.stringify({ project: catalog.project, sharedFiles, ...verifyCatalog(root, catalog) }, null, 2));
    else if (command === 'export') console.log(JSON.stringify(exportKit(root, catalog, process.argv[3]), null, 2));
    else throw new Error('Usage: node scripts/vn-materials.mjs verify | export .reuse-kit/<new-name>');
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
