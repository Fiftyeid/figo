// ملف مُولَّد آليًا من story2.py — لا تعدّله يدويًا.
export type Mood = 'calm' | 'warm' | 'pray' | 'battle' | 'dark' | 'end';
export type Kind = 'title' | 'hero' | 'quote' | 'caption' | 'icon' | 'end';
export type Scene = {
  kind: Kind; t0: number; t1: number; mood: Mood;
  main?: string; sub?: string; kicker?: string; label?: string; text?: string;
  icon?: string; size?: number; subsize?: number; subcolor?: string; color?: string;
  y?: number; cy?: number; maxw?: number; pad?: number; echo?: string;
};

export const FPS = 30;
export const DURATION = 181.0;
export const TOTAL_FRAMES = 5430;

export const CHAPTERS: { t: number; label: string }[] = [
  { t: 0.0, label: "١ · رجلٌ لا يعرفه أحد" },
  { t: 25.3, label: "٢ · الخطبة والزواج" },
  { t: 111.5, label: "٣ · المعركة والبحث" },
  { t: 159.0, label: "٤ · هذا منّي وأنا منه" },
];

export const BEATS: Scene[] = [
  {"kind": "title", "t0": 0.2, "t1": 3.3, "mood": "calm", "main": "قصّة جليبيب", "sub": "صحابيّ… لا حسبَ ولا نسبَ ولا مال", "kicker": "من صحيح مسلم"},
  {"kind": "hero", "t0": 3.4, "t1": 7.6, "mood": "dark", "main": "ولا أهل… ولا قوم", "kicker": "لا يُعرف له نسبٌ", "icon": "groups", "size": 190},
  {"kind": "hero", "t0": 7.7, "t1": 13.7, "mood": "dark", "main": "دميمُ الخِلقة", "sub": "لم يكن له من الجمالِ نصيب", "size": 200},
  {"kind": "icon", "t0": 13.9, "t1": 18.5, "mood": "calm", "main": "دائمَ الذكرِ لربّه", "sub": "لا يفارقُ الصفَّ الأوّل", "icon": "menu_book"},
  {"kind": "icon", "t0": 18.6, "t1": 25.2, "mood": "warm", "main": "يراه النبيُّ ﷺ في المسجد", "sub": "أعزبَ… لم يتزوّج", "icon": "mosque", "size": 116},
  {"kind": "quote", "t0": 25.3, "t1": 31.7, "mood": "warm", "label": "قال له النبيُّ صلّى الله عليه وسلّم", "text": "«يا جليبيب… ألا تتزوّج؟»", "size": 132},
  {"kind": "hero", "t0": 31.8, "t1": 35.1, "mood": "calm", "main": "ومن يُزوّجني؟", "sub": "لا حسبَ لي ولا نسبَ ولا مال", "size": 190},
  {"kind": "caption", "t0": 35.2, "t1": 38.6, "mood": "calm", "main": "فسأله مرّةً ثانية… وثالثة", "sub": "وكان الجوابُ هو الجواب", "icon": "forum"},
  {"kind": "icon", "t0": 38.7, "t1": 47.2, "mood": "warm", "main": "اذهب إلى بيتِ فلانٍ من الأنصار", "sub": "وقل: رسولُ اللهِ يخطبُ ابنتك", "icon": "door_front", "size": 104, "y": 1140},
  {"kind": "hero", "t0": 47.3, "t1": 52.5, "mood": "warm", "main": "طرقَ الباب", "sub": "وبلّغ الرسالة", "size": 210},
  {"kind": "quote", "t0": 52.6, "t1": 58.0, "mood": "warm", "label": "قال جليبيب", "text": "«رسولُ اللهِ يخطبُ ابنتك»", "size": 126},
  {"kind": "hero", "t0": 58.0, "t1": 63.8, "mood": "calm", "main": "شافعٌ… أم آمر؟", "sub": "وهو يخطبُ ابنتك", "size": 180},
  {"kind": "hero", "t0": 63.9, "t1": 69.8, "mood": "calm", "main": "أمرُ رسولِ الله", "sub": "لا يُرَدّ", "size": 170, "subcolor": "E9C27A"},
  {"kind": "caption", "t0": 69.9, "t1": 76.5, "mood": "calm", "main": "فدخل جليبيب… وبلّغ أمَّ الفتاة", "icon": "campaign"},
  {"kind": "hero", "t0": 76.6, "t1": 82.4, "mood": "warm", "main": "لا أُزوّجه", "sub": "غضبت أمُّها", "size": 210, "color": "D98B7F"},
  {"kind": "quote", "t0": 82.5, "t1": 91.1, "mood": "warm", "label": "قالت الفتاة", "text": "«أتردّانِ على رسولِ اللهِ\\Nأمرَه؟»", "size": 120},
  {"kind": "caption", "t0": 91.2, "t1": 95.2, "mood": "calm", "main": "افعلوا ما أمر… فإنّه لن يُضيّعني", "icon": "handshake"},
  {"kind": "hero", "t0": 95.3, "t1": 99.6, "mood": "warm", "main": "فرضي الأبوان", "sub": "وتمّ الأمر", "icon": "favorite", "size": 185},
  {"kind": "caption", "t0": 99.7, "t1": 104.5, "mood": "calm", "main": "وكان درسًا: الزواجُ بالدِّينِ والخُلُق", "icon": "school"},
  {"kind": "caption", "t0": 104.6, "t1": 107.2, "mood": "pray", "main": "فدعا لهما النبيُّ ﷺ", "icon": "folded_hands"},
  {"kind": "quote", "t0": 107.3, "t1": 111.4, "mood": "pray", "label": "دعاء النبيّ صلّى الله عليه وسلّم", "text": "«اللهم صبِّ عليهما الخيرَ صبًّا\\Nولا تجعل عيشَهما كَدًّا»", "size": 104},
  {"kind": "hero", "t0": 111.5, "t1": 116.5, "mood": "battle", "main": "ثم جاءت المعركة", "icon": "swords", "size": 175},
  {"kind": "caption", "t0": 116.6, "t1": 119.3, "mood": "battle", "main": "وجاء معها الامتحان", "icon": "bolt"},
  {"kind": "icon", "t0": 119.4, "t1": 125.2, "mood": "battle", "main": "في الصفِّ الأوّل", "sub": "جاهزًا للقتال", "icon": "shield"},
  {"kind": "hero", "t0": 125.3, "t1": 129.1, "mood": "battle", "main": "قامت المعركة", "size": 200},
  {"kind": "caption", "t0": 129.2, "t1": 131.5, "mood": "battle", "main": "وانتصر المسلمون نصرًا مؤزّرًا", "icon": "flag"},
  {"kind": "caption", "t0": 131.6, "t1": 135.2, "mood": "calm", "main": "وقف النبيُّ ﷺ يتفقّدُ أصحابه", "icon": "groups"},
  {"kind": "caption", "t0": 135.3, "t1": 138.6, "mood": "calm", "main": "فيُعدّون له الشهداء", "sub": "واحدًا واحدًا", "icon": "checklist"},
  {"kind": "caption", "t0": 138.7, "t1": 141.8, "mood": "calm", "main": "حتى قالوا: ما بقيَ أحد", "icon": "group_off"},
  {"kind": "quote", "t0": 141.9, "t1": 146.7, "mood": "warm", "label": "قال صلّى الله عليه وسلّم", "text": "«إنّي أفتقدُ جليبيبًا»", "size": 132},
  {"kind": "caption", "t0": 146.8, "t1": 150.4, "mood": "calm", "main": "قالوا: لا نعلم يا رسولَ الله", "icon": "help"},
  {"kind": "caption", "t0": 150.5, "t1": 152.4, "mood": "calm", "main": "قال: قوموا معي نبحثُ عنه", "icon": "search"},
  {"kind": "hero", "t0": 152.5, "t1": 156.4, "mood": "calm", "main": "فبحثوا… حتى وجدوه", "icon": "location_on", "size": 165},
  {"kind": "caption", "t0": 156.5, "t1": 158.9, "mood": "battle", "main": "وجدوه شهيدًا في أرضِ المعركة", "icon": "star"},
  {"kind": "quote", "t0": 159.0, "t1": 161.7, "mood": "battle", "label": "قال رسول الله صلّى الله عليه وسلّم", "text": "«قتل سبعةً… ثم قتلوه»", "size": 124},
  {"kind": "caption", "t0": 161.8, "t1": 165.1, "mood": "warm", "main": "فحمله النبيُّ ﷺ… وضمّ رأسَه إلى صدره", "icon": "favorite", "size": 88},
  {"kind": "quote", "t0": 165.2, "t1": 170.2, "mood": "warm", "label": "قال رسول الله صلّى الله عليه وسلّم", "text": "«هذا منّي… وأنا منه»", "size": 136},
  {"kind": "caption", "t0": 170.4, "t1": 172.2, "mood": "calm", "main": "وأمر أن يُحفرَ له قبر", "icon": "landscape"},
  {"kind": "caption", "t0": 172.4, "t1": 174.1, "mood": "calm", "main": "فحمله بيده… ووضعه في القبر", "icon": "back_hand", "size": 88},
  {"kind": "caption", "t0": 174.3, "t1": 176.4, "mood": "calm", "main": "وصَلّى عليه… ولم يُغسَّل", "icon": "volunteer_activism"},
  {"kind": "caption", "t0": 176.5, "t1": 177.7, "mood": "calm", "main": "لأنّه شهيد", "icon": "star", "size": 110},
  {"kind": "end", "t0": 177.9, "t1": 181.0, "mood": "end", "main": "وهكذا… عاش مجهولًا\\Nومات شهيدًا", "label": "من صحيح مسلم"},
];

export const sceneAt = (t: number): Scene | null => {
  const b = BEATS.find((s) => t >= s.t0 && t < s.t1);
  return b ?? (t >= DURATION ? BEATS[BEATS.length - 1] : null);
};

export const chapterAt = (t: number): string => {
  let out = CHAPTERS[0].label;
  for (const c of CHAPTERS) if (t >= c.t - 0.15) out = c.label;
  return out;
};
