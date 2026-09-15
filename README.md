# FIGO — إعادة إنتاج مونتاج Pinterest بـ Remotion

> **الرابط المحلل:** https://www.pinterest.com/pin/986499493410837438/  
> **النمط:** Aesthetic Montage / Soft Cinematic Vertical (9:16) — الأكثر فيروسية على Pinterest 2025-2026

هذا المشروع يعيد إنتاج أسلوب المونتاج الفيروسي في الفيديو الأصلي بشكل برمجي 100% باستخدام **Remotion** (React).

### 🎬 المعاينة المباشرة
المشروع يعمل الآن على:
```
npm run dev → http://localhost:3000
```
في هذه البيئة: **https://3000-i3e7l85ec80u6s256z4sv.e2b.app** (اضغط LIVE PREVIEW)

ثلاث تركيبات جاهزة:
- `PinterestMontage` — 1080×1920 (9:16) المدة تحسب تلقائياً من مجموع الكليبات (~8.3 ثانية)
- `PinterestMontageShort` — نسخة سريعة للاختبار
- `PinterestMontageSquare` — 1080×1080

### 🚀 التشغيل السريع

```bash
npm install
npm run dev        # افتح الاستوديو
# أو للتصدير:
npm run render     # out/pinterest-montage.mp4 (يحتاج Chrome Headless)
```

### 🎨 كيف تغير المحتوى

افتح `src/Root.tsx` وعدّل `clips`:

```ts
{
  src: 'https://.../your-image.jpg', // أو فيديو mp4 عبر <Video> أو <OffthreadVideo>
  label: 'MORNING',
  sublabel: '05:30 AM',
  durationInFrames: 36, // 36 = 1.2 ثانية @30fps
}
```

غيّر العنوان:
```ts
title: "SOFT ERA",
subtitle: "a Pinterest montage"
```

### 📁 بنية المشروع

```
src/
  Root.tsx              # تسجيل التركيبات + البيانات الافتراضية
  PinterestMontage.tsx  # المنطق الرئيسي: تقطيع، إيقاع، progress bar
  components/
    KenBurnsClip.tsx    # زوم بطيء + whip transition + flash
    KineticText.tsx     # نص حركي Pop + Stagger لكل حرف
    FilmGrain.tsx       # تحبيب + light leak
    Vignette.tsx        # تظليل سينمائي + إطار
```

انظر `ANALYSIS.md` للتحليل الكامل خطوة بخطوة.
