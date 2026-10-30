import { cp, mkdir, access } from 'node:fs/promises';
import path from 'node:path';

const here = path.dirname(new URL(import.meta.url).pathname);
const root = path.resolve(here, '..');
const pub = path.join(root, 'public');

const copy = async (from, to) => {
  try {
    await access(from);
    await mkdir(path.dirname(to), { recursive: true });
    await cp(from, to, { recursive: true });
    console.log('copied', path.relative(root, to));
  } catch {
    console.warn('skipped (missing):', from);
  }
};

await mkdir(pub, { recursive: true });
for (const f of [
  'Cairo-ExtraBold.ttf',
  'Cairo-Bold.ttf',
  'Tajawal-ExtraBold.ttf',
  'Amiri-Bold.ttf',
  'MaterialSymbols-Rounded.ttf',
]) {
  await copy(path.join(root, '..', 'fonts', f), path.join(pub, 'fonts', f));
}
await copy(path.join(root, '..', 'media', 'voice.mp3'), path.join(pub, 'voice.mp3'));
