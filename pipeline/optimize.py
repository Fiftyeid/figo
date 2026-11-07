"""Lock the film: shrink renders to JPEG q97 and drop regenerable intermediates."""
import glob
import os

from PIL import Image

for p in sorted(glob.glob("renders/*.png")):
    j = p[:-4] + ".jpg"
    im = Image.open(p).convert("RGB")
    im.save(j, quality=97, subsampling=0)
    if os.path.getsize(j) < os.path.getsize(p):
        os.remove(p)
    print("%-24s -> %-24s %5.2f MB" % (os.path.basename(p), os.path.basename(j),
                                       os.path.getsize(j) / 1e6))

for f in glob.glob("work/scenes/*.png") + glob.glob("work/*.wav"):
    os.remove(f)
print("cleaned intermediates")
