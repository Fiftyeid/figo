# -*- coding: utf-8 -*-
"""
Narration timing:
  1. process every TTS clip (tempo 1.05x, high-pass) -> 48 kHz mono
  2. align the script text to detected pauses (DP alignment of punctuation <-> silences)
  3. cut clips into sections, insert gaps, write build/narration.wav + build/timeline.json
Each section in timeline.json carries a char->time map so storyboard anchors
(sub-strings of the section text) can be converted to absolute times.
"""
import json, os, re, math, subprocess, bisect
import numpy as np
import imageio_ffmpeg

from script_data import SECTIONS, tts_text
from common import BUILD, ROOT

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
TEMPO = 1.0
GAP_SECTION = 0.55      # extra breathing room between sections
TITLE_GAP = 3.4         # title sting inserted after the intro hook
HOOK_END = "the sixty-year race to break through it."    # intro is split right after this phrase
LEAD_IN = 0.6           # silence before first word

STRONG = set(".!?…:")
WEAK = set(",;—")


def num_punct(text, i):
    """True for '.' / ',' inside a number (400.87, 1,200) - spoken, not a pause."""
    return (text[i] in ".," and 0 < i < len(text) - 1 and text[i - 1].isdigit() and text[i + 1].isdigit())


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def process_clip(src, dst):
    run([FF, "-y", "-v", "error", "-i", src, "-af",
         f"atempo={TEMPO},highpass=f=60,aresample={SR}", "-ac", "1", "-c:a", "pcm_s16le", dst])


def load(path):
    raw = subprocess.run([FF, "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def silences(x, win=0.01, thr_db=-38.0, min_len=0.16):
    hop = int(SR * win)
    n = len(x) // hop
    fr = x[: n * hop].reshape(n, hop)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(1) + 1e-12) + 1e-9)
    q = db < thr_db
    out, i = [], 0
    while i < n:
        if q[i]:
            j = i
            while j < n and q[j]:
                j += 1
            if (j - i) * win >= min_len:
                out.append((i * win, j * win))
            i = j
        else:
            i += 1
    return out


def char_weights(text):
    w = np.zeros(len(text), np.float32)
    for i, ch in enumerate(text):
        if num_punct(text, i):
            w[i] = 3.0 if ch == "." else 0.0     # "point" / silent thousands separator
        elif ch.isdigit():
            w[i] = 3.2                            # digits are read as long words
        elif ch.isalpha():
            w[i] = 1.0
        elif ch == " ":
            w[i] = 0.35
        elif ch in WEAK:
            w[i] = 2.2
        elif ch in STRONG:
            w[i] = 5.0
        elif ch == "\n":
            w[i] = 0.0
        else:
            w[i] = 0.1   # diacritics etc.
    return w


def align_clip(text, sil, dur):
    """Return list of (char_index, time) mapping points for one clip."""
    speech0 = sil[0][1] if sil and sil[0][0] <= 0.02 else 0.0
    speech1 = sil[-1][0] if sil and sil[-1][1] >= dur - 0.05 else dur
    inner = [s for s in sil if s[0] > speech0 + 0.05 and s[1] < speech1 - 0.05 and s[1] - s[0] >= 0.26]
    w = char_weights(text)
    cw = np.concatenate([[0], np.cumsum(w)])
    tot = cw[-1]

    def est(ci):
        return speech0 + (speech1 - speech0) * cw[ci] / tot

    # candidate break points: strong punctuation (+ following whitespace) and weak ones
    cands = []
    for i, ch in enumerate(text):
        if num_punct(text, i):
            continue
        if ch in STRONG:
            # skip runs like '!…' -> keep last of run
            if i + 1 < len(text) and (text[i + 1] in STRONG):
                continue
            strength = 2.0 if (i + 1 < len(text) and text[i + 1] == "\n") else 1.0
            cands.append((i, strength))
        elif ch in WEAK:
            cands.append((i, 0.35))
    m, n = len(cands), len(inner)
    INF = 1e9
    # dp[i][j]: best cost aligning first i cands with first j silences
    dp = np.full((m + 1, n + 1), INF)
    bt = np.zeros((m + 1, n + 1), np.int8)
    dp[0, :] = np.arange(n + 1) * 0.9  # unused silences before first cand
    for i in range(1, m + 1):
        ci, strength = cands[i - 1]
        e = est(ci + 1)
        skip_c = 0.9 * strength + 0.05
        for j in range(0, n + 1):
            best, arg = dp[i - 1, j] + skip_c, 0           # cand without silence
            if j > 0:
                v = dp[i, j - 1] + 0.9                       # unused silence
                if v < best:
                    best, arg = v, 1
                mid = (inner[j - 1][0] + inner[j - 1][1]) / 2
                v = dp[i - 1, j - 1] + abs(mid - e) * 1.2 - 0.3 * strength
                if v < best:
                    best, arg = v, 2
            dp[i, j], bt[i, j] = best, arg
    # backtrack
    i, j = m, n
    pairs = []
    while i > 0 or j > 0:
        a = bt[i, j] if i > 0 else 1
        if i > 0 and a == 0:
            i -= 1
        elif a == 1 or i == 0:
            j -= 1
        else:
            pairs.append((cands[i - 1][0], inner[j - 1]))
            i -= 1
            j -= 1
    pairs.reverse()
    pts = [(0, speech0)]
    for ci, (s0, s1) in pairs:
        pts.append((ci + 1, s0))
        pts.append((ci + 1.5, s1))   # half index => "after the pause"
    pts.append((len(text), speech1))
    # make strictly monotonic
    clean = []
    for c, t in pts:
        if clean and (c <= clean[-1][0] or t < clean[-1][1]):
            continue
        clean.append((c, t))
    return clean, cw


