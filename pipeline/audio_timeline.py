"""Audio analysis: durations, pause detection, and the master timeline."""
import json
import re
import subprocess

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def duration(path):
    err = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", err)
    h, mnt, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mnt * 60 + s


def speech_runs(path, noise="-32dB", min_sil=0.18):
    err = subprocess.run(
        [FFMPEG, "-i", path, "-af", f"silencedetect=noise={noise}:d={min_sil}", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", err)]
    total = duration(path)
    runs, t = [], 0.0
    for i, s in enumerate(starts):
        s = max(0.0, s)
        if s - t > 0.12:
            runs.append((t, s))
        t = ends[i] if i < len(ends) else total
    if total - t > 0.12:
        runs.append((t, total))
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < 0.14:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append((r[0], r[1]))
    return merged, total


def build_timeline(pad_lead=0.28, min_scene=1.1, tail=2.2):
    clips = json.load(open("audio/clips.json"))
    d = json.load(open("data/vehicles.json"))
    cats = {c["id"]: c for c in d["categories"]}
    vs = {v["id"]: v for v in d["vehicles"]}

    units = []
    for c in clips:
        runs, clen = speech_runs(f"audio/{c['id']}.mp3")
        u = c["units"]
        total_chars = sum(x["chars"] for x in u)
        gaps = [(runs[i][1], runs[i + 1][0]) for i in range(len(runs) - 1)] if len(runs) > 1 else []
        bounds, cum, prev = [], 0, 0.0
        for i, x in enumerate(u):
            if i < len(u) - 1:
                cum += x["chars"]
                est = clen * cum / total_chars
                best, bestd = None, 9e9
                for g in gaps:
                    mid = (g[0] + g[1]) / 2
                    if abs(mid - est) < bestd and mid > prev + 0.4:
                        best, bestd = mid, abs(mid - est)
                cut = best if (best is not None and bestd < 2.6) else est
                cut = max(cut, prev + 0.6)
            else:
                cut = clen
            bounds.append((prev, cut))
            prev = cut
        for x, b in zip(u, bounds):
            units.append(dict(kind=x["kind"], cat=x["cat"], vid=x["vid"],
                              a0=b[0], a1=b[1], clip=c["id"]))

    offset = 0.0
    for c in clips:
        clen = duration(f"audio/{c['id']}.mp3")
        for u in units:
            if u["clip"] == c["id"]:
                u["a0"] += offset
                u["a1"] += offset
        offset += clen
    total_audio = offset

    units.sort(key=lambda u: u["a0"])

    scenes, veh_i = [], 0
    for u in units:
        s = dict(u)
        if u["kind"] == "vehicle":
            veh_i += 1
            s["index"] = veh_i
            s["vehicle"] = vs[u["vid"]]
            s["category"] = cats[u["cat"]]
        elif u["kind"] == "section":
            s["category"] = cats[u["cat"]]
            s["index"] = cats[u["cat"]]["index"]
        scenes.append(s)

    for i, s in enumerate(scenes):
        want = 0.0 if i == 0 else s["a0"] - pad_lead
        s["t0"] = want if i == 0 else max(want, scenes[i - 1]["t0"] + min_scene)
    for i, s in enumerate(scenes):
        s["t1"] = scenes[i + 1]["t0"] if i + 1 < len(scenes) else total_audio + tail
        s["dur"] = round(s["t1"] - s["t0"], 3)

    out = dict(total_audio=round(total_audio, 3),
               total_video=round(scenes[-1]["t1"], 3),
               total_vehicles=len(d["vehicles"]), scenes=scenes)
    json.dump(out, open("work/timeline.json", "w"), indent=1)
    return out


if __name__ == "__main__":
    tl = build_timeline()
    print("audio %.1fs  video %.1fs (%.1f min)  scenes %d" %
          (tl["total_audio"], tl["total_video"], tl["total_video"] / 60, len(tl["scenes"])))
