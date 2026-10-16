# ليه محافظات مصر اتسمّت بالأسماء دي؟ — فيديو كامل (13:32)

فيديو يوتيوب تعليمي بنفس فكرة وأسلوب فيديو «أسئلة نص الليل» عن أصل أسماء محافظات مصر،
لكن **بسكريبت تعليق صوتي جديد ١٠٠٪** (مكتوب من الصفر ومراجَع على مصادر)، وبصريات أصلية.

| الملف | الوصف |
|---|---|
| `output/egypt_governorates_names.mp4` | الفيديو النهائي — 1920×1080، 25 فريم، 13:32 دقيقة، صوت AAC بمستوى يوتيوب (‎-14 LUFS) |
| `output/thumbnail.jpg` | صورة مصغّرة 1280×720 |
| `output/subtitles_ar.srt` | ترجمة عربية متزامنة (213 سطر) — ارفعها على يوتيوب كـ Subtitles |
| `output/youtube_description_ar.md` | عنوان + وصف + **فصول الفيديو (Chapters)** جاهزة للنسخ |
| `script/script_ar.md` | سكريبت التعليق الصوتي كامل بالتوقيتات |
| `output/shorts_ar.md` | **خطة النشر** (الطويل الأول ولا الشورت + المواعيد) + لكل شورت: عنوان وبديل، وصف، تاجز، هاشتاجات، كومنت مثبّت — حسب معايير vidIQ ومراجَعة أوتوماتيك |
| `output/shorts_covers/` | **٨ أغلفة** 1080×1920 للشورتس (يوتيوب / إنستجرام / تيك توك / فيسبوك) |

## محتوى الفيديو
هوك سريع (٣ معلومات صادمة في أول ١٤ ثانية + سؤال «الأسامي دي جت منين؟») ← تتر العنوان (٠:٢١) ← وعد ولغز مفتوح للآخر
(«محافظتين اتولدوا واتلغوا في ٣ سنين») ← ٢٧ محافظة بالترتيب الجغرافي، من القاهرة (٠:٣٥) لسيناء ← خاتمة بتحل اللغز
← طلب اللايك والاشتراك.
كل محافظة ليها: خريطة بتتنوّر عليها المحافظة + عاصمتها، وكروت متحركة لرحلة الاسم
(مصري قديم ← قبطي ← يوناني ← عربي)، وكروت «الحكاية الشعبية ✗ / الأصل ✓»، وصور تاريخية مرسومة.
فوق الشاشة شارة «رقم المحافظة / ٢٧» وشريط تقدّم من ٢٧ خانة.

## مقاطع Shorts / Reels
٨ مقاطع طولية 1080×1920 (من ٢٩ ثانية لدقيقة وعشر ثواني) لنشر الفيديو على يوتيوب شورتس وإنستجرام ريلز وتيك توك وفيسبوك ريلز.
كل مقطع حكاية محافظة واحدة: **سؤال افتتاحي بصوت الراوي** ← الحكاية من الفيديو الطويل (القطع بيبدأ عند وقفة في الكلام)
← **«شوف الفيديو الكامل»** على الصورة المصغّرة. فوق: عنوان «ليه اسمها …؟»، وفي النص الفيديو 16:9 فوق نسخة مغبّشة منه،
وتحت: ترجمة محروقة متزامنة بالكلمات المهمة بالدهبي، والمنطقتين اللي فوق وتحت فاضيين عشان أزرار التطبيقات.
ترتيب `SHORTS` في `src/shorts.py` هو ترتيب النشر المقترح (ومنه أرقام الملفات).
لكل مقطع **غلاف** (`src/covers.py`): رسمة طولية أصلية بنفس ستايل الفيديو + اسم المحافظة بالدهبي + التويست في كارت ملوّن
زي الصورة المصغّرة للفيديو الطويل، وكل حاجة مهمة جوه القصّة 4:5 و3:4 اللي بتستخدمها شبكات القنوات.
ونفس الغلاف متحط آخر نص ثانية في كل شورت، عشان ينفع يتختار كصورة مصغّرة من تطبيق يوتيوب
حتى لو القناة لسه ماعندهاش رفع صورة مصغّرة للشورتس.
الملفات نفسها على درايف (مش في git عشان حجمها)، واللينكات في `output/shorts_ar.md`.

