# دليل سريع: اعمل فيديو جديد بنفس ستايل HIKKA في 15 دقيقة

## 1. جهّز الصور

أي صورة معدات **على خلفية بيضاء نقية** تنفع كمدخل:

```
assets_raw/pack_us.png     ← صورة على أبيض
assets_raw/pack_cn.png
```

ثم:

```bash
python3 video/cutout.py            # يفرّغ الخلفية ويكتب assets/pack_us.png (شفاف)
```

الاسكربت بيطبع نسبة تغطية كل صورة — لو رقم صغير جداً (< 3%) يبقى التفريغ فشل
(الصورة مش على أبيض نقي) فاستخدم صورة أنضف.

> نصيحة: لسه مفيش صور؟ استخدم **DVIDS** (Public Domain) أو **Wikimedia Commons**
> (CC BY / CC BY-SA) أو رندرات 3D من Sketchfab بترخيص CC — وسجّل المصدر في وصف الفيديو.

## 2. اكتب السكربت

افتح `video/engine/content.py` وعدّل:

```python
META = {
    "title": "GEAR COMPARED",              # العنوان الكبير
    "subtitle": "USA vs CHINA — SOLDIER",
    "episode": "FIELD LOADOUT STUDY  /  EP. 02",
    "deck": "جملة واحدة تظهر تحت العنوان في المقدمة",
    "disclaimer": "OPEN-SOURCE DATA · ILLUSTRATIVE RENDERS",
}

SIDES = {   # أسماء الجهتين وألوانهما
    "left":  {"code": "USA", "flag": "us", "force": "U.S. ARMY",  "accent": (21, 45, 88)},
    "right": {"code": "CHN", "flag": "cn", "force": "PEOPLE'S LIBERATION ARMY", "accent": (196, 34, 34)},
}
```

ولكل فصل:

```python
{
    "id": "19",                       # ← اسم ملف الصوت: audio/vo/19.mp3
    "kind": "duel",                   # شكل المشهد (الجدول تحت)
    "chapter": "THE PACK",
    "title": "ASSAULT PACK",
    "standfirst": "سطر واحد يشرح فكرة المقارنة",
    "assets": {"left": "pack_us", "right": "pack_cn"},
    "names":  {"left": "MOLLE II", "right": "PLA TYPE 21"},
    "specs":  [("CAPACITY", "60 L", "55 L"),
               ("EMPTY WEIGHT", "2.6 kg", "2.1 kg"),
               ("FRAME", "External", "Internal")],
    "nominal": 12.0,                  # مدة احتياطية لو مفيش صوت
    "narration": "النص الإنجليزي…",
    "narration_ar": "النص العربي…",    # للترجمة (srt)
}
```

## 3. سجّل التعليق الصوتي

ملف واحد لكل فصل:

```
audio/vo/intro.mp3
audio/vo/01.mp3 … audio/vo/19.mp3
```

المحرّك بيقيس مدة كل ملف ويبني التايم لاين عليها — **مش محتاج تظبط أي توقيت**.

## 4. رندر

```bash
python3 video/build.py                 # الفيديو الكامل
python3 video/build.py --only 01,19    # الفصلين دول بس (تجربة سريعة)
python3 video/build.py --poster intro  # صورة بوستر
```

النتيجة:

```
deliverables/hikka_gear_usa_vs_china.mp4
deliverables/hikka_gear_usa_vs_china.en.srt
deliverables/hikka_gear_usa_vs_china.ar.srt
deliverables/poster.png
```

## 5. جدول أنواع المشاهد

| kind | الشكل | الحقول المطلوبة |
|---|---|---|
| `duel` | عنصرين مفرغين متقابلين على أرضية الاستوديو | `assets`, `names`, `specs` |
| `bars` | بارين بيتكوّنوا من الفاصل للخارج + أرقام كبيرة | `bars` + `specs` |
| `swatch` | كروت تمويه مولّدة (OCP / بكسلات) | `names`, `specs` |
| `ammo` | خراطيش بمقياس نسبي + خط قياس | `bullets`, `names` |
| `list` | تشيك ليست 3 بنود لكل جهة | `list`, `names`, `specs` |
| `stat` | رقم ضخم في سداسي شفاف | `stats`, `names`, `specs` |
| `outro` | جدول حكم + الجنديين + خاتمة | `assets`, `specs` |

## 6. تغيير الهوية البصرية كاملة

كل شيء في `video/engine/config.py`:

```python
BG_TOP / BG_HORIZON / BG_BOTTOM   # خلفية الاستوديو
INK / INK_DIM / CHARCOAL         # أحبار النصوص
US_NAVY, CN_RED                  # ألوان الجهتين (أو عدّل SIDES في content.py)
font(weight, size)               # العائلة: bold / mono / reg
```

ولو عايز ألوان جهتين مختلفين (مثلاً مصر × إسرائيل)، غيّر `SIDES` فقط:
اللافتات، الشارات، أشرطة الـbars، والـwash الخلفي كلهم بياخدوا اللون أوتوماتيك.

## 7. لقطات B-Roll (اختياري بس بيفرق جداً)

الفصول 07 و10 و13 و16 مستنية كليب:

```bash
python3 video/broll.py my_clip.mp4 mg_fire     # نزّل الكليب من DVIDS/Commons الأول
python3 video/build.py
```

لو مفيش كليب، الفصل يشتغل استوديو عادي — مافيش أي crash.

## 8. خد بالك

- **الأرقام والمواصفات مسؤوليتك**: المحرّك بيعرض اللي تكتبه. راجع المصادر
  واذكرها في وصف الفيديو (زي الفيديو الأصلي: DVIDS + Wikimedia).
- الصور الحالية **رندرات توضيحية** مولّدة — مكتوب على الشاشة
  `ILLUSTRATIVE RENDERS`. لو استخدمت صور حقيقية، عدّل سطر الحقوق في `META`.
- الإخراج 1080p30 + AAC mono. لتغيير الدقة/الـfps عدّل `render()` في `video/build.py`
  (`w`, `h`, `fps`) — الليّاوت بيتمدد نسبياً لأن كل حاجة محسوبة على شبكة ثابتة.
