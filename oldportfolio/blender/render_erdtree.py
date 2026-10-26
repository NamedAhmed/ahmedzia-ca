"""Render erdtree.blend to erdtree.jpg with a soft bloom added afterwards.

Run:  blender --background erdtree.blend --python render_erdtree.py
Env:  ERD_SAMPLES (default: the file's setting), ERD_SCALE (resolution percentage, default 100),
      ERD_NAME (output name, default "erdtree"),
      ERD_REGION ("left,top,right,bottom" as fractions of the frame, to test one area quickly)
"""
import bpy, os, time
import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
scene = bpy.context.scene
r = scene.render
r.resolution_percentage = int(os.environ.get("ERD_SCALE", "100"))
if "ERD_SAMPLES" in os.environ:
    scene.cycles.samples = int(os.environ["ERD_SAMPLES"])
if "ERD_REGION" in os.environ:
    left, top, right, bottom = (float(v) for v in os.environ["ERD_REGION"].split(","))
    r.use_border = r.use_crop_to_border = True
    r.border_min_x, r.border_max_x = left, right
    r.border_min_y, r.border_max_y = 1 - bottom, 1 - top
r.image_settings.file_format = "PNG"

device = "CPU"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = kind
        except Exception:
            continue
        prefs.get_devices()
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == kind
            scene.cycles.device = "GPU"
            device = kind
            break
except Exception as e:
    print("GPU setup skipped:", e)

t0 = time.time()
raw = os.path.join(OUT, "erdtree_raw.png")
r.filepath = raw
bpy.ops.render.render(write_still=True)
print(f"RENDERED device={device} {time.time()-t0:.1f}s")

img = bpy.data.images.load(raw)
W, H = img.size
a = np.empty(W * H * 4, dtype=np.float32)
img.pixels.foreach_get(a)
rgb = a.reshape(H, W, 4)[:, :, :3]


def blur(ch, sigma):
    pad = int(sigma * 3)
    p = np.pad(ch, pad)
    fy = np.fft.fftfreq(p.shape[0])[:, None]
    fx = np.fft.rfftfreq(p.shape[1])[None, :]
    g = np.exp(-2 * (np.pi ** 2) * (sigma ** 2) * (fx ** 2 + fy ** 2))
    return np.fft.irfft2(np.fft.rfft2(p) * g, s=p.shape)[pad:-pad, pad:-pad]


k = W / 1440
bright = np.clip(rgb - 0.5, 0, None)
out = rgb.copy()
for c in range(3):
    out[:, :, c] += 0.5 * blur(bright[:, :, c], 5 * k) + 0.7 * blur(bright[:, :, c], 26 * k) + 0.55 * blur(bright[:, :, c], 100 * k)
out = np.clip(out, 0, 1)
res = bpy.data.images.new("erdtree_final", W, H, alpha=False)
full = np.ones((H, W, 4), dtype=np.float32)
full[:, :, :3] = out
res.pixels.foreach_set(full.reshape(-1))
res.filepath_raw = os.path.join(OUT, os.environ.get("ERD_NAME", "erdtree") + ".jpg")
res.file_format = "JPEG"
res.save()
print(f"DONE {time.time()-t0:.1f}s")
