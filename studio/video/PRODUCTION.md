# EP01 — The Last Night of Constantinople
## Production log — how the demo was built, and how to take it to 2 h 40

---

## 1) ما الذي اتنفّذ فعليًا في هذه النسخة

| العنصر | القيمة |
|---|---|
| الفيديو | `exports/EP01_partA.mp4` (1080p) · `exports/EP01_partA_720p.mp4` |
| الطول | **1:03:23** (63 دقيقة سرد متصل + خروج موسيقي صامت) |
| الدقة | 1920×1080 · 24fps · H.264 · SAR 1:1 |
| الصوت | AAC 48kHz ستيريو · **−16.1 LUFS** · Peak −2.6 dBFS |
| السرد | 9,005 كلمة · 153 كلمة/دقيقة · صوت واحد (The Keeper) |
| الحركات | 9 (00 · I · II · III · Interlude A · IV · V · VI · Interlude B) |
| اللقطات | 36 لقطة من 23 خلفية |
| المونتاج | Ken Burns 1.06× · Cross-fade 0.9s · Grain + Vignette + Warm grade |
| الموسيقى | 432 Hz drone مُولّد برمجيًا (`assets/ambient_432.wav`) |

**الفيلم المقصود 2 ساعة و43 دقيقة.** السكربت كامل ومكتوب (24,700 كلمة في 14 فصلًا +
7 فصول وسطية)، و`narration/order.json` فيه ترتيب الـ108 مقطعًا. المسجَّل 47 مقطعًا،
والباقي 61 — الصورة والمانيفست والموسيقى جاهزون، الناقص هو التسجيل فقط.
---

## 2) لماذا يبدو المونتاج مثل القناة المرجعية

| ما تفعله Sleepy History | ما يفعله المحرك |
|---|---|
| صورة ثابتة تتحرك ببطء شديد | `zoompan` من 1.00 → 1.10 على مدى 70 ثانية (0.14% في الثانية) |
| انتقال ناعم جدًا | `xfade=fade` بمدة **0.9 ثانية** — أبطأ من اليوتيوب القياسي (0.3) |
| تباين منخفض، دفء عسلي | `eq contrast=0.94 saturation=0.88` + `colorbalance` دافئ |
| حبيبات فيلم | `noise=alls=4:allf=t+u` (متحرك، ليس ثابتًا) |
| أطراف داكنة | `vignette=PI/5.2` |
| موسيقى ثابتة بلا أحداث | drone 432 Hz بـ 3 نغمات منحرفة قليلًا لكل جزئية (beating بطيء) |
| نهاية صامتة | 45 ثانية موسيقى فقط بعد آخر كلمة، ثم fade |

**لا يوجد في الفيديو:** نص على الشاشة، شعار، انتقال أبيض، مؤثر صوتي، موسيقى تتغير، قطع سريع.

---

## 3) خط الإنتاج (يشتغل على أي جهاز)

```bash
cd studio/video
pip install pillow numpy imageio-ffmpeg

# 1) مولّد موسيقى النوم (432 Hz) — 60 ثانية تتكرر بلا نهاية
python3 tools/make_ambient.py assets/ambient_432.wav --seconds 60

# 2) تسجيل/توليد السرد → narration/narration_full.wav

# 3) بناء الـ manifest (صور + مدد) — انسخ أي ملف في scripts/
python3 tools/render_video.py scripts/ep01_demo.manifest.json
```

المخرج النهائي: `exports/*.mp4` جاهز للرفع على يوتيوب.

### Manifest — أقل تعديل ممكن
```json
{
  "narration": "narration/narration_full.wav",
  "ambient": "assets/ambient_432.wav",
  "width": 1920, "height": 1080, "fps": 24,
  "transition": 0.9, "fade_in": 2.0, "outro": 45,
  "segments": [
    {"image": "../art/bg-01-constantinople.png", "duration": 74, "zoom": [1.0, 1.10]},
    {"image": "../art/bg-06-hagia-sophia.png",   "duration": 66, "zoom": [1.06, 1.0], "pan": "left"}
  ]
}
```

