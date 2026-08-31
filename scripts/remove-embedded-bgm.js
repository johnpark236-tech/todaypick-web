import { rm } from 'node:fs/promises';
import { join } from 'node:path';

const distAudio = join(process.cwd(), 'dist', 'audio');
const embeddedBgmFiles = ['bgm_01.mp3', 'bgm_01.ogg'];

await Promise.allSettled(
  embeddedBgmFiles.map((fileName) => rm(join(distAudio, fileName), { force: true }))
);

console.log(`Removed embedded BGM files from dist/audio: ${embeddedBgmFiles.join(', ')}`);
