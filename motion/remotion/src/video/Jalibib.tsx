import React from 'react';
import {
  AbsoluteFill,
  Audio,
  interpolate,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { BEATS, chapterAt, DURATION, FPS, TOTAL_FRAMES } from './story';
import { SceneView } from './scenes';
import { ChapterLabel, Grain, ProgressBar, Vignette, useFontsReady } from './components';

export const VIDEO = {
  id: 'Jalibib',
  width: 1080,
  height: 1920,
  fps: FPS,
  durationInFrames: TOTAL_FRAMES,
};

const Fade: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const inA = interpolate(frame, [0, fps * 0.7], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const outA = interpolate(frame, [durationInFrames - fps * 1.1, durationInFrames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return <AbsoluteFill style={{ background: '#000', opacity: Math.max(inA, outA) }} />;
};

export const Jalibib: React.FC = () => {
  useFontsReady();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  return (
    <AbsoluteFill style={{ backgroundColor: '#050506' }}>
      <Audio src="/voice.mp3" />
      {BEATS.map((b, i) => (
        <Sequence
          key={`${b.t0}-${i}`}
          from={Math.round(b.t0 * FPS)}
          durationInFrames={Math.max(2, Math.round((b.t1 - b.t0) * FPS))}
        >
          <SceneView scene={b} />
        </Sequence>
      ))}
      <ChapterLabel text={chapterAt(t)} />
      <ProgressBar p={Math.min(1, t / DURATION)} />
      <Grain />
      <Vignette />
      <Fade />
    </AbsoluteFill>
  );
};
