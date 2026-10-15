# ليه محافظات مصر اتسمّت بالأسماء دي؟ — فيديو كامل (13:57)

فيديو يوتيوب تعليمي بنفس فكرة وأسلوب فيديو «أسئلة نص الليل» عن أصل أسماء محافظات مصر،
لكن **بسكريبت تعليق صوتي جديد ١٠٠٪** (مكتوب من الصفر ومراجَع على مصادر)، وبصريات أصلية.

| الملف | الوصف |
|---|---|
| `output/egypt_governorates_names.mp4` | الفيديو النهائي — 1920×1080، 25 فريم، 13:57 دقيقة، صوت AAC بمستوى يوتيوب (‎-14 LUFS) |
| `output/thumbnail.jpg` | صورة مصغّرة 1280×720 |
| `output/subtitles_ar.srt` | ترجمة عربية متزامنة (218 سطر) — ارفعها على يوتيوب كـ Subtitles |
| `output/youtube_description_ar.md` | عنوان + وصف + **فصول الفيديو (Chapters)** جاهزة للنسخ |
| `script/script_ar.md` | سكريبت التعليق الصوتي كامل بالتوقيتات |

## محتوى الفيديو
مقدمة (Hook) ← تتر العنوان ← ٢٧ محافظة بالترتيب الجغرافي (القاهرة … سيناء) ← خاتمة ومعلومة أخيرة ← طلب اللايك والاشتراك.
كل محافظة ليها: خريطة بتتنوّر عليها المحافظة + عاصمتها، وكروت متحركة لرحلة الاسم
(مصري قديم ← قبطي ← يوناني ← عربي)، وكروت «الحكاية الشعبية ✗ / الأصل ✓»، وصور تاريخية مرسومة.
فوق الشاشة شارة «رقم المحافظة / ٢٧» وشريط تقدّم من ٢٧ خانة.

## المكوّنات (كلها أصلية أو مفتوحة الترخيص)
- **التعليق الصوتي:** صوت مولّد (TTS) باللهجة المصرية — الصوت اللي اخترته في البداية.
- **الصور المرسومة (9):** مولّدة بالذكاء الاصطناعي خصيصًا للفيديو (`assets/images`).
- **الخرائط:** بيانات Natural Earth (ملكية عامة)، وحدود مصر الجنوبية على خط ٢٢ (حلايب وشلاتين داخل مصر).
- **الخطوط:** Cairo / Lalezar / Tajawal / Amiri — Google Fonts (رخصة OFL).
- **الموسيقى والمؤثرات:** مؤلفة برمجيًا بالكامل (`src/music.py`) — تقاسيم «عود» وإيقاع مقسوم وبادات — بدون أي حقوق ملكية لطرف تالت.

## إعادة البناء
```bash
pip install pillow numpy scipy shapely imageio-ffmpeg   # + libfribidi لتشكيل الحروف العربي
./build.sh
```
عشان تعدّل السكريبت: غيّر `src/script_data.py` (النص) و`src/storyboard.py` (المشاهد والتوقيتات)،
ولازم تولّد التعليق الصوتي من جديد للمقاطع اللي اتغيرت (`assets/audio/clip_XX.opus`).

---
**English summary:** a 13:57 Egyptian-Arabic explainer on the origins of Egypt's 27 governorate names, with a brand-new
voice-over script. Pipeline: TTS narration → pause-aligned timing (`timing.py`) → Pillow/raqm motion-graphics renderer
with maps, etymology chains and Ken-Burns illustrations (`shots.py`, `storyboard.py`, `render.py`) → procedural score + SFX
and loudness-normalised mix (`music.py`) → 2-pass H.264.
