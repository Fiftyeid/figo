import React from 'react';
import {AbsoluteFill, interpolate, spring, Easing} from 'remotion';

type Props = {
  label: string;
  sublabel?: string;
  clipFrame: number;
  fps: number;
  index: number;
};

export const KineticText: React.FC<Props> = ({
  label,
  sublabel,
  clipFrame,
  fps,
}) => {
  // حركة النص: pop + slide
  const s = spring({
    frame: clipFrame,
    fps,
    config: {damping: 16, stiffness: 180, mass: 0.6},
  });

  // تأخير بسيط للـ sublabel
  const subSpring = spring({
    frame: Math.max(0, clipFrame - 6),
    fps,
    config: {damping: 14, stiffness: 160},
  });

  const opacity = interpolate(clipFrame, [0, 8, 28, 36], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // خروج بانزلاق للأعلى
  const exitY = interpolate(
    clipFrame,
    [24, 36],
    [0, -40],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.quad)}
  );

  const y = interpolate(s, [0, 1], [50, 0]);
  const scale = interpolate(s, [0, 1], [0.85, 1]);
  const rotate = interpolate(s, [0, 1], [-2, 0]);

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        pointerEvents: 'none',
        opacity,
        transform: `translateY(${exitY}px)`,
      }}
    >
      {/* خلفية نص شبه شفافة - أسلوب Pinterest */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          transform: `translateY(${y}px) scale(${scale}) rotate(${rotate}deg)`,
          filter: `blur(${interpolate(s, [0, 1], [6, 0])}px)`,
        }}
      >
        {/* label الرئيسي */}
        <div
          style={{
            fontFamily: "'Instrument Serif', serif",
            fontSize: 92,
            fontWeight: 400,
            color: 'white',
            lineHeight: 1,
            letterSpacing: '0.08em',
            textAlign: 'center',
            textShadow: '0 4px 30px rgba(0,0,0,0.5)',
            // تأثير outline خفيف
            WebkitTextStroke: '0.5px rgba(255,255,255,0.3)',
            padding: '0 20px',
            // كل حرف يظهر بتأخير (stagger)
            display: 'flex',
            gap: '0.06em',
          }}
        >
          {label.split('').map((char, i) => {
            const charDelay = i * 1.5;
            const charSpring = spring({
              frame: Math.max(0, clipFrame - charDelay),
              fps,
              config: {damping: 14, stiffness: 220},
            });
            const charY = interpolate(charSpring, [0, 1], [40, 0]);
            const charOpacity = interpolate(charSpring, [0, 1], [0, 1]);
            return (
              <span
                key={i}
                style={{
                  display: 'inline-block',
                  transform: `translateY(${charY}px)`,
                  opacity: charOpacity,
                }}
              >
                {char === ' ' ? '\u00A0' : char}
              </span>
            );
          })}
        </div>

        {sublabel && (
          <div
            style={{
              marginTop: 16,
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              transform: `translateY(${interpolate(
                subSpring,
                [0, 1],
                [20, 0]
              )}px)`,
              opacity: subSpring,
            }}
          >
            <div
              style={{
                width: interpolate(subSpring, [0, 1], [0, 28]),
                height: 1,
                background: 'white',
                opacity: 0.8,
              }}
            />
            <span
              style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: 15,
                letterSpacing: '0.35em',
                color: 'rgba(255,255,255,0.95)',
                fontWeight: 400,
                textShadow: '0 2px 10px rgba(0,0,0,0.6)',
              }}
            >
              {sublabel}
            </span>
            <div
              style={{
                width: interpolate(subSpring, [0, 1], [0, 28]),
                height: 1,
                background: 'white',
                opacity: 0.8,
              }}
            />
          </div>
        )}
      </div>

      {/* رقم الكليب في الزاوية - أسلوب تحريري */}
      <div
        style={{
          position: 'absolute',
          bottom: 300,
          right: 50,
          fontFamily: "'Space Mono', monospace",
          fontSize: 90,
          fontWeight: 700,
          color: 'transparent',
          WebkitTextStroke: '1px rgba(255,255,255,0.18)',
          lineHeight: 1,
          transform: `translateX(${interpolate(s, [0, 1], [30, 0])}px)`,
          opacity: interpolate(s, [0, 1], [0, 1]),
        }}
      >
        0{((clipFrame % 7) + 1).toFixed(0).padStart(1, '0')}
      </div>
    </AbsoluteFill>
  );
};
