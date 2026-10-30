/**
 * فحص دخان: يرسم كل مشهد من مشاهد الفيديو في jsdom
 * للتأكد إن مفيش أخطاء وقت التشغيل قبل ما نجرّب في المتصفّح.
 *
 *   npx tsx test/smoke.tsx
 */
import { JSDOM } from 'jsdom';
import React from 'react';

const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {
  pretendToBeVisual: true,
  url: 'http://localhost:5173/',
});

const g = globalThis as any;
g.window = dom.window;
g.document = dom.window.document;
Object.defineProperty(g, 'navigator', { value: dom.window.navigator, configurable: true });
g.HTMLElement = dom.window.HTMLElement;
g.HTMLMediaElement = dom.window.HTMLMediaElement;
g.Element = dom.window.Element;
g.Node = dom.window.Node;
g.requestAnimationFrame = (cb: any) => setTimeout(() => cb(Date.now()), 16);
g.cancelAnimationFrame = (id: any) => clearTimeout(id);
g.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
g.IntersectionObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
if (dom.window.HTMLCanvasElement) {
  dom.window.HTMLCanvasElement.prototype.getContext = () => null;
}
g.HTMLCanvasElement = dom.window.HTMLCanvasElement;

const { createRoot } = await import('react-dom/client');
const { Player } = await import('@remotion/player');
const { Jalibib, VIDEO } = await import('../src/video/Jalibib');
const { BEATS } = await import('../src/video/story');

let failures = 0;
const errors: string[] = [];
const origError = console.error;
console.error = (...args: any[]) => {
  const msg = args.map(String).join(' ');
  if (!msg.includes('Not implemented') && !msg.includes('HTMLMediaElement')) errors.push(msg);
  origError(...args);
};

const container = dom.window.document.getElementById('root')!;
const root = createRoot(container);

for (const [i, beat] of BEATS.entries()) {
  const frame = Math.round(beat.t0 * VIDEO.fps + Math.min(1.2 * VIDEO.fps, (beat.t1 - beat.t0) * VIDEO.fps * 0.5));
  try {
    root.render(
      React.createElement(Player, {
        component: Jalibib,
        durationInFrames: VIDEO.durationInFrames,
        compositionWidth: VIDEO.width,
        compositionHeight: VIDEO.height,
        fps: VIDEO.fps,
        initialFrame: frame,
        controls: false,
        style: { width: 270, height: 480 },
        acknowledgeRemotionLicense: true,
      } as any),
    );
    await new Promise((r) => setTimeout(r, 12));
  } catch (e: any) {
    failures++;
    console.log(`✗ ${i} ${beat.kind} @${beat.t0}s → ${e?.message ?? e}`);
  }
}

const html = container.innerHTML;
const checks: [string, boolean][] = [
  ['يوجد DOM', html.length > 500],
  ['نص عربي', /[\u0600-\u06FF]/.test(html)],
  ['أيقونة', html.includes('MS') || /[\uE000-\uF8FF]/.test(html)],
];

console.log('---');
for (const [name, ok] of checks) {
  console.log(`${ok ? '✓' : '✗'} ${name}`);
  if (!ok) failures++;
}
if (errors.length) {
  console.log('--- أخطاء كونسول:');
  for (const e of errors.slice(0, 12)) console.log('  ', e.slice(0, 220));
  failures += errors.length;
}
console.log(failures === 0 ? '\nنجح الفحص' : `\nفشل: ${failures}`);
process.exit(failures === 0 ? 0 : 1);
