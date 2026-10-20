# studio/ — Vellum Logs Thumbnail Engine

محرك توليد الصور المصغرة بهوية «Sleepy History»: خلفية تاريخية هادئة بألوان ترابية + خط Slab Serif
ثقيل بظل ناعم + شارة 432 Hz/No Adverts.

## التشغيل

```bash
cd studio
python3 tools/make_thumbnail.py configs/ep01.json
# أو الكل:
./batch.sh
```

المتطلبات: `pip install pillow` — الخطوط موجودة في `fonts/`.

## الملفات

| المسار | الوصف |
|---|---|
| `tools/make_thumbnail.py` | المحرك (معالجة الخلفية، نص متعدد الأسطر، شارة Pill، هلال الهوية) |
| `configs/*.json` | 5 نماذج إعداد (كل ملف = صورة مصغرة) |
| `art/*.png` | خلفيات 16:9 مولّدة بألوان النيش |
| `out/*.png` | النواتج النهائية 1280×720 |
| `PLAYBOOK.md` | دليل القناة الكامل: الصيغ، السكربت، الوصف، الكلمات المفتاحية، المونتاج |

## الحقول المدعومة في الإعداد

- `background` مسار صورة الخلفية (نسبة 16:9 مُفضّلة).
- `warmth` (0–1) دفء الألوان · `grain` · `vignette` · `blur`.
- `blocks[]`: `text` (يدعم `\n`) · `size` · `y` (0–1) · `x` (0–1 للطرف الأيسر) ·
  `align` (left/center/right) · `weight` (700/900) · `color` · `stroke` · `tracking` ·
  `line_gap` · `max_width` (0–1 من العرض) · `shadow` (0–1).
- `pill`: شارة دائرية بيضاء — `text` · `y` · `size` · `icon` (`wave` أو null).
- `brand`: علامة القناة (هلال + VELLUM LOGS) — `text` · `y` · `size` · `align`.
