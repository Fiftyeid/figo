# FIGO — محرّك فيديو بأسلوب HIKKA (Comparative Visual Explainer)

محرّك إنتاج فيديو كامل بأسلوب قناة **HIKKA** لفيديو *Gear Compared: USA vs CHINA Soldier*:
استوديو افتراضي أبيض/رمادي بشبكة أرضية، عناصر مفرغة (PNG cutouts) بظلال وانعكاسات،
مقارنة سبليت-سكرين بترميز لوني صارم (أزرق/أبيض لأمريكا، أحمر/أصفر للصين)، كبسولات بيانات
داكنة، سرد صوتي يقود التوقيت، وموسيقى تصويرية مولّدة برمجياً.

```
deliverables/           الفيديو النهائي + البوستر (مش داخل git — بيتولّد بأمر واحد)
video/engine/           قلب المحرّك
  config.py             الهوية البصرية: ألوان، خطوط، إيقاعات، easing
  pixels.py             تفريغ الخلفية البيضاء، sprites، نصوص، أعلام، ظلال
  scenes.py             المسرح + 7 تخطيطات مشاهد (duel / bars / swatch / ammo / list / stat / outro)
  art.py                تمويه مولّد برمجياً + مقاطع خرطوش مرسومة بمقياس
  audio.py              الموسيقى التصويرية + الدَكِنغ تحت الصوت
  content.py            << الملف الوحيد اللي تعدّله: 18 قسماً + النصوص + الفويس أوفر
video/build.py          التجميع: قياس الصوت → تايم لاين → رندر ffmpeg
assets/                 الصور المفرغة الجاهزة للرندر
assets_raw/             الصور الأصلية على خلفية بيضاء (input)
audio/vo/               مقاطع التعليق الصوتي (intro.mp3, 01.mp3 … 18.mp3)
```

---

## 1) التشغيل

```bash
pip install pillow numpy scipy matplotlib      # مرة واحدة
python3 video/build.py                          # الفيديو الكامل (1080p30 + صوت)
python3 video/build.py --only 01,05,18          # نسخة سريعة لثلاث حلقات فقط
python3 video/build.py --poster intro           # إطار من الفيديو
python3 video/thumbnail.py --showroom           # الثمبنيل الرئيسي: بانلين + ستنسل + أرضية عاكسة
python3 video/thumbnail.py --light --dark       # نسختان بديلتان (فاتحة/سينمائية)
python3 video/build.py --draft                  # ~540p للتجربة السريعة
```

مخرجات: `deliverables/hikka_gear_usa_vs_china.mp4` (+ `deliverables/poster.png`).

`ffmpeg` بيتم جلبه تلقائياً من `tools/node_modules/@ffmpeg-installer` (ثنائي static لـ linux-x64).
لو عندك `ffmpeg` على النظام، المحرّك بيستخدمه؛ أو حدّده بـ `FFMPEG_BIN=/path/to/ffmpeg`.

## 2) الإيقاع (v2 — نفس أرقام الريفيو)

| البند | قبل | بعد |
|---|---|---|
| بداية الفويس أوفر في المقدمة | `1.3s` صمت | **`0.2s`** + مؤثر دخول (impact) |
| صمت بين الفصول | `1.05 + 1.45 = 2.5s` | **`0.35 + 0.45 = 0.8s`** |
| مدة الفيلم | `5:14` | **`4:35`** |
| كادر المقدمة | ثابت 20 ثانية | زوم `5%` + كل جندي يبرز عند جملته + عدّاد الأرضية |
| الفصل | ثابت بعد 1.35s | زوم `3.5%` على مدار الفصل + كبسولات عند `1.5 / 4.0 / 6.5s` |
| المؤثرات | لا شيء | tick / whoosh / impact مولّدة + ducking |

## 3) لقطات الـ B-Roll (بقت شغالة فعلاً)

الفصول `07, 08, 10, 13, 16` بتفتح بلقطة ميدانية بملء الشاشة (3–3.4s) قبل ما ترجع
للاستوديو. المحرّك بيقبل مصدرين، والأولوية للفيديو الحقيقي:

| المصدر | المسار | الشكل |
|---|---|---|
| فيديو حقيقي | `broll/<name>.mp4` ← ثم `python3 video/broll.py` | لقطة متحركة 1080p30 |
| لوحة ثابتة | `assets/broll/<name>.jpg` | حركة 2.5D (Ken Burns) + حبيبات فيلم |

**الوضع الحالي في المشروع:** 5 لوحات ثابتة مولّدة بأسلوب تصوير ميداني
(`nvg_field`, `optic_range`, `mg_fire`, `ration_heat`, `drone_launch`)، مع
حركة كاميرا 2.5D + grade سينمائي + grain + fade in/out، ومكتوب عليها بوضوح
`ILLUSTRATIVE RECONSTRUCTION · NOT ARCHIVE FOOTAGE`.

**لو عايز أرشيف حقيقي (DVIDS / Wikimedia):** نزّل الكليب عندك وشغّل

```bash
python3 video/broll.py my_clip.mp4 mg_fire    # + nvg_field / optic_range / ration_heat / drone_launch
python3 video/build.py
```

الفيديو بياخد أولوية تلقائياً على اللوحة الثابتة، وبس تحرّك سطر الحقوق في
`content.py` → `broll.credit` لاسم الأرشيف والرخصة.

> ليه مش أرشيف حقيقي من الأول؟ بيئة التنفيذ بتسمح بالوصول لـ GitHub/npm/pypi بس،
> وDVIDS وWikimedia محجوبين (`HTTP 000`)، فمفيش طريقة تنزيل الكليبات من هنا.

