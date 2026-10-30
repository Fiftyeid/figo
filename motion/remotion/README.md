# قصّة جليبيب — نسخة Remotion

إعادة بناء الفيديو بمحرّك **Remotion** (React → فيديو): كل جملة منطوقة = مكوّن React
له حركته الخاصة (springs)، والأيقونات والخطوط عربية حقيقية في المتصفّح.

```
src/
├── video/
│   ├── story.ts        لوحة الإيقاعات (٤٢ بيت) — مُولَّدة آليًا من ../../story2.py
│   ├── theme.ts        ألوان + خطوط + مزاجات (moods) + إعدادات السبرينغ
│   ├── icons.ts        خريطة أيقونات Material Symbols (اسم → codepoint)
│   ├── components.tsx  الخلفية، الحبيبات، الفينييت، النوع الحركي، الأيقونات، الشرائط
│   ├── scenes.tsx      مشاهد: Title · Hero · Quote · Caption · Icon · End
│   └── Jalibib.tsx     التركيبة الكاملة (Sequences + صوت + طبقات علويّة)
├── register.tsx        نقطة تسجيل Remotion للـ Studio/CLI
└── ui/App.tsx          واجهة المعاينة + الرندر داخل المتصفّح
```

## ١) معاينة حيّة (بدون أي متصفّح في السيرفر)

```bash
npm install
npm run dev          # → http://localhost:5173
```

الصفحة فيها مشغّل Remotion (Player) + لوحة تحكّم:
- **الدقّة**: 1080×1920 / 720×1280 / 540×960
- **عدد الأجزاء**: كل جزء يُرندَر ويُرفع للسيرفر (مقاومة للانقطاع)
- **لقطات**: أزرار ٢ث · ٣٠ث · ٥٥ث … تحفظ PNG في `out/` للمراجعة
- **ابدأ الرندر**: يُنتج MP4 في `out/final.mp4`

> الرندر يشتغل **في المتصفّح** عبر WebCodecs (`@remotion/web-renderer`)، فمش محتاج
> Chromium على السيرفر. الأجزاء تُدمج بـ ffmpeg على السيرفر مع الصوت الأصلي.
> لو المتصفّح مش بيدعم H.264 تلقائيًا يتحوّل لـ VP9/WebM والدمج يحوّله MP4.

## ٢) رندر على جهازك (Node + Chrome)

```bash
npm run studio     # Remotion Studio (تحرير بصري)
npm run render     # → out/jalibib-remotion.mp4 (1080×1920 · 30fps)
```

## ٣) الأصول

`scripts/copy-assets.mjs` بينسخ الخطوط (`../fonts`) والصوت (`../media/voice.mp3`)
إلى `public/` قبل التشغيل — عشان الريبو يفضل خفيف.

## ٤) الفرق عن نسخة بايثون

| | بايثون (`build_v2.py`) | Remotion |
|---|---|---|
| الرسم | أقنعة alpha + numpy compositor | DOM/CSS + React |
| الحركة | منحنيات يدوية | `spring()` / `interpolate()` |
| التشغيل | ffmpeg pipe | WebCodecs في المتصفّح |
| التعديل | إعادة كتابة كود | HMR + Studio بصري |

الاثنين بيقروا **نفس** لوحة الإيقاعات (`story2.py` → `story.ts`)، فالتوقيتات واحدة.
