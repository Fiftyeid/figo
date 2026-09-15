import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  spring,
  Easing,
  Sequence,
} from 'remotion';
import {KenBurnsClip} from './components/KenBurnsClip';
import {KineticText} from './components/KineticText';
import {FilmGrain} from './components/FilmGrain';
import {Vignette} from './components/Vignette';
import {Fonts} from './components/Fonts';

export type ClipConfig = {
  src: string;
  label: string;
  sublabel?: string;
  durationInFrames: number;
};

export type PinterestMontageProps = {
  clips: ClipConfig[];
  title: string;
  subtitle: string;
};

// هذا هو التحليل الدقيق لأسلوب الفيديو في الرابط:
// الفيديو الأصلي هو مونتاج Pinterest الفيروسي (aesthetic montage)
// خصائصه: قطع سريع على الإيقاع، زوم تدريجي، نصوص حركية، تحبيب فيلمي

export const PinterestMontage: React.FC<PinterestMontageProps> = ({
  clips,
  title,
  subtitle,
}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // حساب الـ beat sync - القطع على الإيقاع
  // الفيديو الأصلي يستخدم إيقاع ~ 110-125 BPM مع قطع كل 0.8-1.2 ثانية
  let accumulated = 0;
  const clipRanges = clips.map((clip) => {
    const start = accumulated;
    const end = start + clip.durationInFrames;
    accumulated = end;
    return {clip, start, end};
  });

  // تحديد الكليب الحالي
  const currentClipIndex = clipRanges.findIndex(
    (r) => frame >= r.start && frame < r.end
  );
  const safeIndex = currentClipIndex === -1 ? clips.length - 1 : currentClipIndex;
  const currentRange = clipRanges[safeIndex];

  // Progress bar (شائع جداً في فيديوهات Pinterest)
  const progress = interpolate(frame, [0, durationInFrames], [0, 100]);

  // تأثير النبض على الإيقاع (pulsing)
  const beatPulse = Math.sin((frame / fps) * Math.PI * 2 * 2) * 0.5 + 0.5;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#0a0a0a',
        fontFamily: "'Instrument Serif', 'Playfair Display', serif",
        overflow: 'hidden',
      }}
    >
      <Fonts />
      {/* خلفية الكليبات مع Ken Burns + Cross Zoom */}
      {clipRanges.map(({clip, start, end}, index) => {
        const isActive = index === safeIndex;
        // نحسب هل الكليب انتهى أو قادم لإضافة انتقال
        const clipFrame = frame - start;
        
        return (
          <Sequence
            key={index}
            from={start}
            durationInFrames={clip.durationInFrames}
          >
            <KenBurnsClip
              src={clip.src}
              clipFrame={clipFrame}
              durationInFrames={clip.durationInFrames}
              index={index}
              isActive={isActive}
              fps={fps}
            />
            {/* تسمية الكليب - النص الحركي */}
            <KineticText
              label={clip.label}
              sublabel={clip.sublabel}
              clipFrame={clipFrame}
              fps={fps}
              index={index}
            />
          </Sequence>
        );
      })}

      {/* طبقة التدرج السينمائي - LUT warm */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.55) 100%)`,
          pointerEvents: 'none',
        }}
      />

      {/* vignette */}
      <Vignette />

      {/* film grain */}
      <FilmGrain />

      {/* Header ثابت - أسلوب Pinterest الأنيق */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          padding: '70px 50px 0 50px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          zIndex: 10,
          color: 'white',
        }}
      >
        <div
          style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontSize: 22,
            letterSpacing: '0.25em',
            fontWeight: 500,
            opacity: 0.9,
            transform: `translateY(${interpolate(
              frame,
              [0, 20],
              [ -20, 0],
              { extrapolateRight: 'clamp', easing: Easing.out(Easing.quad)}
            )}px)`,
          }}
        >
          Pinterest — 2026
        </div>
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: '50%',
            border: '1px solid rgba(255,255,255,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 18,
          }}
        >
          ✦
        </div>
      </div>

      {/* العنوان الرئيسي - ثابت مع نبض خفيف */}
      <div
        style={{
          position: 'absolute',
          bottom: 220,
          left: 0,
          right: 0,
          textAlign: 'center',
          zIndex: 10,
          color: 'white',
          padding: '0 40px',
        }}
      >
        {/* Subtitle صغير فوق العنوان */}
        <div
          style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontSize: 18,
            letterSpacing: '0.4em',
            fontWeight: 500,
            opacity: interpolate(frame, [0, 20, durationInFrames - 20, durationInFrames], [0, 0.7, 0.7, 0]),
            marginBottom: 18,
            transform: `translateY(${interpolate(frame, [0, 30], [10, 0], {extrapolateRight: 'clamp'})}px)`,
          }}
        >
          {subtitle.toUpperCase()}
        </div>

        <h1
          style={{
            fontFamily: "'Instrument Serif', serif",
            fontSize: 145,
            fontWeight: 400,
            lineHeight: 0.85,
            letterSpacing: '-0.04em',
            margin: 0,
            textShadow: '0 10px 40px rgba(0,0,0,0.4)',
            // نبض خفيف على الإيقاع
            transform: `scale(${1 + beatPulse * 0.008})`,
            // ظهور تدريجي
            opacity: interpolate(frame, [0, 15], [0, 1], {extrapolateRight: 'clamp'}),
          }}
        >
          {title.split(' ').map((word, i) => (
            <span
              key={i}
              style={{
                display: 'inline-block',
                transform: `translateY(${interpolate(
                  frame,
                  [10 + i * 6, 30 + i * 6],
                  [60, 0],
                  {
                    extrapolateLeft: 'clamp',
                    extrapolateRight: 'clamp',
                    easing: Easing.out(Easing.cubic),
                  }
                )}px)`,
                opacity: interpolate(frame, [10 + i * 6, 25 + i * 6], [0, 1], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                }),
              }}
            >
              {word}&nbsp;
            </span>
          ))}
        </h1>

        {/* خط زخرفي */}
        <div
          style={{
            width: interpolate(frame, [30, 60], [0, 120], {
              extrapolateRight: 'clamp',
              easing: Easing.out(Easing.quad),
            }),
            height: 1,
            background: 'white',
            margin: '28px auto 0 auto',
            opacity: 0.8,
          }}
        />

        {/* عداد الكليبات - 01 / 07 */}
        <div
          style={{
            fontFamily: "'Space Mono', monospace",
            fontSize: 16,
            letterSpacing: '0.2em',
            marginTop: 18,
            opacity: 0.7,
          }}
        >
          0{safeIndex + 1} &nbsp;—&nbsp; 0{clips.length}
        </div>
      </div>

      {/* Progress bar سفلي - مقسم حسب الكليبات */}
      <div
        style={{
          position: 'absolute',
          bottom: 60,
          left: 40,
          right: 40,
          height: 2,
          background: 'rgba(255,255,255,0.2)',
          borderRadius: 2,
          overflow: 'hidden',
          zIndex: 10,
          display: 'flex',
          gap: 6,
        }}
      >
        {clipRanges.map(({start, end}, i) => {
          const segmentProgress = interpolate(
            frame,
            [start, end],
            [0, 100],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
          );
          const isPast = frame >= end;
          const isCurrent = frame >= start && frame < end;
          
          return (
            <div
              key={i}
              style={{
                flex: 1,
                height: '100%',
                background: 'rgba(255,255,255,0.2)',
                borderRadius: 2,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${isPast ? 100 : isCurrent ? segmentProgress : 0}%`,
                  height: '100%',
                  background: 'white',
                  transition: 'width 0.1s linear',
                }}
              />
            </div>
          );
        })}
      </div>

      {/* Footer - CTA */}
      <div
        style={{
          position: 'absolute',
          bottom: 90,
          left: 0,
          right: 0,
          textAlign: 'center',
          zIndex: 10,
          opacity: interpolate(frame, [durationInFrames - 40, durationInFrames - 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        <div
          style={{
            display: 'inline-block',
            border: '1px solid rgba(255,255,255,0.9)',
            borderRadius: 100,
            padding: '12px 28px',
            fontFamily: "'Space Grotesk', sans-serif",
            fontSize: 15,
            letterSpacing: '0.15em',
            color: 'white',
            background: 'rgba(255,255,255,0.08)',
            backdropFilter: 'blur(10px)',
          }}
        >
          SAVE →
        </div>
      </div>
    </AbsoluteFill>
  );
};

// نسخة مختصرة 5 ثواني للاختبار السريع
export const PinterestMontageShort: React.FC<PinterestMontageProps> = (props) => {
  return <PinterestMontage {...props} />;
};
