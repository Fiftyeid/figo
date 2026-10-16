# -*- coding: utf-8 -*-
"""
Vertical Shorts / Reels (1080x1920) cut from the long video.

Each short:  spoken hook question (new TTS clip, same narrator voice)
          -> the governorate's story, cut from the long video at a sentence pause
          -> spoken call-to-action over the long video's thumbnail
          -> a short dissolve into the Short's own cover (output/shorts_covers, from covers.py), held for
             a few frames, so it can be picked as the thumbnail in the YouTube frame selector.
Layout: question title on top, the 16:9 video in the middle over a blurred copy of itself,
burned-in Arabic captions (key words in gold) under it, all clear of the Shorts/Reels UI zones
(top bar, bottom title area, right-hand buttons).  Music/SFX/ducking/loudness = same chain as music.py.

  python3 shorts.py plan                      -> cut points, silence check, durations
  python3 shorts.py preview <id> t1 t2 ...    -> build/shorts/prev_<id>_<t>.jpg
  python3 shorts.py <id> [<id> ...] | all     -> build/shorts/NN_<id>.mp4
  python3 shorts.py audio [<id> ...|all]      -> new soundtrack only (after a new score), picture kept
Needs build/: narration.wav, music.wav, sfx.wav, timeline.json, video_noaudio.mp4 (from build.sh)
and the covers (python3 covers.py; generated on the fly if missing).
"""
import os, re, sys, json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.io import wavfile
import imageio_ffmpeg

from common import (ROOT, ASSETS, BUILD, FPS, GOLD, WHITE, INK, TEAL,
                    font, text_image, wrap_lines, chip, rounded_rect, glow, grade_image,
                    ease_out_cubic, ease_out_back, clamp)

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
VW, VH = 1080, 1920
FW, FH = 1080, 608           # the 16:9 window
FY = 640                     # its top edge
CAP_Y = 1415                 # caption block centre (UI-safe: under the video, above the Shorts title zone)
OUT = os.path.join(BUILD, "shorts")
AUD = os.path.join(ASSETS, "audio", "shorts")
IMG = os.path.join(ASSETS, "images")
VIDEO = os.path.join(BUILD, "video_noaudio.mp4")
THUMB = os.path.join(ROOT, "output", "thumbnail.jpg")
COVERS = os.path.join(ROOT, "output", "shorts_covers")
COVER_FADE, COVER_HOLD = 4, 8   # frames: dissolve from the CTA into the cover, then hold it (silent tail)
SERIES = "أصل أسماء محافظات مصر"

# id, timeline section, title lines, hook still, phrase where the story cut starts (None = section start),
# hook text (= the TTS clip assets/audio/shorts/hook_<id>.opus), caption key words shown in gold
# The list order is the recommended posting order -> output numbering NN_<id> (see output/shorts_ar.md).
SHORTS = [
    dict(id="cairo", sec="cairo", l1="ليه اسمها", name="القاهرة", img="intro_mars_desert",
         cut="سنة تسعمية تسعة وستين",
         hook="تعرف إن فيه حكاية بتقول، إن القاهرة اتسمّت على اسم كوكب؟",
         keys="القاهرة للقاهرة القاهر المريخ كوكب المنصورية"),
    dict(id="benisuef", sec="benisuef", l1="ليه اسمها", name="بني سويف", img="ottoman_ledger",
         cut="لو سألت أهلها",
         hook="تعرف إن اسم بني سويف، ممكن يكون جاي من غلطة في دفتر؟",
         keys="بني سويف السيوف منفسويه غلطة دفتر"),
    dict(id="faiyum", sec="faiyum", l1="ليه اسمها", name="الفيوم", img="faiyum_moeris",
         cut="المحافظة اللي اسمها",
         hook="ليه الفيوم اسمها الفيوم؟",
         keys="الفيوم فيوم البحر با يم سوبك التماسيح"),
    dict(id="redsea", sec="redsea", l1="ليه اسمه", name="البحر الأحمر", img="suez_qulzum",
         cut="فيه أكتر من رأي",
         hook="البحر الأحمر لونه أزرق.. طب ليه اسمه الأحمر؟",
         keys="الأحمر أزرق الغردقة الغردق الجنوب"),
    dict(id="luxor", sec="luxor", l1="ليه اسمها", name="الأقصر", img="luxor_karnak",
         cut="دي كانت واست",
         hook="ليه الأقصر اسمها الأقصر؟",
         keys="الأقصر القصور قصور واست طيبة"),
    dict(id="giza", sec="giza", l1="ليه اسمها", name="الجيزة", img="giza_pyramids",
         cut="بعد ما عمرو بن العاص",
         hook="ليه الجيزة اسمها الجيزة؟",
         keys="الجيزة جاز الناحية عدى عدّى الأهرامات"),
    dict(id="sohag", sec="sohag", l1="ليه اسمها", name="سوهاج", img="sohag_bull",
         cut=None,
         hook="حكاية سو هاج دي.. حقيقة ولا نكتة؟",
         keys="سوهاج سو هاج نكتة جرجا"),
    dict(id="dakahlia", sec="dakahlia", l1="ليه اسمها", name="الدقهلية", img="mansoura_1250",
         cut="ودي فيها مفاجأة",
         hook="ليه الدقهلية اسمها الدقهلية؟",
         keys="الدقهلية دقهلة المنصورة مفاجأة"),
]
CTA = "وعشان تعرف حكاية اسم كل محافظة في مصر، شوف الفيديو الكامل على القناة."
CTA_KEYS = "الفيديو الكامل"

