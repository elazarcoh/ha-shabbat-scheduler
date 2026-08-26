import resolve from '@rollup/plugin-node-resolve';
import typescript from '@rollup/plugin-typescript';
import terser from '@rollup/plugin-terser';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { bundleManifest } from './bundle-manifest.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const outFile = path.join(
  here,
  '../custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js',
);

export default {
  input: 'src/card.ts',
  output: {
    file: outFile,
    format: 'es',
    sourcemap: false,
  },
  plugins: [
    resolve(),
    typescript({ tsconfig: './tsconfig.json' }),
    // Default options only: mangles local variable/function names. Do not
    // enable mangle.properties - Lit's @property() names and this card's
    // cross-module property access (.hass, .action, .target, ...), read by
    // name from outside the class, would be renamed inconsistently.
    terser(),
    // Records what this build was made from. tests/test_frontend.py fails
    // if the committed bundle stops matching the committed sources, which
    // is otherwise invisible: every test stays green and the cache-busting
    // resource URL does not change either. Runs after the (already
    // minified) bundle is written to disk, so `bundle` hashes the final,
    // shipped bytes regardless of plugin order.
    bundleManifest({
      srcDir: path.join(here, 'src'),
      outFile,
      manifestDir: here,
    }),
  ],
};
