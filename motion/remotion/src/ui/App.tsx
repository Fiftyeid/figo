import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Player } from '@remotion/player';
import { canRenderMediaOnWeb, renderMediaOnWeb, renderStillOnWeb } from '@remotion/web-renderer';
import { Jalibib, VIDEO } from '../video/Jalibib';
import { DURATION, TOTAL_FRAMES } from '../video/story';

type Preset = { id: string; label: string; width: number; height: number; bitrate: number };

const PRESETS: Preset[] = [
  { id: 'full', label: 'كامل 1080×1920', width: 1080, height: 1920, bitrate: 12_000_000 },
  { id: 'hd', label: 'سريع 720×1280', width: 720, height: 1280, bitrate: 7_000_000 },
  { id: 'draft', label: 'مسوّدة 540×960', width: 540, height: 960, bitrate: 3_500_000 },
];

type Format = { container: 'mp4' | 'webm'; codec: 'h264' | 'vp9'; ext: string };

const log = (msg: string) => {
  void fetch('/api/log', { method: 'POST', body: `[${new Date().toISOString()}] ${msg}` }).catch(() => {});
};

export const App: React.FC = () => {
  const [presetId, setPresetId] = useState('hd');
  const [parts, setParts] = useState(6);
  const [support, setSupport] = useState<{ ok: boolean; msg: string } | null>(null);
  const [format, setFormat] = useState<Format>({ container: 'mp4', codec: 'h264', ext: 'mp4' });
  const [running, setRunning] = useState(false);
  const [pct, setPct] = useState(0);
  const [status, setStatus] = useState('جاهز');
  const [doneParts, setDoneParts] = useState(0);
  const [finalUrl, setFinalUrl] = useState<string | null>(null);
  const [stillT, setStillT] = useState('27');
  const [stillMsg, setStillMsg] = useState('');
  const [thumb, setThumb] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);

  const preset = useMemo(() => PRESETS.find((p) => p.id === presetId) ?? PRESETS[1], [presetId]);

  useEffect(() => {
    void (async () => {
      try {
        const mp4 = await canRenderMediaOnWeb({
          container: 'mp4',
          videoCodec: 'h264',
          width: preset.width,
          height: preset.height,
          muted: true,
        });
        if (mp4.canRender && !mp4.issues.some((i: any) => i.severity === 'error')) {
          setFormat({ container: 'mp4', codec: 'h264', ext: 'mp4' });
          setSupport({ ok: true, msg: 'WebCodecs جاهز (H.264 / MP4)' });
          return;
        }
        const webm = await canRenderMediaOnWeb({
          container: 'webm',
          videoCodec: 'vp9',
          width: preset.width,
          height: preset.height,
          muted: true,
        });
        if (webm.canRender && !webm.issues.some((i: any) => i.severity === 'error')) {
          setFormat({ container: 'webm', codec: 'vp9', ext: 'webm' });
          setSupport({ ok: true, msg: 'المتصفح لا يدعم H.264 — هيتم الرندر VP9/WebM ثم تحويله' });
          return;
        }
        setSupport({
          ok: false,
          msg: [...mp4.issues, ...webm.issues]
            .filter((i: any) => i.severity === 'error')
            .map((i: any) => i.message)
            .join(' · ') || 'المتصفح لا يدعم WebCodecs',
        });
      } catch (e: any) {
        setSupport({ ok: false, msg: String(e?.message ?? e) });
      }
    })();
  }, [preset.width, preset.height]);

  const composition = useMemo(
    () => ({
      id: VIDEO.id,
      component: Jalibib,
      width: preset.width,
      height: preset.height,
      fps: VIDEO.fps,
      durationInFrames: VIDEO.durationInFrames,
    }),
    [preset],
  );

  const start = useCallback(async () => {
    if (running) return;
    setRunning(true);
    setFinalUrl(null);
    setPct(0);
    setDoneParts(0);
    setStatus('تهيئة…');
    abort.current = new AbortController();
    log(`start preset=${preset.id} parts=${parts}`);
    try {
      const per = Math.ceil(TOTAL_FRAMES / parts);
      for (let i = 0; i < parts; i++) {
        const from = i * per;
        const to = Math.min(TOTAL_FRAMES - 1, from + per - 1);
        if (from > to) break;
        setStatus(`رندر الجزء ${i + 1} من ${parts} (فريم ${from}–${to})`);
        const res = await renderMediaOnWeb({
          composition: composition as any,
          frameRange: [from, to] as [number, number],
          muted: true,
          container: format.container,
          videoCodec: format.codec,
          videoBitrate: preset.bitrate,
          logLevel: 'warn',
          signal: abort.current.signal,
          onProgress: ({ progress }: { progress: number }) => {
            const overall = ((i + progress) / parts) * 100;
            setPct(Math.min(99, overall));
          },
        } as any);
        const blob = await res.getBlob();
        setStatus(`رفع الجزء ${i + 1}…`);
        await fetch(`/api/part?i=${i}&ext=${format.ext}`, { method: 'POST', body: blob });
        setDoneParts(i + 1);
        log(`part ${i} ok ${blob.size} bytes`);
      }
      setStatus('دمج الأجزاء وإضافة الصوت…');
      setPct(99.5);
      const fin = await fetch('/api/finish', { method: 'POST' }).then((r) => r.json());
      if (!fin?.ok) throw new Error(fin?.error ?? 'فشل الدمج');
      setFinalUrl(`${fin.url}?v=${Date.now()}`);
      setPct(100);
      setStatus(`تم — ${(fin.bytes / 1048576).toFixed(1)} ميجابايت`);
      log(`finish ok ${fin.bytes} bytes`);
    } catch (e: any) {
      const msg = String(e?.message ?? e);
      setStatus(`توقف: ${msg}`);
      log(`error ${msg}`);
    } finally {
      setRunning(false);
    }
  }, [composition, format.codec, format.container, format.ext, parts, preset.bitrate, preset.id, running]);

  const stop = () => {
    abort.current?.abort();
    setRunning(false);
    setStatus('تم الإيقاف');
  };

  const snapshot = async (seconds?: number) => {
    const sec = seconds ?? Number(stillT);
    if (seconds !== undefined) setStillT(String(seconds));
    setStillMsg('…');
    try {
      const frame = Math.max(0, Math.min(TOTAL_FRAMES - 1, Math.round(sec * VIDEO.fps)));
      const res = await renderStillOnWeb({
        composition: { ...composition, width: 1080, height: 1920 } as any,
        frame,
      });
      const blob = await res.blob({ format: 'png' });
      setThumb(URL.createObjectURL(blob));
      const r = await fetch(`/api/still?t=${sec}`, { method: 'POST', body: blob });
      const j = await r.json();
      setStillMsg(j.ok ? `محفوظة في السيرفر: ${j.file}` : `فشل: ${j.error}`);
      log(`still ${sec} -> ${j.file}`);
    } catch (e: any) {
      setStillMsg(`فشل: ${String(e?.message ?? e)}`);
      log(`still error ${String(e?.message ?? e)}`);
    }
  };

  const eta = running && pct > 1 ? Math.round(((100 - pct) / pct) * 0) : 0;

  return (
    <div className="wrap">
      <header>
        <h1>قصّة جليبيب — Remotion</h1>
        <p className="sub">
          مشهد واحد لكل جملة · {TOTAL_FRAMES} فريم · {DURATION.toFixed(0)} ثانية · رندر داخل المتصفح
          (WebCodecs) بدون أي متصفّح في السيرفر
        </p>
      </header>

      <div className="grid">
        <div className="preview">
          <Player
            component={Jalibib}
            durationInFrames={VIDEO.durationInFrames}
            compositionWidth={1080}
            compositionHeight={1920}
            fps={VIDEO.fps}
            style={{ width: '100%', height: '100%' }}
            controls
            acknowledgeRemotionLicense
          />
        </div>

        <aside className="panel">
          <div className="row">
            <label>الدقّة</label>
            <select value={presetId} onChange={(e) => setPresetId(e.target.value)} disabled={running}>
              {PRESETS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div className="row">
            <label>عدد الأجزاء</label>
            <input
              type="number"
              min={1}
              max={12}
              value={parts}
              disabled={running}
              onChange={(e) => setParts(Math.max(1, Math.min(12, Number(e.target.value) || 1)))}
            />
          </div>

          <div className={`badge ${support?.ok ? 'ok' : 'bad'}`}>
            {support ? (support.ok ? '✓ ' : '✕ ') + support.msg : 'جارٍ فحص إمكانيات المتصفح…'}
          </div>

          <button className="primary" onClick={start} disabled={running || support?.ok === false}>
            {running ? 'شغّال…' : 'ابدأ الرندر'}
          </button>
          {running && (
            <button className="ghost" onClick={stop}>
              إيقاف
            </button>
          )}

          <div className="bar">
            <div style={{ width: `${pct}%` }} />
          </div>
          <div className="status">
            {status} {pct > 0 && pct < 100 ? `· ${pct.toFixed(0)}%` : ''}{' '}
            {doneParts ? `· أجزاء جاهزة: ${doneParts}/${parts}` : ''}
            {eta ? '' : ''}
          </div>

          {finalUrl && (
            <div className="result">
              <video src={finalUrl} controls playsInline />
              <a href={finalUrl} download="jalibib-remotion.mp4">
                تحميل MP4 ({finalUrl})
              </a>
            </div>
          )}

          <hr />

          <div className="row">
            <label>لقطة للمراجعة (ثانية)</label>
            <input value={stillT} onChange={(e) => setStillT(e.target.value)} disabled={running} />
          </div>
          <button className="ghost" onClick={() => snapshot()} disabled={running}>
            التقط لقطة
          </button>
          <div className="shots">
            {[2, 30, 55, 95, 113, 154, 168, 179].map((t) => (
              <button key={t} className="chip" onClick={() => snapshot(t)} disabled={running}>
                {t}s
              </button>
            ))}
          </div>
          <div className="status small">{stillMsg}</div>
          {thumb && <img className="thumb" src={thumb} alt="still" />}

          <p className="hint">
            الرندر يشتغل على جهازك أنت (Chrome/Edge). الأجزاء تُرفع للسيرفر ثم يُدمجها ffmpeg مع
            الصوت الأصلي. لو الجهاز بطيء: قلّل الدقّة أو زوّد عدد الأجزاء.
          </p>
        </aside>
      </div>
    </div>
  );
};
