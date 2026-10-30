# figo · motion

مولّد فيديو موشن جرافيك عربي (9:16 / 1080×1920) من ملف صوتي:
تفريغ تلقائي بالكلمة والتوقيت ← تايبوجرافي متزامن ← خلفية متحركة ← MP4 جاهز.

## Pipeline

```
voice.mp3
   │  transcribe.py   (faster-whisper small · int8 · CPU, word timestamps)
   ▼
deliver/transcript.json  ──►  storyboard (ظهور/تلاشي، كروت، هايلايت)
   │
   ▼
build.py  ── mgfx/assgen.py  (نص + أنميشن ASS، تشكيل عربي حقيقي عبر libass)
          └─ mgfx/background.py (numpy: mesh gradient + جزيئات + حلقات + waveform)
   │
   ▼
deliver/final.mp4   (H.264 · 1080×1920 · 30fps · AAC 192k)
```

## تشغيل

```bash
python -m venv ../.venv && ../.venv/bmedia/pip install -r requirements.txt

# 1) نسخة استعراض الستايل (بدون صوت) 15 ثانية
../.venv/bmedia/python build_demo.py          # -> deliver/style_preview.mp4

# 2) من الصوت للفيديو
../.venv/bmedia/python transcribe.py media/voice.mp3 --out deliver/transcript.json
../.venv/bmedia/python build.py --audio media/voice.mp3 --transcript deliver/transcript.json
```

## ملاحظات تقنية

- **تشكيل الحروف العربية**: بيتعمل بـ `libass` (HarfBuzz + FriBidi) مش PIL،
  فالوصل والحركات والأرقام العربية كلها صح. الخطوط: Cairo + Tajawal (SIL OFL).
- **الأداء**: الرندر ~15–25 فريم/ثانية على نواتين، أي دقيقة كلام ≈ 4× وقتها.
- **الصوت**: بيتحاكى زي ما هو مع AAC 192k، والـ waveform محسوب من الـ envelope
  الحقيقي للتسجيل.

## النسخة ٢ — موشن جرافيك حقيقي (`build_v2.py`)

النسخة الأولى كانت «تلوبس» (سطر نص أسفل الشاشة). النسخة الثانية بتعالج كل سطر
منطوق كمشهد تصميمي كامل: نوع حركي + أيقونة + إطار + إضاءة، بمحرّك سين Inherited
بايثون خالص (numpy + Pillow + libass) بدون متصفّح.

```
story2.py            لوحة الإيقاعات (beat sheet): 42 بيت، لكل بيت t0/t1 + المود
   │
   ▼
build_v2.py          مركّب المشاهد: TitleBeat · HeroBeat · QuoteBeat · CaptionBeat
   │                 · IconBeat · CounterBeat · EndBeat  (+ طبقة overlay عامة)
   ├── mgfx/masks.py  شكل الحروف عبر libass → قناع alpha مقصوص (cache على القرص)
   ├── mgfx/stage.py  خلفية إجرائية + paste (scale/rot/blur/glow) + rect + ring
   ├── mgfx/icons.py  Material Symbols Rounded (4,415 أيقونة) + أسماء بديلة
   └── mgfx/ease.py   منحنيات الحركة (out_back / out_cubic / in_out / ramp)
   │
   ▼
deliver/final_v2.mp4
```

```bash
# لقطة واحدة للمراجعة (أسرع بكتير من رندر كامل)
../.venv/bin/python build_v2.py --probe 27      # -> /tmp/probe.png

# الرندر الكامل (~12 دقيقة، 5430 فريم)
../.venv/bin/python build_v2.py --out deliver/final_v2.mp4
```

### قواعد التصميم

- **الطبقات**: خلفية مود-مزاج (calm/warm/pray/battle/dark/end) + بنية علوية
  (فصل الحكاية + خيط ذهبي) + الكتلة النصية + معيار تقدّم أسفل الشاشة.
- **النوع الحركي**: كل كلمة بتدخل بـ `out_back` + blur→0 + rise، بتتابع 0.05–0.14ث،
  ولما الكلمة الأخيرة تخلص بتعمل pulse. السطور الداعمة تدخل ككتلة واحدة
  (أدق للعلامات والحركات).
- **الاقتباسات**: كارت بحدود ذهبية + خط Amiri، والنص سطر/سطرين ككتلة واحدة
  عشان الوصل العربي يفضل سليم.
- **الأيقونات**: دائرتين رقيقة + glyph كبير + دوران بسيط عند الدخول.
- **القطع**: flash خفيف + punch-in 6% في أول 0.5ث من كل بيت.
- **الحبيبات**: `noise + eq + vignette` درجتهم خفيفة في ffmpeg.

### مشاكل عربية محلها

- خطوط المشروع مفيهاش `…` ولا `«»`؛ فبنتحولها لحروف موجودة (`mgfx.masks.sanitize`).
- ffmpeg بيطلع `gray` بمدى محدود (16–235)؛ فالأقنعة بتتفك بـ
  `(a-0.0627)/0.8588` قبل القص، وإلا القص بيطلع غلط.
