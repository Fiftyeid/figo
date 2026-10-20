# Vellum Logs — Content Studio

مختبر إنتاج قناة **Vellum Logs** — وثائقيات تاريخية هادئة للنوم (نموذج: Sleepy History Channel).

## ابدأ من هنا

| الملف | الوصف |
|---|---|
| **[`studio/video/index.html`](studio/video/index.html)** | **الحلقة الأولى مُنتَجة** — 1080p · 8:37 · يمكن مشاهدتها وتنزيلها. |
| [`studio/index.html`](studio/index.html) | نظام المحتوى الكامل (تشريح النموذج، 5 صيغ، عناوين، وصف، مونتاج، خطة 90 يومًا). |
| [`studio/video/scripts/EP01_publish.md`](studio/video/scripts/EP01_publish.md) | حزمة النشر: عنوان + وصف + فصول + وسوم + Shorts. |
| [`studio/video/scripts/EP01_The-Last-Night-of-Constantinople.md`](studio/video/scripts/EP01_The-Last-Night-of-Constantinople.md) | السكربت الكامل + خطة 13 فصلًا حتى 2:40. |
| [`studio/video/PRODUCTION.md`](studio/video/PRODUCTION.md) | خط الإنتاج وإعادة البناء وطريق الوصول إلى 2:40. |
| [`studio/thumbnails/`](studio/thumbnails/) | 5 صور مصغرة جاهزة 1280×720. |
| [`research/index.html`](research/index.html) | تحليل منافسة نيش التاريخ السينمائي (14 قناة). |

## تشغيل المعاينة محليًا

```bash
python3 serve.py 8000 .        # سيرفر يدعم Range (تشغيل/تقديم الفيديو)
# ثم افتح:
#   http://localhost:8000/studio/video/index.html
#   http://localhost:8000/studio/index.html
```

## إعادة إنتاج الفيديو

```bash
cd studio/video
pip install pillow numpy imageio-ffmpeg

python3 tools/make_ambient.py assets/ambient_432.wav --seconds 60
python3 tools/render_video.py scripts/ep01_demo.manifest.json
```

المخرج: `studio/video/exports/EP01_partA.mp4`

## إعادة توليد الصور المصغرة

```bash
cd studio
python3 tools/make_thumbnail.py configs/ep01.json
./batch.sh          # كل النماذج
```

## هوية بصرية

- خلفيات تاريخية بألوان عسلية/رملية هادئة، تباين منخفض، ضباب وحبيبات فيلم.
- خط **Roboto Slab Black** بحدّ أسود وظل ناعم + **Inter** للشارات.
- شارة بيضاء دائرية: `432 Hz` أو `NO ADVERTS`.
- علامة القناة: هلال + `VELLUM LOGS`.
- في الفيديو: Ken Burns 0.14%/ثانية · Cross-fade 0.9s · موسيقى 432 Hz ثابتة · نهاية صامتة 45s.

## ملاحظات

- الأرقام في `research/` و`studio/` مسحوبة علنًا بتاريخ **19 أكتوبر 2026** من Social Blade وصفحات يوتيوب.
- كل الصور والموسيقى **أصلية** ومولّدة لهذا المشروع، وليست مأخوذة من القناة المرجعية.
- الخطوط: Roboto Slab (Apache 2.0) و Inter (SIL OFL).
- الملفات الصوتية الكبيرة (`narration_full.wav`، `ambient_432.wav`) لا تُحفظ في المستودع — تُعاد بناؤها بالأوامر أعلاه.
