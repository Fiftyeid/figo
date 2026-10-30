import { Composition, registerRoot } from 'remotion';
import { Jalibib, VIDEO } from './video/Jalibib';

const Root: React.FC = () => (
  <Composition
    id={VIDEO.id}
    component={Jalibib}
    durationInFrames={VIDEO.durationInFrames}
    fps={VIDEO.fps}
    width={VIDEO.width}
    height={VIDEO.height}
  />
);

registerRoot(Root);
