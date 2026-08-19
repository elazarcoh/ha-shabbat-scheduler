/**
 * The hash the build stamps and the test suite re-checks.
 *
 * Why this exists: the bundle is committed (a HACS user has no Node), and
 * nothing used to notice when it stopped matching `frontend/src`. Editing
 * a source file and forgetting `npm run build` left every Python and
 * frontend test green while the previous card shipped - and because the
 * Lovelace resource URL is stamped with the hand-maintained CARD_VERSION,
 * the URL did not change either, so browsers kept serving the stale copy
 * out of cache.
 *
 * Rebuilding inside the test suite is not an option: it is slow, and it
 * needs Node on a machine that may not have it. So the build records what
 * it built from, and `tests/test_frontend.py` recomputes the same number
 * in pure Python. Both directions are covered - a source edited without a
 * rebuild, and a bundle hand-edited or committed from a different tree.
 *
 * THE FORMAT IS A CONTRACT with `tests/test_frontend.py`. Any change here
 * must be made there too, or the test fails for the wrong reason:
 *
 *   1. Every `*.ts` under `src/`, recursively.
 *   2. Paths relative to `src/`, POSIX separators, sorted by code point.
 *   3. Each file's bytes with CRLF collapsed to LF (a Windows or
 *      autocrlf checkout must not read as "everything changed"), then
 *      SHA-256.
 *   4. The digest of `"<path> <sha256hex>\n"` for each file, concatenated
 *      in that order and encoded UTF-8, is the `sources` hash.
 *   5. The bundle's own bytes, CRLF-collapsed, SHA-256, is `bundle`.
 */

import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const MANIFEST_NAME = 'bundle-manifest.json';

function normalise(bytes) {
  // Buffer -> Buffer with \r\n collapsed to \n.
  return Buffer.from(bytes.toString('binary').replace(/\r\n/g, '\n'), 'binary');
}

function sha256(bytes) {
  return createHash('sha256').update(normalise(bytes)).digest('hex');
}

function walk(dir, base = dir) {
  const found = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      found.push(...walk(full, base));
    } else if (entry.name.endsWith('.ts')) {
      found.push(path.relative(base, full).split(path.sep).join('/'));
    }
  }
  return found;
}

export function sourcesHash(srcDir) {
  const files = walk(srcDir).sort();
  const digest = createHash('sha256');
  for (const rel of files) {
    digest.update(`${rel} ${sha256(readFileSync(path.join(srcDir, rel)))}\n`, 'utf8');
  }
  return { hash: digest.digest('hex'), count: files.length };
}

export function fileHash(file) {
  return sha256(readFileSync(file));
}

/**
 * Rollup plugin: write the manifest next to this config, after the bundle
 * itself has been written to disk.
 */
export function bundleManifest({ srcDir, outFile, manifestDir }) {
  return {
    name: 'bundle-manifest',
    writeBundle() {
      const { hash, count } = sourcesHash(srcDir);
      writeFileSync(
        path.join(manifestDir, MANIFEST_NAME),
        `${JSON.stringify(
          {
            note: 'Written by `npm run build`. See bundle-manifest.mjs; tests/test_frontend.py re-checks it.',
            source_files: count,
            sources: hash,
            bundle: fileHash(outFile),
          },
          null,
          2,
        )}\n`,
        'utf8',
      );
    },
  };
}
