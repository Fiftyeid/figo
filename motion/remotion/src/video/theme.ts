import type { Mood } from './story';

export const W = 1080;
export const H = 1920;

export const COLORS = {
  ivory: '#F5EFE6',
  gold: '#E9C27A',
  gold2: '#C79A4B',
  mint: '#8FD3C1',
  red: '#D98B7F',
  quote: '#F8E9C8',
  paper: 'rgba(27,18,9,0.52)',
  ink: '#050506',
};

export const FONT = {
  display: "'CairoExtra', 'Cairo', sans-serif",
  bold: "'CairoBold', 'Cairo', sans-serif",
  num: "'Tajawal', 'Cairo', sans-serif",
  serif: "'Amiri', 'Cairo', serif",
  icon: "'MS', sans-serif",
};

type MoodStyle = {
  base: string;
  glowA: string;
  glowB: string;
  glowC: string;
  streaks: number;
  tint: string;
};

export const MOODS: Record<Mood, MoodStyle> = {
  calm: {
    base: 'radial-gradient(120% 80% at 50% 10%, #0E0C12 0%, #08080B 55%, #040405 100%)',
    glowA: 'rgba(90,63,28,0.55)',
    glowB: 'rgba(20,82,74,0.35)',
    glowC: 'rgba(52,44,82,0.25)',
    streaks: 0,
    tint: 'rgba(255,255,255,0)',
  },
  warm: {
    base: 'radial-gradient(120% 80% at 50% 8%, #171009 0%, #0B0907 55%, #040404 100%)',
    glowA: 'rgba(120,78,30,0.70)',
    glowB: 'rgba(24,86,74,0.36)',
    glowC: 'rgba(96,58,22,0.28)',
    streaks: 0,
    tint: 'rgba(255,196,120,0.04)',
  },
  pray: {
    base: 'radial-gradient(120% 80% at 50% 8%, #0D1210 0%, #080B09 55%, #040504 100%)',
    glowA: 'rgba(72,110,86,0.42)',
    glowB: 'rgba(120,92,40,0.35)',
    glowC: 'rgba(20,74,74,0.28)',
    streaks: 0,
    tint: 'rgba(200,255,220,0.03)',
  },
  battle: {
    base: 'radial-gradient(120% 80% at 50% 8%, #170D08 0%, #0C0806 55%, #050303 100%)',
    glowA: 'rgba(150,66,32,0.55)',
    glowB: 'rgba(96,40,18,0.42)',
    glowC: 'rgba(60,74,60,0.22)',
    streaks: 1,
    tint: 'rgba(255,140,90,0.05)',
  },
  dark: {
    base: 'radial-gradient(120% 80% at 50% 10%, #0B0D14 0%, #07080D 55%, #030304 100%)',
    glowA: 'rgba(60,70,120,0.32)',
    glowB: 'rgba(80,60,30,0.28)',
    glowC: 'rgba(16,60,66,0.22)',
    streaks: 0,
    tint: 'rgba(180,200,255,0.03)',
  },
  end: {
    base: 'radial-gradient(120% 80% at 50% 12%, #12100C 0%, #090807 55%, #040404 100%)',
    glowA: 'rgba(110,80,34,0.45)',
    glowB: 'rgba(30,80,72,0.30)',
    glowC: 'rgba(60,46,30,0.22)',
    streaks: 0,
    tint: 'rgba(255,235,200,0.03)',
  },
};

/** إيقاع الحركة الموحّد */
export const SPRING = {
  word: { damping: 200, mass: 0.5, stiffness: 130 },
  pop: { damping: 12, mass: 0.6, stiffness: 180 },
  soft: { damping: 200, mass: 1, stiffness: 90 },
};
