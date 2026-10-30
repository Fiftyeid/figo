import React, { useEffect, useState } from 'react';
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { COLORS, FONT, H, MOODS, SPRING, W } from './theme';
import type { Mood } from './story';
import { iconGlyph } from './icons';

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/* ---------------------------------------------------------------- fonts */
export const useFontsReady = () => {
  const [handle] = useState(() => delayRender('loading-fonts'));
  useEffect(() => {
    if (typeof document === 'undefined' || !document.fonts?.load) {
      continueRender(handle);
      return;
    }
    const loads = [
      '700 100px CairoExtra',
      '700 100px CairoBold',
      '700 100px Tajawal',
      '700 100px Amiri',
      '400 100px MS',
    ];
    Promise.all(loads.map((f) => document.fonts.load(f)))
      .then(() => document.fonts.ready)
      .then(() => continueRender(handle))
      .catch(() => continueRender(handle));
  }, [handle]);
};

/* ----------------------------------------------------------- background */
export const Background: React.FC<{ mood: Mood; seed?: number }> = ({ mood, seed = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps + seed;
  const m = MOODS[mood] ?? MOODS.calm;

  const blobs = [
    { x: 26 + Math.sin(t * 0.17) * 9, y: 20 + Math.cos(t * 0.13) * 7, s: 1180, c: m.glowA },
    { x: 78 + Math.cos(t * 0.11) * 8, y: 52 + Math.sin(t * 0.16) * 8, s: 980, c: m.glowB },
    { x: 44 + Math.sin(t * 0.09 + 2) * 12, y: 84 + Math.cos(t * 0.12 + 1) * 6, s: 1120, c: m.glowC },
  ];

  return (
    <AbsoluteFill style={{ background: m.base }}>
      {blobs.map((b, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `${b.x}%`,
            top: `${b.y}%`,
            width: b.s,
            height: b.s,
            transform: 'translate(-50%, -50%)',
            background: `radial-gradient(circle at center, ${b.c} 0%, rgba(0,0,0,0) 62%)`,
            filter: 'blur(6px)',
          }}
        />
      ))}

      {/* حلقات مدارية خفيفة */}
      {[0.72, 1, 1.3].map((k, i) => {
        const r = 380 * k;
        const spin = t * (i % 2 === 0 ? 5 : -4);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: '50%',
              top: '24%',
              width: r * 2,
              height: r * 2,
              marginLeft: -r,
              marginTop: -r,
              borderRadius: '50%',
              border: `${1.4 / k}px solid rgba(233,194,122,${0.14 / (i + 1)})`,
              maskImage: `conic-gradient(from ${spin}deg, #000 0deg, #000 ${22 / k}deg, transparent ${22 / k}deg, transparent 360deg)`,
              WebkitMaskImage: `conic-gradient(from ${spin}deg, #000 0deg, #000 ${22 / k}deg, transparent ${22 / k}deg, transparent 360deg)`,
            }}
          />
        );
      })}

      {/* غبار طائر */}
      {Array.from({ length: 26 }).map((_, i) => {
        const px = ((i * 137.5) % 100) + Math.sin(t * 0.4 + i) * 1.6;
        const py = ((i * 61.8 + t * 1.6) % 106) - 3;
        const size = 2 + (i % 4);
        const o = 0.06 + 0.1 * Math.abs(Math.sin(t * 1.1 + i));
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${px}%`,
              top: `${py}%`,
              width: size,
              height: size,
              borderRadius: '50%',
              background: 'rgba(241,227,200,0.9)',
              opacity: o,
            }}
          />
        );
      })}

      {/* خطوط ضوء أفقية لأجواء المعركة */}
      {m.streaks > 0 &&
        Array.from({ length: 9 }).map((_, i) => {
          const y = 8 + i * 11;
          const shift = ((t * (140 + i * 30)) % (W + 600)) - 300;
          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                top: `${y}%`,
                left: shift - 500,
                width: 620,
                height: 1.5 + (i % 3),
                background:
                  'linear-gradient(90deg, rgba(255,150,90,0) 0%, rgba(255,150,90,0.22) 50%, rgba(255,150,90,0) 100%)',
              }}
            />
          );
        })}

      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: m.tint,
          mixBlendMode: 'screen',
        }}
      />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------- grain/vignette */
export const Grain: React.FC = () => (
  <AbsoluteFill
    style={{
      opacity: 0.085,
      mixBlendMode: 'overlay',
      backgroundImage:
        "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/></filter><rect width='220' height='220' filter='url(%23n)' opacity='0.55'/></svg>\")",
      backgroundSize: '220px 220px',
      pointerEvents: 'none',
    }}
  />
);

export const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      background:
        'radial-gradient(120% 78% at 50% 46%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.45) 78%, rgba(0,0,0,0.82) 100%)',
      pointerEvents: 'none',
    }}
  />
);

/* -------------------------------------------------------------- overlays */
export const ChapterLabel: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = interpolate(frame, [fps * 0.9, fps * 1.6], [0, 1], clamp);
  return (
    <div
      style={{
        position: 'absolute',
        top: 132,
        width: '100%',
        textAlign: 'center',
        opacity: 0.5 * a,
        fontFamily: FONT.bold,
        fontSize: 38,
        letterSpacing: 1,
        color: COLORS.gold2,
      }}
    >
      {text}
      <div
        style={{
          width: 68,
          height: 2,
          margin: '14px auto 0',
          background: COLORS.gold2,
          opacity: 0.5,
        }}
      />
    </div>
  );
};

export const ProgressBar: React.FC<{ p: number }> = ({ p }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = interpolate(frame, [fps * 1.0, fps * 1.8], [0, 1], clamp);
  return (
    <div style={{ position: 'absolute', bottom: 78, left: 100, right: 100, opacity: a }}>
      <div style={{ height: 3, background: 'rgba(245,239,230,0.10)', borderRadius: 2 }} />
      <div
        style={{
          position: 'absolute',
          top: 0,
          height: 3,
          width: `${Math.max(0.4, Math.min(100, p * 100))}%`,
          background: COLORS.gold2,
          borderRadius: 2,
          opacity: 0.75,
        }}
      />
    </div>
  );
};

export const Flash: React.FC = () => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [0, 3, 9], [0.3, 0.1, 0], clamp);
  return <AbsoluteFill style={{ background: '#fff', opacity: o, pointerEvents: 'none' }} />;
};

/* ----------------------------------------------------------------- text */
/** تنظيف علامات الترقيم غير المدعومة في الخطوط (نفس منطق النسخة بايثون). */
export const sanitize = (t: string): string =>
  t
    .replace(/\u2026/g, '\u060C')
    .replace(/[\u00AB\u00BB]/g, '')
    .replace(/[\u00B7\u2022]/g, '-')
    .replace(/\s+/g, ' ')
    .trim();
type WordsProps = {
  text: string;
  size: number;
  color: string;
  font?: string;
  delay?: number;
  stagger?: number;
  maxWidth?: number;
  glow?: number;
  gapEm?: number;
  lineHeight?: number;
  align?: 'center' | 'right';
};

const useReveal = (delay: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const start = delay * fps;
  const s = spring({ frame: frame - start, fps, config: SPRING.word });
  const opacity = interpolate(frame, [start, start + 7], [0, 1], clamp);
  const blur = (1 - s) * 16;
  return { s, opacity, blur };
};

export const Words: React.FC<WordsProps> = ({
  text,
  size,
  color,
  font = FONT.display,
  delay = 0,
  stagger = 0.12,
  maxWidth = 940,
  glow = 0.16,
  gapEm = 0.22,
  lineHeight = 1.28,
  align = 'center',
}) => {
  const words = sanitize(text).split(/\s+/).filter(Boolean);
  return (
    <div
      dir="rtl"
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: align === 'center' ? 'center' : 'flex-start',
        columnGap: size * gapEm,
        rowGap: size * 0.12,
        maxWidth,
        margin: '0 auto',
        fontFamily: font,
        fontSize: size,
        lineHeight,
        color,
        fontWeight: 700,
      }}
    >
      {words.map((w, i) => (
        <Word key={`${w}-${i}`} text={w} delay={delay + i * stagger} glow={glow} color={color} />
      ))}
    </div>
  );
};

const Word: React.FC<{ text: string; delay: number; glow: number; color: string }> = ({
  text,
  delay,
  glow,
  color,
}) => {
  const { s, opacity, blur } = useReveal(delay);
  return (
    <span
      style={{
        display: 'inline-block',
        opacity,
        transform: `translateY(${(1 - s) * 78}px) scale(${0.82 + 0.18 * s})`,
        filter: blur > 0.3 ? `blur(${blur}px)` : undefined,
        textShadow: glow > 0 ? `0 0 ${38 * glow}px ${hexA(color, glow * 0.55)}` : undefined,
      }}
    >
      {text}
    </span>
  );
};

export const Block: React.FC<{
  text: string;
  size: number;
  color: string;
  font?: string;
  delay?: number;
  rise?: number;
  maxWidth?: number;
  lineHeight?: number;
}> = ({ text, size, color, font = FONT.display, delay = 0, rise = 54, maxWidth = 900, lineHeight = 1.5 }) => {
  const { s, opacity, blur } = useReveal(delay);
  return (
    <div
      dir="rtl"
      style={{
        maxWidth,
        margin: '0 auto',
        textAlign: 'center',
        fontFamily: font,
        fontSize: size,
        lineHeight,
        color,
        fontWeight: 700,
        opacity,
        transform: `translateY(${(1 - s) * rise}px)`,
        filter: blur > 0.3 ? `blur(${blur * 0.6}px)` : undefined,
      }}
    >
      {sanitize(text)}
    </div>
  );
};

const hexA = (hex: string, a: number) => {
  if (hex.startsWith('rgba') || hex.startsWith('rgb')) return hex;
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${Math.min(1, a)})`;
};

/* --------------------------------------------------------------- shapes */
export const Rule: React.FC<{ width: number; delay?: number; color?: string; opacity?: number; thickness?: number }> = ({
  width,
  delay = 0.35,
  color = COLORS.gold2,
  opacity = 0.8,
  thickness = 4,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = interpolate(frame, [delay * fps, (delay + 0.5) * fps], [0, 1], clamp);
  return (
    <div
      style={{
        width: width * p,
        height: thickness,
        borderRadius: thickness,
        background: color,
        opacity: opacity * p,
        margin: '0 auto',
      }}
    />
  );
};

export const Spine: React.FC<{ height: number; delay?: number }> = ({ height, delay = 0.2 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = interpolate(frame, [delay * fps, (delay + 0.6) * fps], [0, 1], clamp);
  return (
    <div style={{ width: 2, height: height * p, margin: '0 auto', background: COLORS.gold2, opacity: 0.16 }}>
      <div
        style={{
          width: 14,
          height: 14,
          marginLeft: -6,
          marginTop: -7,
          borderRadius: 4,
          background: COLORS.gold2,
          opacity: p * 0.9,
        }}
      />
    </div>
  );
};

export const Glyph: React.FC<{
  name?: string;
  size: number;
  color?: string;
  opacity?: number;
  delay?: number;
  rings?: number[];
}> = ({ name, size, color = COLORS.gold2, opacity = 0.9, delay = 0, rings = [] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay * fps, fps, config: SPRING.pop });
  const p = interpolate(frame, [delay * fps, delay * fps + fps * 0.8], [0, 1], clamp);
  const glyph = iconGlyph(name);
  return (
    <div style={{ position: 'relative', width: size * 2, height: size * 2, margin: '0 auto' }}>
      {rings.map((r, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            width: r * 2 * (1 + (1 - p) * 0.08),
            height: r * 2 * (1 + (1 - p) * 0.08),
            marginLeft: -r,
            marginTop: -r,
            borderRadius: '50%',
            border: `${i === 0 ? 2.2 : 1.1}px solid ${hexA(color, (i === 0 ? 0.4 : 0.2) * p)}`,
          }}
        />
      ))}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: FONT.icon,
          fontSize: size * 1.5,
          color,
          opacity: opacity * p,
          transform: `scale(${0.7 + 0.3 * s}) rotate(${(1 - s) * -12}deg)`,
          filter: `drop-shadow(0 0 30px ${hexA(color, 0.35)})`,
        }}
      >
        {glyph}
      </div>
    </div>
  );
};