```bash
cd src
python3 shorts.py plan                # نقط القطع ومدة كل مقطع
python3 shorts.py preview luxor 3 10  # صور معاينة -> build/shorts/
python3 shorts.py all                 # المقاطع -> build/shorts/NN_<id>.mp4  (محتاج build/ من ./build.sh)
python3 shorts.py audio all           # بعد موسيقى جديدة: يغيّر الصوت بس ويسيب الصورة زي ما هي
python3 covers.py                     # الأغلفة -> output/shorts_covers/NN_<id>.jpg
python3 publishing.py                 # خطة النشر + بيانات الرفع + مراجعة معايير vidIQ -> output/shorts_ar.md
```
محافظة جديدة = سطر في `SHORTS` جوه `src/shorts.py` + سؤال افتتاحي بصوت الراوي في `assets/audio/shorts/hook_<id>.opus`.

## المكوّنات (كلها أصلية أو مفتوحة الترخيص)
- **التعليق الصوتي:** صوت مولّد (TTS) باللهجة المصرية — الصوت اللي اخترته في البداية.
- **الصور المرسومة (19):** مولّدة بالذكاء الاصطناعي خصيصًا للفيديو (`assets/images`).
- **الخرائط:** بيانات Natural Earth (ملكية عامة)، وحدود مصر الجنوبية على خط ٢٢ (حلايب وشلاتين داخل مصر).
- **الخطوط:** Cairo / Lalezar / Tajawal / Amiri — Google Fonts (رخصة OFL).
- **الموسيقى:** مؤلفة ومولّدة برمجيًا من الصفر (`src/score.py`) — بدون أي عينات أو حقوق ملكية لطرف تالت.
  الأسلوب المعتمد «وثائقي سينمائي»: بيانو ناعم ووتريات ووتريات غليظة، بتتغيّر كل حوالي دقيقة ونص على حدود المحافظات،
  وبتنزل تحت الصوت أوتوماتيك (ducking). فيه كمان أسلوبين جاهزين: `mystery` (غموض وفضول) و`oriental` (ناي وقانون بدون إيقاع):
  `python3 src/music.py mystery` يبني الصوت بيهم، و`python3 src/music.py audition` يعمل معاينة لأول ٣٧ ثانية بالتلاتة.
- **المؤثرات:** whoosh بين المحافظات، pop للكروت، riser + impact على العنوان (`src/music.py`).

## إعادة البناء
```bash
pip install pillow numpy scipy shapely imageio-ffmpeg   # + libfribidi لتشكيل الحروف العربي
./build.sh
```
عشان تعدّل السكريبت: غيّر `src/script_data.py` (النص) و`src/storyboard.py` (المشاهد والتوقيتات)،
ولازم تولّد التعليق الصوتي من جديد للمقاطع اللي اتغيرت (`assets/audio/clip_XX.opus`).
لو غيّرت المقدمة بس: `ALIGN_TO=../build/<timeline القديم>.json python3 timing.py` بيظبط الوقفة بعد المقدمة (أقل من فريم)
عشان باقي الفيديو يتحرك بعدد فريمات صحيح، فتعيد رندر أول segment بس وتلزقه في الباقي من غير ما ترندر الفيديو كله.
وبعد أي تعديل في المشاهد شغّل `python3 src/check_timing.py` — بيطلّع أي عنصر (كارت/دبوس/عنوان) هيظهر متأخر
بعد ما المشهد يتقطع، فالمشاهد عمره ما هيشوفه.

