"""Pack the narration into <=1500-character TTS clips, splitting only at
vehicle boundaries, and emit audio/clips.json."""
import json
import os

LIMIT = 1480
d = json.load(open('data/vehicles.json'))
vs = d['vehicles']

units = [('intro', None, None, d['meta']['intro_vo'])]
for c in d['categories']:
    units.append(('section', c['id'], None, c['vo']))
    for v in vs:
        if v['cat'] == c['id']:
            units.append(('vehicle', c['id'], v['id'], v['vo']))
units.append(('outro', None, None, d['meta']['outro_vo']))

clips, cur, cur_len = [], [], 0
for u in units:
    t = u[3]
    assert len(t) < LIMIT, (len(t), u[0])
    if cur and cur_len + 1 + len(t) > LIMIT:
        clips.append(cur)
        cur, cur_len = [], 0
    cur.append(u)
    cur_len += len(t) + 1
if cur:
    clips.append(cur)

out = []
for i, c in enumerate(clips):
    out.append({
        "id": "clip%02d" % (i + 1),
        "text": " ".join(u[3] for u in c),
        "units": [{"kind": u[0], "cat": u[1], "vid": u[2], "chars": len(u[3])} for u in c],
        "chars": sum(len(u[3]) for u in c) + len(c) - 1,
    })
os.makedirs('audio', exist_ok=True)
json.dump(out, open('audio/clips.json', 'w'), indent=1)
for c in out:
    print(c['id'], c['chars'])