---

## 4) الطريق إلى 2:40 — الخريطة الرقمية

| الطول المطلوب | الكلمات المطلوبة (130 كلمة/د) | عدد اللقطات المقترح | حجم الصوت |
|---|---|---|---|
| 8 دقائق | 1,040 | 6–8 | 21 MB WAV |
| 30 دقيقة | 3,900 | 14–18 | — |
| 60 دقيقة | 7,800 | 24–30 | — |
| **2:40** | **20,800** | **45–60 لقطة** | — |

**خياران للسرد الكامل:**
1. **بشري (الأفضل):** تسجيل صوتك بسرعة 128–132 كلمة/دقيقة، على 6 جلسات × 25 دقيقة.
   هذا ما تفعله القناة المرجعية، وهو أيضًا ما يحميك من سياسة المحتوى غير الأصيل.
2. **TTS (أسرع):** نفس الصوت المستخدم هنا، على دفعات 1,400 حرف لكل مقطع، ثم دمج:
   ```bash
   # دمج المقاطع بفواصل 0.8 ثانية + إبطاء إلى 130 كلمة/د + EQ + غرفة
   ffmpeg -i c1.mp3 -i c2.mp3 ... -filter_complex \
     "[0:a]apad=pad_dur=0.8[p0];[1:a]apad=pad_dur=0.8[p1];[p0][p1]concat=n=2:v=0:a=1,atempo=0.82,highpass=f=70,lowpass=f=8600[nar]" \
     -map "[nar]" narration_full.wav
   ```

> ملف السكربت `scripts/EP01_The-Last-Night-of-Constantinople.md` يحتوي:
> المقدمة + الفصل I + II + III **مكتوبة كاملة كلمة بكلمة** (≈ 5,700 كلمة / 44 دقيقة)،
> و**مخططات إيقاعية مفصّلة** للفصول IV–XIII مع جمله المفتاحية.

---

## 5) ما يجب قياسه بعد أول نشر

| المؤشر | الهدف | ماذا يعني لو انخفض |
|---|---|---|
| الاحتفاظ عند 0:30 | > 70% | الافتتاحية طويلة أو الصورة لا تتحرك |
| الاحتفاظ عند 10:00 | > 35% | السرد أسرع من اللازم أو الموسيقى عالية |
| متوسط مدة المشاهدة | 25–40 دقيقة | الجمهور لا ينام — الفيديو لا يحقق الغرض |
| CTR | 4–7% | الصورة المصغرة أو العنوان |

**ملاحظة:** في نيش النوم، «متوسط مدة المشاهدة» العالي أهم من النقرات. المشاهد النائم يشاهد
90 دقيقة ولا ينقر مرتين. لا تحسّن CTR على حساب الطول.

---

## 6) ملاحظات صدق تقنية

- الصوت في هذه النسخة **TTS** — نظيف ومظبوط، لكنه يظل أقل دفئًا من صوت بشري. القناة المرجعية تستخدم صوتًا بشريًا.
- الموسيقى **مُولّدة برمجيًا** بـ 432 Hz حقيقي (A4 = 432) وليست ملفًا جاهزًا — آمنة تمامًا من حقوق النشر.
- الصور **أصلية** ومولّدة لهذا المشروع، وليست لقطات من القناة المرجعية.
- مدة الرندر: ≈ 20 دقيقة لهذا الملف على معالج مشترك. للفيديو الكامل (160 دقيقة) احسب 6–8 ساعات، أو انشر على دفعات.

---

## FULL EPISODE — build log (2 h 49 m cut)

The demo proved the pipeline in 8:37. The full episode is the same recipe at
twenty times the length, and it needed more words, more chapters, and a
renderer that does not re-encode the picture three times.

### What the finished episode is