## سجل التحديثات
- **خطة النشر + الأغلفة:** غلاف طولي لكل شورت (٨ رسومات جديدة)، والغلاف متحط في آخر كل شورت عشان يتختار كصورة مصغّرة.
  وكمان خطة نشر (الطويل الخميس ٦ م وبعده شورت كل يوم ٧ م)، وبيانات رفع لكل فيديو مبنية على معايير vidIQ
  واقتراحات بحث يوتيوب الحقيقية (`src/publishing.py`). ترتيب الشورتس اتغيّر لترتيب النشر.
- **الإصدار ٣:** هوك جديد أقوى — المقدمة اتكتبت من جديد: ٣ معلومات صادمة في أول ١٤ ثانية، العنوان عند ٠:٢١ بدل ٠:٢٧،
  والقاهرة بتبدأ عند ٠:٣٥ بدل ١:٠٠، ولغز مفتوح للآخر. وموسيقى خلفية جديدة بأسلوب وثائقي سينمائي (بيانو ووتريات)
  بدل العود والإيقاع المقسوم (`src/score.py`). الفيديو بقى 13:32، والشورتس الـ٨ اتحدّث صوتها بالموسيقى الجديدة.
- **مقاطع Shorts / Reels:** ٨ مقاطع طولية متقطّعة من الإصدار ٢ (`src/shorts.py`)، بأسئلة افتتاحية ودعوة للفيديو الكامل
  بصوت نفس الراوي، وترجمة محروقة ما بتقسمش الأسماء والسنين والعبارات المترابطة على كارتين.
- **الإصدار ٢:** ١٠ صور مرسومة جديدة للمحافظات اللي كانت خرايط وكروت بس — ميناء القلزم (السويس)،
  لويس التاسع محبوس في المنصورة (الدقهلية)، الشيخ طلحة في القرية (كفر الشيخ)، المساحين العثمانيين بدفاترهم
  (بني سويف + المقدمة)، بحيرة موريس ومعبد سوبك (الفيوم)، الفلاح والتور «سو هاج!» (سوهاج)، قافلة درب الأربعين
  (أسيوط + خلفية الوادي الجديد)، العرب قدام معابد الكرنك (الأقصر)، سوق أسوان القديم، ومناجم الفيروز (سيناء).
  ومعاها إصلاح كروت كانت آخر خانة فيها بتظهر بعد ما المشهد يتقطع (السويس، الفيوم، المنيا، سوهاج، الوادي الجديد،
  الإسماعيلية، طنطا)، ودبابيس خرايط كانت بتظهر لأقل من ثانية.
- **الإصدار ١:** النسخة الأولى (٩ صور مرسومة).

---
**English summary:** a 13:32 Egyptian-Arabic explainer on the origins of Egypt's 27 governorate names, with a brand-new
voice-over script. Pipeline: TTS narration → pause-aligned timing (`timing.py`) → Pillow/raqm motion-graphics renderer
with maps, etymology chains and Ken-Burns illustrations (`shots.py`, `storyboard.py`, `render.py`) → synthesised score
(`score.py`: felt piano, string ensemble, Karplus-Strong plucks, FM bells, ney; three styles) + SFX and a ducked,
loudness-normalised mix (`music.py`) → 2-pass H.264. `check_timing.py` lints the storyboard for elements that would
appear after their shot is cut. v2 adds 10 illustrations (19 total) and fixes several late-appearing card items. v3 rewrites the cold open (title at
0:21, first governorate at 0:35 instead of 1:00, open loop paid off in the outro) and replaces the oud/darbuka bed with
a cinematic piano-and-strings score.
`shorts.py` cuts 8 vertical 1080×1920 Shorts/Reels from the finished build (spoken hook → original narration cut at a
pause → spoken call-to-action over the thumbnail) with burned-in, phrase-aware Arabic captions; the MP4s live on Drive.
`covers.py` builds a 1080×1920 cover per Short (new vertical art + gold name + hook pill, kept inside the 4:5/3:4 grid
crops), which `shorts.py` also appends as the last 0.48 s so it can be picked in YouTube's frame selector; `publishing.py`
writes the release plan and per-video metadata (titles, descriptions, tags, hashtags, pinned comments) and checks it
against vidIQ's published criteria.
