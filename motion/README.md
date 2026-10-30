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
