import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const ROOT = path.dirname(new URL(import.meta.url).pathname);
const OUT = path.join(ROOT, 'out');
const AUDIO = path.join(ROOT, '..', 'media', 'voice.mp3');
const FFMPEG =
  process.env.FFMPEG_BIN ||
  '/home/user/.venv/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2';

const json = (res: any, code: number, data: unknown) => {
  res.statusCode = code;
  res.setHeader('content-type', 'application/json; charset=utf-8');
  res.end(JSON.stringify(data));
};

const readBody = (req: any): Promise<Buffer> =>
  new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on('data', (c: any) => chunks.push(Buffer.from(c)));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });

const run = (args: string[]) =>
  new Promise<{ code: number; err: string }>((resolve) => {
    const p = spawn(FFMPEG, args, { stdio: ['ignore', 'ignore', 'pipe'] });
    let err = '';
    p.stderr.on('data', (d) => (err += d.toString()));
    p.on('close', (code) => resolve({ code: code ?? 1, err: err.slice(-1500) }));
  });

/**
 * واجهة صغيرة على سيرفر التطوير:
 *   POST /api/part?i=N   ← جزء الفيديو الخام (mp4) من المتصفح
 *   POST /api/finish     ← دمج الأجزاء + إضافة الصوت الأصلي بـ ffmpeg
 *   POST /api/still?t=T  ← لقطة PNG للمراجعة
 *   POST /api/log        ← سجل التشخيص
 *   GET  /out/<file>     ← تحميل الناتج
 */
function renderApi(): Plugin {
  return {
    name: 'jalibib-render-api',
    configureServer(server) {
      server.middlewares.use('/api/part', async (req, res) => {
        if (req.method !== 'POST') return json(res, 405, { error: 'POST only' });
        const url = new URL(req.url ?? '/', 'http://x');
        const i = Number(url.searchParams.get('i') ?? '0');
        const extRaw = (url.searchParams.get('ext') ?? 'mp4').toLowerCase();
        const ext = ['mp4', 'webm', 'mkv', 'mov'].includes(extRaw) ? extRaw : 'mp4';
        const body = await readBody(req);
        await fs.promises.mkdir(OUT, { recursive: true });
        for (const old of await fs.promises.readdir(OUT)) {
          if (old.startsWith(`part-${String(i).padStart(2, '0')}.`)) {
            await fs.promises.unlink(path.join(OUT, old));
          }
        }
        const file = path.join(OUT, `part-${String(i).padStart(2, '0')}.${ext}`);
        await fs.promises.writeFile(file, body);
        json(res, 200, { ok: true, part: i, bytes: body.length });
      });

      server.middlewares.use('/api/finish', async (req, res) => {
        if (req.method !== 'POST') return json(res, 405, { error: 'POST only' });
        try {
          const files = (await fs.promises.readdir(OUT))
            .filter((f) => /^part-\d+\.(mp4|webm|mkv|mov)$/.test(f))
            .sort();
          if (!files.length) return json(res, 400, { error: 'لا توجد أجزاء' });
          const listText = files.map((f) => `file '${path.join(OUT, f)}'`).join('\n');
          const listPath = path.join(OUT, 'parts.txt');
          await fs.promises.writeFile(listPath, listText);

          const target = path.join(OUT, 'final.mp4');
          const withAudio = fs.existsSync(AUDIO);
          const base = ['-y', '-f', 'concat', '-safe', '0', '-i', listPath];
          if (withAudio) base.push('-i', AUDIO);

          const copyArgs = [
            ...base,
            '-c:v', 'copy',
            ...(withAudio ? ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest'] : ['-an']),
            '-movflags', '+faststart',
            target,
          ];
          let r = await run(copyArgs);
          if (r.code !== 0) {
            const reArgs = [
              ...base,
              '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
              ...(withAudio ? ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest'] : ['-an']),
              '-movflags', '+faststart',
              target,
            ];
            r = await run(reArgs);
            if (r.code !== 0) return json(res, 500, { error: 'ffmpeg failed', log: r.err });
          }
          const size = (await fs.promises.stat(target)).size;
          json(res, 200, { ok: true, url: '/out/final.mp4', bytes: size, parts: files.length });
        } catch (e: any) {
          json(res, 500, { error: String(e?.message ?? e) });
        }
      });

      server.middlewares.use('/api/still', async (req, res) => {
        if (req.method !== 'POST') return json(res, 405, { error: 'POST only' });
        const url = new URL(req.url ?? '/', 'http://x');
        const t = (url.searchParams.get('t') ?? '0').replace(/[^\d.]/g, '');
        const body = await readBody(req);
        await fs.promises.mkdir(OUT, { recursive: true });
        const file = path.join(OUT, `still-${t}.png`);
        await fs.promises.writeFile(file, body);
        json(res, 200, { ok: true, file: `/out/still-${t}.png`, bytes: body.length });
      });

      server.middlewares.use('/api/log', async (req, res) => {
        const body = await readBody(req);
        await fs.promises.mkdir(OUT, { recursive: true });
        await fs.promises.appendFile(path.join(OUT, 'client.log'), body.toString() + '\n');
        json(res, 200, { ok: true });
      });

      server.middlewares.use('/out', async (req, res) => {
        const name = (req.url ?? '/').split('?')[0].replace(/^\/+/, '');
        const file = path.join(OUT, name);
        if (!file.startsWith(OUT) || !fs.existsSync(file)) {
          res.statusCode = 404;
          return res.end('not found');
        }
        const stat = await fs.promises.stat(file);
        res.setHeader('content-type', name.endsWith('.mp4') ? 'video/mp4' : 'application/octet-stream');
        res.setHeader('content-length', String(stat.size));
        res.setHeader('accept-ranges', 'bytes');
        if (name.endsWith('.mp4')) res.setHeader('content-disposition', 'inline');
        fs.createReadStream(file).pipe(res);
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), renderApi()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    hmr: false,
  },
  build: { target: 'es2022' },
});
