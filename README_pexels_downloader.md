# 📸 Pexels Downloader — سكربت تنزيل ملفات Pexels

سكربت بايثون لتنزيل **الصور والفيديوهات** من [Pexels](https://www.pexels.com/) عبر الـ **API الرسمي المجاني**.

لا يحتاج أي مكتبات خارجية — يعمل بمكتبة Python القياسية فقط (**Python 3.8+**).

## 🔑 الخطوة الأولى: الحصول على مفتاح API

1. سجّل حسابًا مجانًا في <https://www.pexels.com/api/>
2. انسخ مفتاح API من لوحة التحكم.

## 🚀 طريقة الاستخدام

### 1) تمرير المفتاح

عبر متغير البيئة (موصى به):

```bash
export PEXELS_API_KEY="مفتاحك هنا"
```

أو مباشرة بالخيار `--api-key`.

### 2) أمثلة جاهزة

```bash
# تنزيل 50 صورة عن الطبيعة
python3 pexels_downloader.py --query nature --limit 50

# تنزيل كل صور عالم مصغّر (بدون حد — كل النتائج)
python3 pexels_downloader.py -q "miniature world"

# تنزيل كل الفيديوهات عن الجبال
python3 pexels_downloader.py -q mountains --type videos

# تنزيل الصور + الفيديوهات معًا
python3 pexels_downloader.py -q sunset --type all

# من المجموعة المميزة (curated)
python3 pexels_downloader.py --curated --limit 100

# صور أفقية عالية الدقة بلون أزرق
python3 pexels_downloader.py -q ocean --orientation landscape --size large --color blue

# معاينة ما سيُنزّل دون تنزيل فعلي
python3 pexels_downloader.py -q sunset --type all --dry-run
```

## ⚙️ الخيارات المتاحة

| الخيار | الوصف |
|---|---|
| `--api-key` | مفتاح Pexels API (أو متغير البيئة `PEXELS_API_KEY`) |
| `-q, --query` | كلمة البحث |
| `--curated` | التنزيل من المجموعة المميزة بدل البحث |
| `-t, --type` | `photos` أو `videos` أو `all` (افتراضي: `photos`) |
| `--limit` | أقصى عدد لكل نوع (0 = كل النتائج) |
| `--per-page` | نتائج كل صفحة API (الحد الأقصى 80) |
| `--orientation` | `landscape` / `portrait` / `square` |
| `--size` | فلتر حجم Pexels: `large` / `medium` / `small` |
| `--color` | فلتر اللون للصور (اسم لون أو كود hex) |
| `--photo-quality` | `original` (كامل) / `large2x` / `large` / `medium` / `small` / `portrait` / `landscape` / `tiny` |
| `--video-quality` | `any` (أعلى دقة) / `hd` / `sd` |
| `--min-duration` / `--max-duration` | مدة الفيديو بالثواني |
| `-o, --out` | مجلد الإخراج (افتراضي: `pexels_downloads`) |
| `--workers` | عدد التنزيلات المتوازية (افتراضي: 4) |
| `--overwrite` | إعادة تنزيل الملفات الموجودة |
| `--no-index` | عدم إنشاء ملف `index.jsonl` |
| `--dry-run` | عرض ما سيُنزّل دون تنزيل |

## 📁 هيكل المخرجات

```
pexels_downloads/
├── photos/
│   ├── pexels_photo_1234567_4000x6000.jpg
│   └── ...
├── videos/
│   ├── pexels_video_7654321_3840x2160.mp4
│   └── ...
└── index.jsonl          # بيانات وصفية لكل ملف (سطر JSON لكل عنصر)
```

## ✨ الميزات

- **بدون تبعيات** — مكتبة Python القياسية فقط.
- تنزيل متوازٍ مع إمكانية ضبط عدد الخيوط.
- **استكمال تلقائي**: تخطي الملفات الموجودة عند إعادة التشغيل.
- ترقيم صفحات تلقائي حتى آخر نتيجة (أو حتى `--limit`).
- إعادة محاولة ذكية عند الأخطاء المؤقتة واحترام حد الطلبات (429).
- تقارير تقدّم لحظية وملخص نهائي بالأحجام.
- حفظ البيانات الوصفية في `index.jsonl` (المصوّر، الأبعاد، الرابط الأصلي…).

## ⚠️ ملاحظات مهمة

- **حد الطلبات**: النسخة المجانية من الـ API تسمح بـ **200 طلب/ساعة** لجلب القوائم (تنزيل الملفات نفسها من خوادم Pexels غير محسوب ضمنها). بصفحة 80 عنصرًا يمكنك الحصول على حتى 16,000 ملف في الساعة.
- لا توجد طريقة عبر الـ API العام لتنزيل «كل» محتوى الموقع — التنزيل يتم حسب كلمة بحث أو من المجموعة المميزة.
- **الترخيص**: ملفات Pexels مجانية للاستخدام وفق [ترخيص Pexels](https://www.pexels.com/license/) — لا يجوز بيعها كما هي دون تعديل ولا استخدام صور الأشخاص بطريقة توحي بترشيحهم لمنتج.
- للحصول على أفضل جودة اترك `--photo-quality original` (افتراضي) و`--video-quality any`.

## 🧪 الاختبار

يوجد خادم وهمي يحاكي الـ API للاختبار المحلي:

```bash
python3 tests/mock_pexels_server.py 8765 &
export PEXELS_API_BASE=http://127.0.0.1:8765
python3 pexels_downloader.py --api-key TESTKEY --query nature --per-page 2 --type all
```
