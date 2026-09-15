import React from 'react';
import {AbsoluteFill} from 'remotion';

export const Vignette: React.FC = () => {
  return (
    <>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at center, transparent 58%, rgba(0,0,0,0.45) 100%)`,
          pointerEvents: 'none',
        }}
      />
      <AbsoluteFill
        style={{
          boxShadow: 'inset 0 0 120px rgba(0,0,0,0.35)',
          pointerEvents: 'none',
        }}
      />
      {/* إطار داخلي أبيض رفيع - لمسة Pinterest */}
      <div
        style={{
          position: 'absolute',
          inset: 22,
          border: '1px solid rgba(255,255,255,0.14)',
          borderRadius: 18,
          pointerEvents: 'none',
        }}
      />
    </>
  );
};
