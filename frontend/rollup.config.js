import resolve from '@rollup/plugin-node-resolve';
import typescript from '@rollup/plugin-typescript';

export default {
  input: 'src/card.ts',
  output: {
    file: '../custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js',
    format: 'es',
    sourcemap: false,
  },
  plugins: [resolve(), typescript({ tsconfig: './tsconfig.json' })],
};