HOP = 0.01


# ------------------------------------------------------------------ audio helpers
def load_mono(path, t0=None, dur=None):
    cmd = [FF, "-v", "error"]
    if t0 is not None:
        cmd += ["-ss", f"{t0:.4f}"]
    if dur is not None:
        cmd += ["-t", f"{dur:.4f}"]
    cmd += ["-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).copy()
    if dur is not None:
        n = int(round(dur * SR))
        x = np.concatenate([x, np.zeros(max(0, n - len(x)), np.float32)])[:n]
    return x


def load_stereo(path, t0, dur):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{t0:.4f}", "-t", f"{dur:.4f}", "-i", path,
                          "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    n = int(round(dur * SR))
    if len(x) < n:
        x = np.vstack([x, np.zeros((n - len(x), 2), np.float32)])
    return x[:n]


def env_db(x):
    h, w = int(HOP * SR), int(0.02 * SR)
    n = max(1, (len(x) - w) // h + 1)
    e = np.array([np.sqrt(np.mean(x[i * h:i * h + w] ** 2) + 1e-12) for i in range(n)])
    return 20 * np.log10(e + 1e-9)


def trim_clip(x, thr=-42.0):
    db = env_db(x)
    on = np.where(db > thr)[0]
    a = max(0, int(on[0] * HOP * SR) - int(0.03 * SR))
    b = min(len(x), int(on[-1] * HOP * SR) + int(0.02 * SR) + int(0.07 * SR))
    return x[a:b]


def floor_f(t):
    return math.floor(t * FPS + 1e-6) / FPS


def ceil_f(t):
    return math.ceil(t * FPS - 1e-6) / FPS


# ------------------------------------------------------------------ plan
_TL = None


def timeline():
    global _TL
    if _TL is None:
        _TL = json.load(open(os.path.join(BUILD, "timeline.json"), encoding="utf-8"))
    return _TL


def section(sid):
    return next(s for s in timeline()["sections"] if s["id"] == sid)


def char_time(sec, c):
    cm = np.array(sec["cmap"], dtype=float)
    return float(np.interp(c, cm[:, 0], cm[:, 1]))


def find_onset(t_guess, back=0.9, fwd=0.35, thr=-40.0):
    """Speech onset at a sentence pause near t_guess (end of the closest silent run)."""
    t0 = t_guess - back
    db = env_db(load_mono(os.path.join(BUILD, "narration.wav"), t0, back + fwd))
    sil = db < thr
    runs, k = [], 0
    while k < len(sil):
        if sil[k]:
            j = k
            while j < len(sil) and sil[j]:
                j += 1
            runs.append((k, j))
            k = j
        else:
            k += 1
    kg = back / HOP
    runs = [r for r in runs if (r[1] - r[0]) * HOP >= 0.12] or runs   # real pauses, not dips inside words
    if not runs:
        return t_guess, 0.0
    # the pause containing the guess, else the nearest one (longer wins ties)
    a, b = min(runs, key=lambda r: (max(r[0] - kg, kg - r[1], 0), -(r[1] - r[0])))
    return t0 + b * HOP, (b - a) * HOP


def make_plan(sp):
    sec = section(sp["sec"])
    text = sec["text"]
    c0 = 0 if sp["cut"] is None else text.index(sp["cut"])
    guess = sec["start"] if c0 == 0 else char_time(sec, c0)
    onset, sil = find_onset(guess)
    cut_t = floor_f(onset - 0.06)
    end_t = sec["end"] + 0.25
    n_story = int(round((end_t - cut_t) * FPS))
    hook = trim_clip(load_mono(os.path.join(AUD, f"hook_{sp['id']}.opus")))
    cta = trim_clip(load_mono(os.path.join(AUD, "cta.opus")))
    t_hook = 0.08
    th = ceil_f(t_hook + len(hook) / SR + 0.38)
    ls = n_story / FPS
    t_end_story = th + ls
    t_cta = t_end_story + 0.45
    total = ceil_f(t_cta + len(cta) / SR + 1.1)
    # first frame of the section that is free of the crossfade from the previous section
    vis_min = sec["start"] - 0.25 + 0.36
    n = int(round(total * FPS))
    n_out = n + COVER_FADE + COVER_HOLD
    return dict(sec=sec, c0=c0, cut_t=cut_t, onset=onset, sil=sil, n_story=n_story, ls=ls,
                hook=hook, cta=cta, t_hook=t_hook, th=th, t_end_story=t_end_story, t_cta=t_cta,
                T=total, n=n, n_out=n_out, T_out=n_out / FPS, vis_min=vis_min)


# ------------------------------------------------------------------ audio build (same chain as music.py)
def build_audio(sp, P, out):
    import music as M
    n = int(round(P["T_out"] * SR))          # T + the silent cover frames
    narr = np.zeros(n, np.float32)

    def put(buf, x, t, g=1.0):
        i = int(round(t * SR))
        L = min(len(x), len(buf) - i)
        buf[i:i + L] += x[:L] * g

    put(narr, P["hook"], P["t_hook"])
    put(narr, load_mono(os.path.join(BUILD, "narration.wav"), P["cut_t"], P["ls"]), P["th"])
    put(narr, P["cta"], P["t_cta"])

    mus = load_stereo(os.path.join(BUILD, "music.wav"), P["cut_t"] - P["th"], P["T_out"])
    tt = np.arange(n) / SR
    mus *= (np.clip(tt / 0.35, 0, 1) * np.clip((P["T"] - tt) / 1.6, 0, 1))[:, None].astype(np.float32)

    sfx = np.zeros((n, 2), np.float32)
    seg = load_stereo(os.path.join(BUILD, "sfx.wav"), P["cut_t"], P["ls"])
    i = int(round(P["th"] * SR))
    sfx[i:i + len(seg)] += seg[:n - i]
    W_ = M.whoosh()
    i = int(round((P["th"] - 0.32) * SR))
    pan = np.linspace(0.2, 0.8, len(W_))
    sfx[i:i + len(W_), 0] += W_ * (1 - pan) * 0.5
    sfx[i:i + len(W_), 1] += W_ * pan * 0.5
    I_ = M.impact()
    for t, g in ((0.0, 0.42), (P["t_end_story"] + 0.05, 0.35)):
        i = int(round(t * SR))
        L = min(len(I_), n - i)
        sfx[i:i + L] += I_[:L, None] * g

    tmp = [os.path.join(OUT, f"_{sp['id']}_{k}.wav") for k in ("n", "m", "s")]
    wavfile.write(tmp[0], SR, narr)
    wavfile.write(tmp[1], SR, mus)
    wavfile.write(tmp[2], SR, sfx)
    flt = (
        "[0:a]aresample=48000,pan=stereo|c0=c0|c1=c0,highpass=f=70,"
        "acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2,asplit=2[v][vsc];"
        "[1:a]volume=0.55[m];"
        "[m][vsc]sidechaincompress=threshold=0.03:ratio=8:attack=40:release=450:makeup=1[md];"
        "[2:a]volume=0.9[s];"
        "[v][md][s]amix=inputs=3:duration=first:normalize=0,"
        "loudnorm=I=-14:TP=-1.5:LRA=11[out]"
    )
    subprocess.run([FF, "-y", "-v", "error", "-i", tmp[0], "-i", tmp[1], "-i", tmp[2],
                    "-filter_complex", flt, "-map", "[out]", "-ar", "48000", "-c:a", "aac", "-b:a", "160k", out],
                   check=True)
    for p in tmp:
        os.remove(p)


# ------------------------------------------------------------------ captions
DIAC = re.compile("[\u064B-\u0652\u0670\u0640]")
STRONG = re.compile(r"[.…؟?!:]$")


def norm(w):
    return re.sub(r"[^\w]", "", DIAC.sub("", w))


def is_key(w, keys):
    for part in w.split(WJ):
        n = norm(part)
        if n and (n in keys or (n[0] in "وفبل" and n[1:] in keys)):
            return True
    return False


def clean(w):
    w = w.replace("…", "")
    return re.sub(r"[،,.:]+$", "", w)


FUNC = set("على في من زي اللي إن ان عن مع لحد بين يعني أو او بس لما عشان ما لا يا كان كانت هو هي دي ده "
           "اللى وفي ومن وعلى بعد قبل لو عند طول سنة حد".split())


def short(w):
    """A single short word (a glued multi-word phrase is long enough to stand alone)."""
    return len(norm(w[2])) < 9


def chunk(words, max_chars=20, max_words=4):
    """words: list of (start_char, end_char, word) -> caption chunks.
    Phrases are cut at punctuation, then split into even pieces; a piece never ends on a
    function word (it moves to the next piece), and lone short words are glued on."""
    phrases, cur = [], []
    for w in words:
        cur.append(w)
        if STRONG.search(w[2]) or w[2].endswith("،"):
            phrases.append(cur)
            cur = []
    if cur:
        phrases.append(cur)
    out = []
    for ph in phrases:
        lens = [len(norm(w[2])) + 1 for w in ph]
        L = sum(lens)
        k = max(1, math.ceil(len(ph) / max_words), math.ceil(L / (max_chars + 1)))
        if L <= max_chars + 3 and len(ph) <= max_words + 1:
            k = 1                                                    # short phrase: keep whole
        k = min(k, len(ph))
        cum = np.cumsum(lens)
        cuts = []
        for j in range(1, k):
            b0 = int(np.argmin(np.abs(cum[:-1] - j * L / k)))      # break after word b0
            b = b0
            while b > 0 and norm(ph[b][2]) in FUNC:
                b -= 1
            lo = cuts[-1] + 1 if cuts else 0
            if norm(ph[b][2]) in FUNC or (b - lo < 1 and short(ph[b])):   # would strand a word: go forward
                b = b0
                while b < len(ph) - 2 and norm(ph[b][2]) in FUNC:
                    b += 1
                if b == lo and short(ph[b]) and b + 1 < len(ph) - 1 and norm(ph[b + 1][2]) not in FUNC:
                    b += 1                                           # take the next word along
            if (not cuts or b > cuts[-1]) and b < len(ph) - 1 and norm(ph[b][2]) not in FUNC:
                cuts.append(b)
        prev = 0
        for b in cuts + [len(ph) - 1]:
            out.append(ph[prev:b + 1])
            prev = b + 1
    merged = []
    for c in out:
        if merged and len(c) == 1:
            prev = merged[-1]
            last = prev[-1][2]
            joined = sum(len(norm(w[2])) + 1 for w in prev) + len(norm(c[0][2]))
            if not STRONG.search(last) and not last.endswith("،") and joined <= max_chars + 10:
                merged[-1] = prev + c
                continue
        merged.append(c)
    return merged


WJ = "\u2060"   # word joiner: glued phrases are never split across captions (same string length)
GLUE = ["عمرو بن العاص", "ملك فرنسا", "لويس التاسع", "السلطان الكامل", "الكامل الأيوبي", "المعز لدين الله",
        "جوهر الصقلي", "محمد رمزي", "بحيرة قارون", "بحيرة موريس", "سيدنا يوسف", "الإله سوبك", "مديرية جرجا",
        "بني سويف", "بني السيوف", "البحر الأحمر", "حصن بابليون", "قاهرة المعز", "با يم", "سو هاج",
        "أم مية باب", "مدينة التماسيح", "كوكب المريخ", "الفيديو الكامل", "عصر المماليك",
        "تسعمية تسعة وستين", "تسعمية تلاتة وسبعين", "ستمية واحد وأربعين", "ألف تسعمية ستين",
        "ألف ميتين تسعتاشر", "تلات تلاف", "تلاتين سنة",
        # noun + adjective / tight phrases that read badly when split across two captions
        "الخليفة الفاطمي", "عاصمة جديدة", "العمال يبدأوا الحفر", "اللحظة دي", "قبيلة عربية",
        "المساحين العثمانيين", "كلمة سوهاج", "الشاعر اليوناني هوميروس", "الحدود اتغيرت", "اتهزم واتأسر",
        "نوع من الطحالب", "مواسم معينة", "نبات صحراوي شوكي", "الحكاية الشعبية", "للبر الغربي",
        "نفس جذر الفعل", "أشهر آثار في الدنيا"]


def glue(text):
    for g in GLUE:
        text = text.replace(g, g.replace(" ", WJ))
    return text


def words_of(text, c0=0):
    text = glue(text)
    return [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", text) if m.start() >= c0]


def spread(text, t0, dur):
    """Chunks for a TTS clip without alignment: time proportional to characters."""
    ws = words_of(text)
    cs = chunk(ws)
    tot = sum(len(norm(w[2])) + 1 for w in ws)
    res, acc = [], 0
    for c in cs:
        L = sum(len(norm(w[2])) + 1 for w in c)
        res.append([t0 + dur * acc / tot, t0 + dur * (acc + L) / tot, [clean(w[2]) for w in c]])
        acc += L
    return res


def make_captions(sp, P):
    keys = set(norm(k) for k in sp["keys"].split()) | set(norm(k) for k in sp["name"].split())
    caps = []
    for c in spread(sp["hook"], P["t_hook"], len(P["hook"]) / SR):
        caps.append(c + [keys])
    sec = P["sec"]
    cs = chunk(words_of(sec["text"], P["c0"]))
    st = []
    for c in cs:
        a = P["th"] + char_time(sec, c[0][0]) - P["cut_t"] - 0.04
        z = P["th"] + char_time(sec, c[-1][1] - 1) - P["cut_t"] + 0.40
        st.append([a, z, [clean(w[2]) for w in c], keys])
    for k in range(len(st)):
        nxt = st[k + 1][0] if k + 1 < len(st) else P["t_end_story"]
        st[k][1] = min(st[k][1], nxt)
        st[k][0] = max(st[k][0], P["th"])
    # a caption shorter than 0.45 s merges with the next one if both fit together (<= 2 lines)
    k = 0
    while k < len(st) - 1:
        a, b = st[k], st[k + 1]
        if (a[1] - a[0] < 0.45 and b[0] - a[1] < 0.1
                and len("".join(norm(w) for w in a[2] + b[2])) <= 34):
            st[k] = [a[0], b[1], a[2] + b[2], keys]
            del st[k + 1]
        else:
            k += 1
    caps += st
    ckeys = set(norm(k) for k in CTA_KEYS.split())
    for c in spread(CTA, P["t_cta"], len(P["cta"]) / SR):
        caps.append(c + [ckeys])
    caps[-1][1] = P["T"] - 0.2
    return caps


CAP_SIZE, CAP_STROKE, CAP_MAXW = 74, 7, 860


def word_img(w, fill, f):
    w = w.replace(WJ, " ")
    d0 = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    bb = d0.textbbox((0, 0), w, font=f, stroke_width=CAP_STROKE, direction="rtl", anchor="ls")
    asc, desc = f.getmetrics()
    m = 6
    img = Image.new("RGBA", (bb[2] - bb[0] + 2 * m, asc + desc + 2 * m), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((m - bb[0], m + asc), w, font=f, fill=fill, stroke_width=CAP_STROKE,
                             stroke_fill=INK, direction="rtl", anchor="ls")
    return img, m


def text_w(t, f):
    t = t.replace(WJ, " ")
    d0 = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    bb = d0.textbbox((0, 0), t, font=f, stroke_width=CAP_STROKE, direction="rtl")
    return bb[2] - bb[0]


def two_lines(words, f):
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        m = max(text_w(a, f), text_w(b, f))
        if best is None or m < best[0]:
            best = (m, [a, b])
    return best


def balanced_lines(words, f):
    """One line if it fits; else the 2-line split with the smallest longest line (no orphans).
    Glued phrases stay together, but as a last resort they may wrap inside the same caption."""
    full = " ".join(words)
    if text_w(full, f) <= CAP_MAXW:
        return [full]
    best = two_lines(words, f) if len(words) > 1 else None
    if best and best[0] <= CAP_MAXW:
        return best[1]
    sub = [p for w in words for p in w.split(WJ)]
    if len(sub) > len(words):
        best = two_lines(sub, f)
        if best[0] <= CAP_MAXW:
            return best[1]
    return wrap_lines(full, "black", CAP_SIZE, CAP_MAXW)


def caption_image(words, keys):
    f = font("black", CAP_SIZE)
    lines = balanced_lines(words, f)
    space = int(CAP_SIZE * 0.26)
    rows = []
    for line in lines:
        ims = []
        for w in line.split():                    # glued phrases: same word gap, one colour for the phrase
            col = GOLD if is_key(w, keys) else WHITE
            ims += [word_img(p, col, f) for p in w.split(WJ)]
        inner = [im.width - 2 * m for im, m in ims]
        total = sum(inner) + space * (len(ims) - 1)
        m = ims[0][1]
        row = Image.new("RGBA", (total + 2 * m, ims[0][0].height), (0, 0, 0, 0))
        xr = m + total
        for (im, _), iw in zip(ims, inner):
            row.alpha_composite(im, (xr - iw - m, 0))
            xr -= iw + space
        rows.append(row)
    lh = int(CAP_SIZE * 1.32)
    wmax = max(r.width for r in rows)
    block = Image.new("RGBA", (wmax + 40, lh * (len(rows) - 1) + rows[-1].height + 40), (0, 0, 0, 0))
    for k, r in enumerate(rows):
        block.alpha_composite(r, ((block.width - r.width) // 2, 20 + k * lh))
    sh = Image.new("RGBA", block.size, (0, 0, 0, 0))
    sh.putalpha(block.getchannel("A").filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.55)))
    out = Image.new("RGBA", block.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 6))
    out.alpha_composite(block)
    return out


# ------------------------------------------------------------------ static layers
def make_header(sp):
    hd = Image.new("RGBA", (VW, FY), (0, 0, 0, 0))
    tag = chip(SERIES, GOLD, kind="black", size=38, fg=INK, padx=30, pady=4)
    hd.alpha_composite(tag, ((VW - tag.width) // 2, 168 - tag.height // 2))
    l1 = text_image(sp["l1"], "black", 92, WHITE, shadow=8)
    hd.alpha_composite(l1, ((VW - l1.width) // 2, 292 - l1.height // 2))
    size = 210
    while True:
        nm = text_image(sp["name"] + "؟", "display", size, GOLD, shadow=10)
        if nm.width <= 1000 or size <= 120:
            break
        size -= 6
    g = glow(nm, radius=22, strength=0.55)
    hd.alpha_composite(g, ((VW - g.width) // 2, 452 - g.height // 2))
    return hd


def fg_shadow():
    sh = Image.new("RGBA", (VW, FH + 120), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([0, 60, VW, 60 + FH], fill=(0, 0, 0, 200))
    return sh.filter(ImageFilter.GaussianBlur(26))


def hook_source(key):
    im = Image.open(os.path.join(IMG, key + ".jpg")).convert("RGB")
    tw, th = int(FW * 1.16), int(FH * 1.16)
    r = max(tw / im.width, th / im.height)
    im = im.resize((int(im.width * r + 0.5), int(im.height * r + 0.5)), Image.LANCZOS)
    x0, y0 = (im.width - tw) // 2, (im.height - th) // 2
    return grade_image(im.crop((x0, y0, x0 + tw, y0 + th)), warmth=0.3)


def ken(src, z):
    """z in [1, 1.16]: crop a centred window of src and scale it to the 16:9 window."""
    w, h = src.width / z, src.height / z
    x0, y0 = (src.width - w) / 2, (src.height - h) / 2
    return src.transform((FW, FH), Image.AFFINE, (w / FW, 0, x0, 0, h / FH, y0), resample=Image.BILINEAR)


def play_button():
    s = 150
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, s - 1, s - 1], fill=(12, 16, 30, 170), outline=GOLD + (255,), width=7)
    d.polygon([(s * 0.40, s * 0.30), (s * 0.40, s * 0.70), (s * 0.72, s * 0.50)], fill=GOLD + (255,))
    return im


DARK = [int(v * 0.42) for v in range(256)] * 3


def make_bg(fg):
    cw = int(FH * VW / VH)
    x0 = (FW - cw) // 2
    small = fg.crop((x0, 0, x0 + cw, FH)).resize((36, 64), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2.0))
    return small.resize((VW, VH), Image.BICUBIC).point(DARK)


# ------------------------------------------------------------------ frames
class Composer:
    def __init__(self, sp, P):
        self.sp, self.P = sp, P
        self.header = make_header(sp)
        self.shadow = fg_shadow()
        self.hook = hook_source(sp["img"])
        th = Image.open(THUMB).convert("RGB")
        self.thumb = th.resize((int(FW * 1.06), int(FH * 1.06)), Image.LANCZOS)
        self.play = play_button()
        self.full_chip = chip("الفيديو الكامل", TEAL, kind="black", size=34, fg=INK, padx=22, pady=2)
        self.caps = make_captions(sp, P)
        self._cap_cache = {}

    def cap(self, k):
        if k not in self._cap_cache:
            self._cap_cache[k] = caption_image(self.caps[k][2], self.caps[k][3])
        return self._cap_cache[k]

    def hook_fg(self, t):
        return ken(self.hook, 1.0 + 0.10 * clamp(t / (self.P["th"] + 0.4)))

    def cta_fg(self, t):
        P = self.P
        u = clamp((t - P["t_end_story"]) / (P["T"] - P["t_end_story"]))
        fg = ken(self.thumb, 1.0 + 0.05 * u)
        fg = fg.convert("RGBA")
        s = 1.0 + 0.06 * math.sin(2 * math.pi * 1.1 * (t - P["t_end_story"]))
        pb = self.play.resize((int(self.play.width * s), int(self.play.height * s)), Image.BILINEAR)
        fg.alpha_composite(pb, (int(FW * 0.27) - pb.width // 2, int(FH * 0.50) - pb.height // 2))
        fg.alpha_composite(self.full_chip, (28, 24))
        return fg.convert("RGB")

    def compose(self, t, story_fg=None, phase=None):
        P = self.P
        if phase is None:
            phase = ("hook" if t < P["th"] - 1e-6 else
                     "story" if t < P["t_end_story"] - 1e-6 else "cta")
        if phase == "hook":
            fg = self.hook_fg(t)
        elif phase == "story":
            fg = story_fg
            a = (t - P["th"]) / 0.2
            if a < 1:
                fg = Image.blend(self.hook_fg(t), fg, ease_out_cubic(clamp(a)))
        else:
            fg = self.cta_fg(t)
            a = (t - P["t_end_story"]) / 0.25
            if a < 1 and self._last_story is not None:
                fg = Image.blend(self._last_story, fg, ease_out_cubic(clamp(a)))
        if story_fg is not None:
            self._last_story = story_fg
        canvas = make_bg(fg)
        canvas.paste(self.shadow, (0, FY - 60), self.shadow)
        canvas.paste(fg, (0, FY))
        canvas.paste(self.header, (0, 0), self.header)
        # progress bar (right -> left, RTL)
        d = ImageDraw.Draw(canvas)
        y = FY + FH + 10
        d.rectangle([60, y, VW - 60, y + 7], fill=(70, 74, 90))
        p = clamp(t / P["T"])
        d.rectangle([VW - 60 - int((VW - 120) * p), y, VW - 60, y + 7], fill=GOLD)
        # caption
        for k, c in enumerate(self.caps):
            if c[0] <= t < c[1]:
                im = self.cap(k)
                u = clamp((t - c[0]) / 0.14)
                s = 0.86 + 0.14 * ease_out_back(u)
                if s != 1.0:
                    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
                if u < 1:
                    a = im.getchannel("A").point(lambda v, f=0.35 + 0.65 * u: int(v * f))
                    im = im.copy()
                    im.putalpha(a)
                canvas.paste(im, (VW // 2 - im.width // 2, CAP_Y - im.height // 2), im)
                break
        return canvas

    _last_story = None


def story_reader(P):
    """Yields the story frames (16:9 window size) in order; frames inside the opening crossfade
    of a section are replaced by the first clean frame."""
    t_start = max(P["cut_t"], P["vis_min"])
    skip = int(round((t_start - P["cut_t"]) * FPS)) if t_start > P["cut_t"] else 0
    nread = P["n_story"] - skip
    proc = subprocess.Popen([FF, "-v", "error", "-ss", f"{t_start:.3f}", "-i", VIDEO, "-frames:v", str(nread),
                             "-vf", f"scale={FW}:{FH}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            stdout=subprocess.PIPE)
    sz = FW * FH * 3
    last, produced = None, 0
    for k in range(nread):
        buf = proc.stdout.read(sz)
        if len(buf) < sz:
            break
        last = Image.frombuffer("RGB", (FW, FH), buf).copy()
        reps = skip + 1 if k == 0 else 1
        for _ in range(reps):
            produced += 1
            yield last
    while produced < P["n_story"]:          # (only if the decoder came up short)
        produced += 1
        yield last
    proc.wait()


def story_frame_at(P, t_long):
    t_long = max(t_long, P["vis_min"])
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{t_long:.3f}", "-i", VIDEO, "-frames:v", "1",
                          "-vf", f"scale={FW}:{FH}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return Image.frombuffer("RGB", (FW, FH), raw).copy()


# ------------------------------------------------------------------ commands
def index_of(sid):
    return [s["id"] for s in SHORTS].index(sid) + 1


def cover_image(sid):
    p = os.path.join(COVERS, f"{index_of(sid):02d}_{sid}.jpg")
    if not os.path.exists(p):
        import covers
        os.makedirs(COVERS, exist_ok=True)
        covers.make_cover(sid).save(p, quality=92, subsampling=0, optimize=True)
    im = Image.open(p).convert("RGB")
    return im if im.size == (VW, VH) else im.resize((VW, VH), Image.LANCZOS)


def render(sid):
    sp = next(s for s in SHORTS if s["id"] == sid)
    os.makedirs(OUT, exist_ok=True)
    P = make_plan(sp)
    aud = os.path.join(OUT, f"_{sid}.m4a")
    build_audio(sp, P, aud)
    out = os.path.join(OUT, f"{index_of(sid):02d}_{sid}.mp4")
    enc = subprocess.Popen([FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}",
                            "-r", str(FPS), "-i", "-", "-i", aud, "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-maxrate", "8M", "-bufsize", "16M",
                            "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest",
                            "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    C = Composer(sp, P)
    reader = story_reader(P)
    f_th = int(round(P["th"] * FPS))
    for k in range(P["n"]):
        t = k / FPS
        phase = "hook" if k < f_th else "story" if k < f_th + P["n_story"] else "cta"
        sf = next(reader) if phase == "story" else None
        frame = C.compose(t, sf, phase)
        enc.stdin.write(frame.tobytes())
    cover = cover_image(sid)
    for j in range(COVER_FADE):
        enc.stdin.write(Image.blend(frame, cover, ease_out_cubic((j + 1) / (COVER_FADE + 1))).tobytes())
    for _ in range(COVER_HOLD):
        enc.stdin.write(cover.tobytes())
    enc.stdin.close()
    enc.wait()
    os.remove(aud)
    print(f"done {out}  {P['T_out']:.2f}s", flush=True)


def remux_audio(sid):
    """Rebuild only the soundtrack (e.g. after a new score) and swap it into the existing MP4 - picture untouched."""
    sp = next(s for s in SHORTS if s["id"] == sid)
    P = make_plan(sp)
    out = os.path.join(OUT, f"{index_of(sid):02d}_{sid}.mp4")
    if not os.path.exists(out):
        return render(sid)
    pk = subprocess.run([FF, "-v", "error", "-i", out, "-map", "0:v", "-c", "copy", "-f", "framecrc", "-"],
                        capture_output=True, text=True).stdout
    nf = sum(1 for l in pk.splitlines() if l and not l.startswith("#"))
    if nf != P["n_out"]:
        raise SystemExit(f"{sid}: existing video has {nf} frames, plan has {P['n_out']} - run a full render instead")
    aud = os.path.join(OUT, f"_{sid}.m4a")
    build_audio(sp, P, aud)
    tmp = out + ".tmp.mp4"
    subprocess.run([FF, "-y", "-v", "error", "-i", out, "-i", aud, "-map", "0:v", "-map", "1:a", "-c", "copy",
                    "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)
    os.remove(aud)
    print(f"audio {out}  {P['T_out']:.2f}s", flush=True)


def preview(sid, times):
    sp = next(s for s in SHORTS if s["id"] == sid)
    os.makedirs(OUT, exist_ok=True)
    P = make_plan(sp)
    C = Composer(sp, P)
    for t in times:
        sf = None
        if P["th"] - 1e-6 <= t < P["t_end_story"] - 1e-6:
            sf = story_frame_at(P, P["cut_t"] + (t - P["th"]))
        elif t >= P["t_end_story"] - 1e-6:
            C._last_story = story_frame_at(P, P["cut_t"] + P["ls"] - 0.04)
        p = os.path.join(OUT, f"prev_{sid}_{t:06.2f}.jpg")
        C.compose(t, sf).save(p, quality=90)
        print(p)


def plan_all():
    for sp in SHORTS:
        P = make_plan(sp)
        sec = P["sec"]
        print(f"{sp['id']:9s} cut {P['cut_t']:7.2f} (onset {P['onset']:.2f}, silence {P['sil']:.2f}s)  "
              f"story {P['ls']:5.2f}s  hook {len(P['hook'])/SR:4.2f}s  total {P['T_out']:5.2f}s  "
              f"starts: «{sec['text'][P['c0']:P['c0']+28]}…»")


if __name__ == "__main__":
    a = sys.argv[1:] or ["plan"]
    if a[0] == "plan":
        plan_all()
    elif a[0] == "preview":
        preview(a[1], [float(x) for x in a[2:]])
    elif a[0] == "audio":
        for sid in ([s["id"] for s in SHORTS] if a[1:] in ([], ["all"]) else a[1:]):
            remux_audio(sid)
    else:
        ids = [s["id"] for s in SHORTS] if a[0] == "all" else a
        for sid in ids:
            render(sid)