## 4) إزاي التوقيت يشتغل (الميزة الأهم)

كل قسم بيقعد على الشاشة **بمدة الفويس أوفر بتاعه بالظبط**:

```
duration(section) = 1.05 s  (دخول المشهد + العنوان)
                  + مدة ملف audio/vo/<id>.mp3
                  + 1.45 s  (مساحة تنفّس قبل القطع)
```

يعني لو غيّرت التعليق الصوتي، الفيديو بيتظبط لوحده — مفيش مونتاج يدوي.
لو مفيش ملف صوت للقسم، المحرّك بيستخدم المدة `nominal` المكتوبة في `content.py`.

## 5) إضافة قسم جديد (30 ثانية شغل)

1. حُط صورتين مفرغتين في `assets/` بنفس أسماء الـ `assets` في القسم.
2. ضيف dict في `video/engine/content.py`:

```python
{
    "id": "19", "kind": "duel",            # duel | bars | swatch | ammo | list | stat | outro
    "chapter": "THE PACK", "title": "ASSAULT PACK",
    "standfirst": "One sentence that frames the comparison.",
    "assets": {"left": "pack_us", "right": "pack_cn"},
    "names":  {"left": "MOLLE II", "right": "PLA TYPE 21"},
    "specs":  [("CAPACITY", "60 L", "55 L"),
               ("EMPTY WEIGHT", "2.6 kg", "2.1 kg"),
               ("FRAME", "External", "Internal")],
    "nominal": 12.0,
    "narration": "What the voiceover says…",
}
```

3. ولّد الصوت: `audio/vo/19.mp3` → التوقيت بيتحدّث أوتوماتيك.

### أنواع المشاهد
| kind | الشكل | يحتاج |
|---|---|---|
| `duel` | عنصرين مفرغين في مواجهة على أرضية الاستوديو | `assets` |
| `bars` | بارين بيتكوّنوا من الفاصل للخارج بأرقام كبيرة | `bars` |
| `swatch` | كروت تمويه مولّدة برمجياً (بلوكات OCP / بكسلات Xingkong) | — |
| `ammo` | خراطيش مرسومة بمقياس نسبي + خط قياس | `bullets` |
| `list` | تشيك ليست لكل جهة | `list` |
| `stat` | رقم ضخم في سداسي شفاف | `stats` |
| `outro` | جدول حكم + جنديين على الجانبين | `assets` |

## 6) خط أنابيب الصور (Images → Cutouts)

الصور بتتولّد/بتتجاب على **خلفية بيضاء نقية**، وبعدين:

```python
from engine.pixels import prepare_cutouts
prepare_cutouts("assets_raw", "assets")     # تفريغ تلقائي + تنظيف الحواف
```

التفريغ بيشتغل على مبدأ *min-channel matting* (أي بكسل أبيض محايد = شفاف)،
مع إعادة تعبئة الثقوب الداخلية (مش هنخلي الزناد يبقى شفاف)، وإزالة التلوث الأبيض
من الحواف (un-mix)، وظل أرضي حقيقي مولّد من قناة الشفافية نفسها.

> ملاحظة قانونية/إنتاجية: الصور الحالية **رندرات توضيحية** مولّدة، مش صور معدات حقيقية،
> ومكتوب على الشاشة `OPEN-SOURCE DATA · ILLUSTRATIVE RENDERS`. لو حابب تستخدم صور
> حقيقية، استخدم DVIDS (Public Domain) و Wikimedia Commons (CC BY / CC BY-SA) وحدّث
> سطر الحقوق في `content.META["disclaimer"]` + وصف الفيديو.

## 7) الصوت

* **الفويس أوفر:** ملف واحد لكل قسم في `audio/vo/` (mp3 أو wav). المحرّك بيوحّد اللودنس
  ويخفّض الموسيقى تحته (ducking بـ side-chain).
* **الموسيقى:** مولّدة بالكامل بـ numpy في `engine/audio.py` — درون ماينور هادي + نبضة ساب
  + طبقة هواء، بدون أي ملفات خارجية أو حقوق. تقدر تغيّر `bpm` و`root` من `make_bed`.

## 8) تفاصيل الستايل المطبّقة

- خلفية سيكلوراما متدرجة + شبكة أرضية بمنظور + توهج علوي + vignette خفيف.
- كل عنصر بيقف على خط أرضية واحد، مع **ظل تلامس** + **انعكاس**، وحركة دخول
  (slide + fade + lift) بـ easing أسّي.
- شارة علم دائرية + كود الدولة في كل ربع، فاصل رأسي في المنتصف، شريط تقدم علوي.
- كبسولات داكنة (dark rounded pills) بخط أحادي المسافة للأرقام التقنية، وشريط لوني
  صغير على حرف كل كبسولة بلون الجهة.
- تايبوجرافي: Sans عريض + Tracking واسع للعناوين والأكواد (DejaVu Sans Bold / Mono).

## 9) الأداء

| مرحلة | التكلفة |
|---|---|
| تجميع إطار 1080p | 55–60 ms (زوم الكاميرا + الكبسولات المتدرجة) |
| فيديو 4:35 | ≈ 8 دقائق رندر |
| ذاكرة | أقل من 1 GB |

الإطارات بتتبعت لـ ffmpeg عبر pipe (rawvideo) — مفيش ملفات PNG وسيطة، فمفيش استهلاك ديسك.
