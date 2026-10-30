import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Scene } from './story';
import { COLORS, FONT, H, W } from './theme';
import {
  Background,
  Block,
  Flash,
  Glyph,
  Rule,
  Spine,
  Words,
} from './components';

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/** عنصر مثبّت رأسيًا على نقطة محددة (متوسّطه على top) */
const At: React.FC<{ top: number; children: React.ReactNode; width?: number }> = ({ top, children, width }) => (
  <div
    style={{
      position: 'absolute',
      top,
      left: 0,
      right: 0,
      transform: 'translateY(-50%)',
      display: 'flex',
      justifyContent: 'center',
      ...(width ? { width, margin: '0 auto' } : {}),
    }}
  >
    <div style={{ width: '100%' }}>{children}</div>
  </div>
);

export const SceneView: React.FC<{ scene: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();
  const punch = interpolate(frame, [0, 14], [1.055, 1], clamp);
  const exit = interpolate(frame, [durationInFrames - 6, durationInFrames], [0, 1], clamp);

  return (
    <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: COLORS.ink }}>
      <AbsoluteFill style={{ transform: `scale(${punch})`, transformOrigin: '50% 42%' }}>
        <Background mood={scene.mood} seed={scene.t0} />
        <AbsoluteFill style={{ opacity: 1 - exit }}>
          <SceneContent scene={scene} />
        </AbsoluteFill>
      </AbsoluteFill>
      <Flash />
    </AbsoluteFill>
  );
};

const SceneContent: React.FC<{ scene: Scene }> = ({ scene }) => {
  switch (scene.kind) {
    case 'title':
      return <TitleScene scene={scene} />;
    case 'hero':
      return <HeroScene scene={scene} />;
    case 'quote':
      return <QuoteScene scene={scene} />;
    case 'caption':
      return <CaptionScene scene={scene} />;
    case 'icon':
      return <IconScene scene={scene} />;
    case 'end':
      return <EndScene scene={scene} />;
    default:
      return null;
  }
};

/* ------------------------------------------------------------------ title */
const TitleScene: React.FC<{ scene: Scene }> = ({ scene }) => (
  <>
    <At top={400}>
      <Glyph name="mosque" size={290} opacity={0.34} delay={0.05} rings={[232, 288]} />
    </At>
    <At top={706}>
      <Words text={scene.kicker ?? ''} size={60} color={COLORS.gold} delay={0.15} stagger={0.05} glow={0.06} />
    </At>
    <At top={880}>
      <Words
        text={scene.main ?? ''}
        size={188}
        color={COLORS.ivory}
        delay={0.3}
        stagger={0.16}
        glow={0.3}
        maxWidth={1000}
      />
    </At>
    <At top={1036}>
      <Rule width={340} delay={0.62} opacity={0.85} />
    </At>
    <At top={1152}>
      <Block text={scene.sub ?? ''} size={72} color={COLORS.mint} delay={0.75} rise={40} maxWidth={980} />
    </At>
  </>
);

/* ------------------------------------------------------------------- hero */
const HeroScene: React.FC<{ scene: Scene }> = ({ scene }) => {
  const baseY = scene.y ?? 950;
  return (
    <>
      {scene.icon ? (
        <At top={baseY - 520}>
          <Glyph name={scene.icon} size={300} opacity={0.46} delay={0.02} rings={[190, 245]} />
        </At>
      ) : (
        <At top={(300 + (baseY - 260)) / 2}>
          <Spine height={baseY - 560} delay={0.1} />
        </At>
      )}
      {scene.kicker ? (
        <At top={baseY - 268}>
          <Words text={scene.kicker} size={58} color={COLORS.gold} delay={0.1} stagger={0.05} glow={0.05} />
        </At>
      ) : null}
      <At top={baseY}>
        <Words
          text={scene.main ?? ''}
          size={scene.size ?? 200}
          color={COLORS.ivory}
          delay={0.22}
          stagger={0.15}
          glow={0.26}
          maxWidth={1000}
        />
      </At>
      {scene.sub ? (
        <>
          <At top={baseY + 196}>
            <Rule width={260} delay={0.7} opacity={0.7} thickness={3} />
          </At>
          <At top={baseY + 300}>
            <Block
              text={scene.sub}
              size={scene.subsize ?? 76}
              color={scene.subcolor ? `#${scene.subcolor}` : COLORS.mint}
              delay={0.85}
              rise={36}
              maxWidth={900}
            />
          </At>
        </>
      ) : null}
    </>
  );
};

