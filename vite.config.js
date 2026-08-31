import { defineConfig } from 'vite';
import { rm } from 'node:fs/promises';
import { join } from 'node:path';

function stripEmbeddedBgm() {
  return {
    name: 'strip-embedded-bgm',
    apply: 'build',
    async closeBundle() {
      const distAudio = join(process.cwd(), 'dist', 'audio');
      await Promise.allSettled([
        rm(join(distAudio, 'bgm_01.mp3'), { force: true }),
        rm(join(distAudio, 'bgm_01.ogg'), { force: true })
      ]);
    }
  };
}

export default defineConfig({
  plugins: [stripEmbeddedBgm()]
});
