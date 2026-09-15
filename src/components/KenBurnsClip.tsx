import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, Easing} from 'remotion';

type Props = {
  src: string;
  clipFrame: number;
  durationInFrames: number;
  index: number;
  isActive: boolean;
  fps: number;
};

export const KenBurnsClip: React.FC<Props> = ({
  src,
  clipFrame,
  durationInFrames,
  index,
  fps,
}) => {
  // Ken Burns: زوم بطيء جداً من 1 إلى 1.18
  // التناوب بين الزوم إن والزوم أوت لكل كليب (أسلوب Pinterest الأنيق)
  const isZoomIn = index % 2 === 0;

  const scale = interpolate(clipFrame, [0, durationInFrames], isZoomIn ? [1, 1.18] : [1.18, 1], {
    easing: Easing.inOut(Easing.quad),
    extrapolateRight: 'clamp',
  });

  // حركة أفقية خفيفة (pan)
  const translateX = interpolate(
    clipFrame,
    [0, durationInFrames],
    index % 3 === 0 ? [-20, 20] : index % 3 === 1 ? [15, -15] : [0, 0],
    {extrapolateRight: 'clamp'}
  );

  const translateY = interpolate(
    clipFrame,
    [0, durationInFrames],
    index % 2 === 0 ? [10, -10] : [-8, 8],
    {extrapolateRight: 'clamp'}
  );

  // انتقال الدخول: تكبير سريع + تلاشي (whip zoom)
  const enterProgress = spring({
    frame: clipFrame,
    fps,
    config: {damping: 100, stiffness: 200, mass: 0.8},
  });

  // للأول 8 فريمات: تأثير دخول
  const enterScale = interpolate(enterProgress, [0, 1], [1.15, 1]);
  const enterOpacity = interpolate(clipFrame, [0, 6], [0, 1], {
    extrapolateRight: 'clamp',
  });
  // بلور خفيف عند الدخول
  const blur = interpolate(clipFrame, [0, 8], [8, 0], {
    extrapolateRight: 'clamp',
  });

  // انتقال الخروج: تلاشي + زوم إضافي
  const exitOpacity = interpolate(
    clipFrame,
    [durationInFrames - 8, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  const combinedScale = scale * enterScale;
  const opacity = Math.min(enterOpacity, exitOpacity);

  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: '#0a0a0a'}}>
      <div
        style={{
          width: '100%',
          height: '100%',
          transform: `scale(${combinedScale}) translate(${translateX}px, ${translateY}px)`,
          opacity,
          filter: `blur(${blur}px) brightness(${interpolate(
            clipFrame,
            [0, 10, durationInFrames - 10, durationInFrames],
            [0.7, 1, 1, 0.8],
            {extrapolateRight: 'clamp'}
          )}) saturate(0.85) contrast(1.05)`,
          willChange: 'transform, filter, opacity',
        }}
      >
        <Img
          src={src}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: 'center',
          }}
        />
        {/* تدرج للحفاظ على قراءة النص */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'linear-gradient(0deg, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.25) 100%)',
          }}
        />
      </div>

      {/* خط أبيض وامض عند القطع - flash transition (أسلوب TikTok/Pinterest) */}
      {clipFrame < 3 && (
        <AbsoluteFill
          style={{
            background: 'white',
            opacity: interpolate(clipFrame, [0, 2], [0.18, 0], {
              extrapolateRight: 'clamp',
            }),
            pointerEvents: 'none',
          }}
        />
      )}
    </AbsoluteFill>
  );
};