def char_to_time(points, cw, ci):
    """Piecewise-linear in cumulative-weight space."""
    cs = [p[0] for p in points]
    k = bisect.bisect_right(cs, ci) - 1
    k = max(0, min(k, len(points) - 2))
    c0, t0 = points[k]
    c1, t1 = points[k + 1]

    def W(c):
        c = max(0.0, min(float(c), len(cw) - 1.0))
        lo = int(np.floor(c)); hi = min(lo + 1, len(cw) - 1)
        return cw[lo] + (cw[hi] - cw[lo]) * (c - lo)

    w0, w1, wc = W(c0), W(c1), W(ci)
    if w1 - w0 < 1e-6:
        return t0
    return t0 + (t1 - t0) * (wc - w0) / (w1 - w0)


def main():
    groups = json.load(open(os.path.join(ROOT, "script", "clip_groups.json")))
    adir = os.path.join(BUILD, "audio")
    pieces = []   # (array, section_id or None, char_offset_in_section_for_start, local_map)
    timeline = {"sections": [], "sr": SR}
    out_audio = [np.zeros(int(LEAD_IN * SR), np.float32)]
    t_cursor = LEAD_IN

    for ci, g in enumerate(groups):
        src = os.path.join(adir, f"clip_{ci:02d}.wav")
        if not os.path.exists(src):   # fresh checkout: decode the archived TTS clip
            os.makedirs(adir, exist_ok=True)
            run([FF, "-y", "-v", "error", "-i", os.path.join(ROOT, "assets", "audio", f"clip_{ci:02d}.opus"),
                 "-ar", "24000", "-ac", "1", src])
        dst = os.path.join(adir, f"proc_{ci:02d}.wav")
        process_clip(src, dst)
        x = load(dst)
        dur = len(x) / SR
        sil = silences(x)
        texts = [tts_text(SECTIONS[i]) for i in g]
        clip_text = "\n\n".join(texts)
        pts, cw = align_clip(clip_text, sil, dur)
        # section char ranges inside clip text
        offs, o = [], 0
        for t in texts:
            offs.append((o, o + len(t)))
            o += len(t) + 2
        def nearest_sil(tt, maxd=0.8):
            best, bd = None, 1e9
            for s0, s1 in sil:
                dd = 0.0 if s0 <= tt <= s1 else min(abs(tt - s0), abs(tt - s1))
                if dd < bd:
                    best, bd = (s0, s1), dd
            return best if bd <= maxd else None

        # shared cut points between consecutive sections
        cuts = []   # (end_of_k, start_of_k+1)
        for k in range(len(g) - 1):
            bt = char_to_time(pts, cw, offs[k][1])
            sl = nearest_sil(bt)
            if sl:
                m = min(0.12, (sl[1] - sl[0]) / 2)
                cuts.append((sl[0] + m, sl[1] - m))
            else:
                cuts.append((bt, bt))
        clip_start = max(0.0, (sil[0][1] - 0.08) if sil and sil[0][0] <= 0.02 else 0.0)
        clip_end = min(dur, (sil[-1][0] + 0.15) if sil and sil[-1][1] >= dur - 0.05 else dur)
        for k, sidx in enumerate(g):
            a, b = offs[k]
            t_start = clip_start if k == 0 else cuts[k - 1][1]
            t_end = clip_end if k == len(g) - 1 else cuts[k][0]
            sec = SECTIONS[sidx]
            stext = texts[k]
            # optional split (intro hook -> title sting)
            splits = []
            if sec["id"] == "intro":
                hk = stext.find(HOOK_END)
                if hk >= 0:
                    c_after = a + hk + len(HOOK_END)
                    t_h = char_to_time(pts, cw, c_after)
                    sl = nearest_sil(t_h)
                    if sl:
                        splits.append((c_after - a, sl[0] + 0.1, sl[1] - 0.05))
            pieces_here = []
            cur0 = t_start
            for (cs, ts0, ts1) in splits:
                pieces_here.append(("AUDIO", cur0, ts0))
                pieces_here.append(("GAP", TITLE_GAP))
                cur0 = ts1
            pieces_here.append(("AUDIO", cur0, t_end))
            abs_start = t_cursor
            title_at = None
            after_gap = []    # abs. time where the voice resumes after the title sting
            shift_list = []   # (l0, l1, shift)
            for p in pieces_here:
                if p[0] == "GAP":
                    title_at = t_cursor
                    out_audio.append(np.zeros(int(p[1] * SR), np.float32))
                    t_cursor += p[1]
                    after_gap.append(t_cursor)
                    continue
                _, l0, l1 = p
                seg = x[int(l0 * SR): int(l1 * SR)].copy()
                fl = min(len(seg) // 2, int(0.01 * SR))
                if fl > 0:
                    seg[:fl] *= np.linspace(0, 1, fl)
                    seg[-fl:] *= np.linspace(1, 0, fl)
                shift_list.append((l0, l1, t_cursor - l0))
                out_audio.append(seg)
                t_cursor += len(seg) / SR
            abs_end = t_cursor

            def local_to_abs(lt, shift_list=shift_list):
                for l0, l1, sh in shift_list:
                    if lt <= l1 + 1e-6:
                        return max(lt, l0) + sh
                l0, l1, sh = shift_list[-1]
                return min(lt, l1) + sh

            # char map for this section, sampled every few chars
            cmap = []
            for c in range(0, len(stext) + 1, 3):
                lt = char_to_time(pts, cw, a + c)
                cmap.append([c, round(local_to_abs(lt), 3)])
            cmap.append([len(stext), round(abs_end, 3)])
            # exact point right after each split: the sampled map must not interpolate across the title gap
            for (cs, _, _), tg in zip(splits, after_gap):
                cmap = [q for q in cmap if not (q[0] > cs and q[1] < tg)]
                cmap.append([cs + 1, round(tg, 3)])
                cmap.sort()
            timeline["sections"].append(dict(id=sec["id"], index=sidx, start=round(abs_start, 3),
                                             end=round(abs_end, 3), text=stext, cmap=cmap,
                                             title_at=round(title_at, 3) if title_at else None))
            # gap after section
            gap = GAP_SECTION
            if sidx == 0 and os.environ.get("ALIGN_TO"):
                # re-cut intro: pad the gap (< 1 frame) so every later section moves by a whole number
                # of frames vs. an earlier timeline -> the rest of the earlier render can be reused as is
                old_next = json.load(open(os.environ["ALIGN_TO"]))["sections"][1]["start"]
                d = (old_next - (t_cursor + gap)) * 25
                gap += (d - math.floor(d)) / 25
            out_audio.append(np.zeros(int(gap * SR), np.float32))
            t_cursor += gap
    out_audio.append(np.zeros(int(1.5 * SR), np.float32))
    t_cursor += 1.5
    y = np.concatenate(out_audio)
    timeline["duration"] = round(len(y) / SR, 3)
    # write narration
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    p = subprocess.Popen([FF, "-y", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
                          os.path.join(BUILD, "narration.wav")], stdin=subprocess.PIPE)
    p.communicate(pcm)
    json.dump(timeline, open(os.path.join(BUILD, "timeline.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("duration", timeline["duration"])
    for s in timeline["sections"]:
        print(f'{s["id"]:16s} {s["start"]:8.2f} {s["end"]:8.2f} {s["end"]-s["start"]:6.2f}', "title_at" if s["title_at"] else "")


if __name__ == "__main__":
    main()
