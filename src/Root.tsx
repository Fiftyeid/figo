import React from 'react';
import {Composition} from 'remotion';
import {PinterestMontage, PinterestMontageShort, PinterestMontageProps} from './PinterestMontage';

// إعدادات الفيديو الأساسية - مقاسات Pinterest المثالية
// Pinterest يفضل 9:16 (1080x1920) و 2:3 (1000x1500)
// هنا نستخدم 9:16 لأنه الأكثر انتشاراً و "immersive"

const defaultProps: PinterestMontageProps = {
  clips: [
    {
      src: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1080&q=80',
      label: 'MORNING',
      sublabel: '05:30 AM',
      durationInFrames: 36, // 1.2s @30fps
    },
    {
      src: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1080&q=80',
      label: 'RITUAL',
      sublabel: 'COFFEE & LIGHT',
      durationInFrames: 30, // 1s
    },
    {
      src: 'https://images.unsplash.com/photo-1485230895905-ec40ba36b9bc?w=1080&q=80',
      label: 'STYLE',
      sublabel: 'LESS IS MORE',
      durationInFrames: 36,
    },
    {
      src: 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=1080&q=80',
      label: 'CITY',
      sublabel: 'IN MOTION',
      durationInFrames: 28,
    },
    {
      src: 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=1080&q=80',
      label: 'DETAILS',
      sublabel: 'THAT MATTER',
      durationInFrames: 36,
    },
    {
      src: 'https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?w=1080&q=80',
      label: 'GOLDEN HOUR',
      sublabel: 'STAY SOFT',
      durationInFrames: 45,
    },
    {
      src: 'https://images.unsplash.com/photo-1445205170230-053b83016050?w=1080&q=80',
      label: 'EDIT',
      sublabel: 'YOUR STORY',
      durationInFrames: 39,
    },
  ],
  title: 'SOFT ERA',
  subtitle: 'a Pinterest montage',
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="PinterestMontage"
        component={PinterestMontage}
        durationInFrames={250} // ~8.3s @30fps - نسخة 8 ثواني (الأكثر انتشاراً)
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultProps}
        calculateMetadata={async ({props}) => {
          const total = props.clips.reduce((a, c) => a + c.durationInFrames, 0);
          return {
            durationInFrames: total,
            props,
          };
        }}
      />
      <Composition
        id="PinterestMontageShort"
        component={PinterestMontageShort}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultProps}
      />
      {/* نسخة مربعة 1:1 لأجهزة مختلفة */}
      <Composition
        id="PinterestMontageSquare"
        component={PinterestMontage}
        durationInFrames={250}
        fps={30}
        width={1080}
        height={1080}
        defaultProps={defaultProps}
      />
    </>
  );
};
