import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, mkdirSync, readFileSync, rmSync, existsSync, symlinkSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import { verifyCatalog, exportKit, repoPath } from './vn-materials.mjs';

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'vn-materials-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  writeFileSync(join(root, 'recipe.txt'), 'recipe\r\n');
  writeFileSync(join(root, 'LICENSE'), 'permission\n');
  writeFileSync(join(root, 'character.webp'), Buffer.from([0, 1, 2, 255]));
  const ref = (path, text, encoding = 'text-lf', role = 'recipe') => ({ path, role, encoding, sha256: createHash('sha256').update(text).digest('hex') });
  const license = { name: 'fixture permission', file: ref('LICENSE', 'permission\n') };
  const catalog = { schema: 1, contractVersion: '1.1.0', project: 'fixture', entries: [
    { id: 'recipe', kind: 'tool', reuse: 'recipe', origin: 'fixture', sourceStatus: 'not-applicable', license, files: [ref('recipe.txt', 'recipe\n')] },
    { id: 'character', kind: 'art', reuse: 'project-only', origin: 'fixture', sourceStatus: 'not-in-repository', sourceNote: 'Source was not preserved', files: [ref('character.webp', Buffer.from([0, 1, 2, 255]), 'binary', 'runtime')] }
  ] };
  return { root, catalog };
}

test('export pins LF text and licenses, excludes project-only art and refuses overwrite', t => {
  const { root, catalog } = fixture(t);
  assert.equal(verifyCatalog(root, catalog).missingSources, 1);
  assert.equal(exportKit(root, catalog, '.reuse-kit/sample').entries, 1);
  assert.equal(readFileSync(join(root, '.reuse-kit/sample/files/recipe.txt'), 'utf8'), 'recipe\n');
  assert.ok(existsSync(join(root, '.reuse-kit/sample/files/LICENSE')));
  assert.ok(!existsSync(join(root, '.reuse-kit/sample/files/character.webp')));
  assert.throws(() => exportKit(root, catalog, '.reuse-kit/sample'), /already exists/);
});

test('changed bytes fail before any export is written', t => {
  const { root, catalog } = fixture(t);
  writeFileSync(join(root, 'recipe.txt'), 'edited\n');
  assert.throws(() => exportKit(root, catalog, '.reuse-kit/sample'), /SHA-256 mismatch/);
  assert.ok(!existsSync(join(root, '.reuse-kit')));
});

test('traversal, absolute Windows paths and unknown encoding are rejected', t => {
  const { root, catalog } = fixture(t);
  for (const name of ['../outside', '/tmp/file', 'C:/file', 'a\\file', 'a/../file', 'a//file']) assert.throws(() => repoPath(root, name), /Unsafe/);
  assert.throws(() => exportKit(root, catalog, 'output'), /Export must use/);
  catalog.entries[0].files[0].encoding = 'guess';
  assert.throws(() => verifyCatalog(root, catalog), /Invalid file reference/);
});

test('duplicate IDs and reuse without a license are rejected', t => {
  const { root, catalog } = fixture(t);
  catalog.entries[1].id = 'recipe';
  assert.throws(() => verifyCatalog(root, catalog), /Duplicate/);
  catalog.entries[1].id = 'character';
  catalog.entries[0].license = undefined;
  assert.throws(() => verifyCatalog(root, catalog), /Missing reusable license/);
});

test('directory links cannot export outside the repository', t => {
  const { root } = fixture(t);
  const external = mkdtempSync(join(tmpdir(), 'vn-materials-external-'));
  t.after(() => rmSync(external, { recursive: true, force: true }));
  writeFileSync(join(external, 'secret.txt'), 'outside');
  symlinkSync(external, join(root, 'linked'), 'junction');
  assert.throws(() => repoPath(root, 'linked/secret.txt'), /escapes repository/);
  assert.throws(() => repoPath(root, 'linked/new/file'), /escapes repository/);
});