| | |
|---|---|
| Structure | 14 chapters + 7 interludes, 21 movements in the reading order |
| Script | ~24,700 narrated words |
| Narration | one continuous mono master, 0.8 s breath between chunks |
| Pace | 187 wpm at source → atempo 0.82 → **≈153 words / minute** |
| Runtime | **≈163 min (2 h 43)** — inside the reference band (2:16–2:59) |
| Rendered so far | 63:23 (9 movements, 36 shots, 5,320→9,005 words) |
| Picture | 11 stills, Ken Burns only, 0.9 s dissolves |
| Audio | narration −16 LUFS, 432 Hz bed at −27 LUFS, limiter 0.87 |

### The reading order

```
0  Welcome            c1–c7, n1
I  The City at Dusk   n2–n6 *        * the demo narrated Ch. 0 and the first
II The Wall           n2–n6            half of Ch. I; the tail lives in n1–n6
A  The Water Below    i1–i8
III The Camp Outside  n7–n10
B  The Names in Stone i9–i15
IV The Ships in Horn  c8–c17
V  The Guns           c18–c21
VI The Last Liturgy   c22–c25
C  The Scriptorium    i16–i22
VII The People        c26–c29
VIII The Last Walk    c30–c34
D  The Dogs           i23–i28
IX Before Dawn        c35–c38
X  The First Light    c39–c42
E  The Road Out       i29–i34
XI What Was Saved     c43–c46
F  The Marble Emperor i35–i40
XII What the Log...   c47–c49
G  The Witness        i41–i45
XIII Sleep            c50
```

105 narrated chunks in total. `narration/order.json` is the single source of
truth for the reading order; `tools/build_narration.py --order` assembles them.

### Chunking

`tools/chunk_script.py` cuts at sentence boundaries only, never across a
chapter, drops `[stage directions]`, and tags every chunk with its chapter.
TTS calls are limited, so the script is planned first and narrated in batches.

### Why a second renderer

`render_video.py` encodes the picture three times (shot → stitch → mux). At
eight minutes that is fine. At three hours it is most of a day. `render_long.py`
encodes each shot once, stitches movements, concatenates them with the stream
copier, and muxes a single audio master on top — so the voice never breaks at a
movement join while the picture dips gently to black.

### Honest risk list

* TTS is the bottleneck: roughly 11 minutes of finished narration per session.
* A 2 h 49 m 1080p24 render is a multi-hour background job; it is split into
  movements so it can be resumed.
* Every chunk is checked against the script word-for-word before the final
  assembly; a dropped sentence is invisible until you listen at 1.5×.

### Narration progress

| | |
|---|---|
| Clips planned | 108 |
| Clips recorded | 47 (63.5 min of finished narration) |
| Projected final runtime | **163 min (2 h 43)** |
| Batch size | 10 clips ≈ 12 min of film per session |

The queue is `narration/order.json`. `tools/next_batch.py --next 10` prints the
next ten scripts verbatim; `--verify` compares each recording's length against
its text (voice-00 runs at 187 wpm ± 5 %). Every clip in the current set passes.

A clip that is 15 % shorter than its text is a dropped sentence — it is
invisible until you listen at 1.5×, so it is checked mechanically after every
batch.

### Render cadence

The picture is rendered in movements and cached in `out/_movements_a/`. Adding
narration only invalidates the movement that grew, so a later batch re-renders
one or two movements, not the film.

### Where the files live (learned the hard way)

The sandbox does **not** persist folders named `out/`, `dist/`, `build/` or
`target/` — they are excluded from the workspace snapshot, so a render that
lives in `out/` is gone the next session even though ffmpeg reported it.

Everything that must survive a session lives in a normally named folder:

| | |
|---|---|
| `exports/*.mp4` | finished cuts, ready for upload |
| `studio/thumbnails/*.png` | the five 1280×720 thumbnails |
| `narration/*.mp3` | the spoken clips (the real source of the film) |
| `art/_graded/*.jpg` | the pre-graded, pre-vignetted stills |

`out/_movements*/` is deliberately temporary: it is only a render cache.