/* ------------------------------------------------------------------ quote */
const QuoteScene: React.FC<{ scene: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const size = scene.size ?? 126;
  const lines = (scene.text ?? '').split(/\\N/);
  const cy = scene.cy ?? 950;
  const cardW = 912;

  const grow = interpolate(frame, [0, 0.5 * fps], [0, 1], clamp);
  const labelA = interpolate(frame, [0.12 * fps, 0.5 * fps], [0, 1], clamp);

  return (
    <>
      <div
        style={{
          position: 'absolute',
          top: cy,
          left: (W - cardW) / 2,
          width: cardW,
          transform: 'translateY(-50%)',
        }}
      >
        {/* الكارت */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: 70,
            background: scene.pad ? 'rgba(27,18,9,0.6)' : 'rgba(27,18,9,0.5)',
            borderTop: `2px solid rgba(199,154,75,${0.6 * grow})`,
            borderBottom: `2px solid rgba(199,154,75,${0.6 * grow})`,
            boxShadow: '0 30px 90px rgba(0,0,0,0.45)',
            opacity: grow,
          }}
        />
        {/* التسمية أعلى الكارت */}
        <div
          style={{
            position: 'absolute',
            top: -118,
            width: '100%',
            textAlign: 'center',
            fontFamily: FONT.bold,
            fontSize: 46,
            color: COLORS.gold,
            opacity: labelA,
          }}
        >
          {scene.label}
          <span
            style={{
              display: 'inline-block',
              width: 11,
              height: 11,
              borderRadius: 3,
              background: COLORS.gold2,
              marginRight: 22,
              verticalAlign: 'middle',
              transform: 'translateY(-4px)',
            }}
          />
        </div>

        {/* نص الاقتباس */}
        <div style={{ position: 'relative', padding: '104px 56px', display: 'flex', flexDirection: 'column', gap: size * 0.34 }}>
          {lines.map((line, i) => (
            <Block
              key={i}
              text={line}
              size={size}
              color={COLORS.quote}
              font={FONT.serif}
              delay={0.3 + i * 0.18}
              rise={44}
              maxWidth={800}
              lineHeight={1.62}
            />
          ))}
        </div>
      </div>
      <At top={cy - 250}>
        <div style={{ width: 1 }} />
      </At>
    </>
  );
};

/* ---------------------------------------------------------------- caption */
const CaptionScene: React.FC<{ scene: Scene }> = ({ scene }) => {
  const y = scene.y ?? 1180;
  return (
    <>
      {scene.icon ? (
        <At top={636}>
          <Glyph name={scene.icon} size={210} opacity={0.42} delay={0.02} rings={[138, 190]} />
        </At>
      ) : (
        <At top={560}>
          <Spine height={320} delay={0.1} />
        </At>
      )}
      <At top={y - 128}>
        <Rule width={64} delay={0.2} opacity={0.4} thickness={3} />
      </At>
      <At top={y}>
        <Words
          text={scene.main ?? ''}
          size={scene.size ?? 96}
          color={COLORS.ivory}
          delay={0.14}
          stagger={0.07}
          glow={0.16}
          maxWidth={980}
        />
      </At>
      {scene.sub ? (
        <At top={y + 152}>
          <Block
            text={scene.sub}
            size={scene.subsize ?? 70}
            color={scene.subcolor ? `#${scene.subcolor}` : COLORS.gold}
            delay={0.5}
            rise={32}
            maxWidth={900}
          />
        </At>
      ) : null}
    </>
  );
};

/* ------------------------------------------------------------------- icon */
const IconScene: React.FC<{ scene: Scene }> = ({ scene }) => {
  const y = scene.y ?? 1150;
  return (
    <>
      <At top={720}>
        <Glyph name={scene.icon} size={320} opacity={0.92} delay={0.02} rings={[232, 288]} />
      </At>
      <At top={y}>
        <Words
          text={scene.main ?? ''}
          size={scene.size ?? 132}
          color={COLORS.ivory}
          delay={0.32}
          stagger={0.1}
          glow={0.14}
          maxWidth={920}
        />
      </At>
      {scene.sub ? (
        <At top={y + 168}>
          <Block
            text={scene.sub}
            size={scene.subsize ?? 72}
            color={scene.subcolor ? `#${scene.subcolor}` : COLORS.mint}
            delay={0.6}
            rise={34}
            maxWidth={900}
          />
        </At>
      ) : null}
    </>
  );
};

/* -------------------------------------------------------------------- end */
const EndScene: React.FC<{ scene: Scene }> = ({ scene }) => {
  const parts = (scene.main ?? '').split(/\\N/);
  return (
    <>
      <At top={640}>
        <Glyph name="favorite" size={270} opacity={0.3} delay={0.02} rings={[170, 225]} />
      </At>
      <At top={856}>
        <Block text={scene.label ?? ''} size={50} color={COLORS.gold} delay={0.15} rise={34} />
      </At>
      {parts.map((p, i) => (
        <At key={i} top={995 + i * 140}>
          <Block text={p} size={110} color={COLORS.ivory} delay={0.35 + i * 0.25} rise={46} maxWidth={950} />
        </At>
      ))}
      <At top={1226}>
        <Rule width={300} delay={0.95} opacity={0.8} />
      </At>
      <At top={1612}>
        <Block text="FIGO MOTION" size={44} color={COLORS.mint} delay={1.15} rise={24} />
      </At>
    </>
  );
};
