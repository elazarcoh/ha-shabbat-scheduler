import resolve from '@rollup/plugin-node-resolve';
import typescript from '@rollup/plugin-typescript';
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
    // Records what this build was made from. tests/test_frontend.py fails
    // if the committed bundle stops matching the committed sources, which
    // is otherwise invisible: every test stays green and the cache-busting
    // resource URL does not change either.
    bundleManifest({
      srcDir: path.join(here, 'src'),
      outFile,
      manifestDir: here,
    }),
  ],
};
