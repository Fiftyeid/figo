import React from 'react';
import {AbsoluteFill, useCurrentFrame, interpolate} from 'remotion';

// تحبيب فيلمي خفيف - أساسي في أسلوب Pinterest الأنيق
export const FilmGrain: React.FC = () => {
  const frame = useCurrentFrame();

  // حركة عشوائية للتحبيب
  const offsetX = (frame * 7) % 100;
  const offsetY = (frame * 11) % 100;

  return (
    <>
      {/* SVG grain */}
      <AbsoluteFill
        style={{
          opacity: 0.18,
          pointerEvents: 'none',
          mixBlendMode: 'overlay',
        }}
      >
        <svg
          width="100%"
          height="100%"
          style={{
            transform: `translate(${offsetX % 3}px, ${offsetY % 3}px)`,
          }}
        >
          <filter id="grain">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.9"
              numOctaves={3}
              stitchTiles="stitch"
            />
            <feColorMatrix type="saturate" values="0" />
          </filter>
          <rect width="100%" height="100%" filter="url(#grain)" opacity={0.4} />
        </svg>
      </AbsoluteFill>

      {/* Dust & scratches خفيف جداً */}
      <AbsoluteFill
        style={{
          opacity: interpolate(frame % 12, [0, 6, 12], [0.02, 0.06, 0.02]),
          background: `repeating-linear-gradient(
            90deg,
            transparent,
            transparent 2px,
            rgba(255,255,255,0.03) 2px,
            rgba(255,255,255,0.03) 3px
          )`,
          mixBlendMode: 'soft-light',
          pointerEvents: 'none',
        }}
      />

      {/* Light leak دافئ يظهر للحظات */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 20% 30%, rgba(255,180,120,0.12) 0%, transparent 60%),
                       radial-gradient(ellipse at 80% 80%, rgba(255,200,150,0.08) 0%, transparent 50%)`,
          opacity: interpolate(frame % 60, [0, 30, 60], [0.5, 0.8, 0.5]),
          mixBlendMode: 'soft-light',
          pointerEvents: 'none',
        }}
      />
    </>
  );
};
