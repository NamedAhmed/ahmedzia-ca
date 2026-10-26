"""Builds a retro CRT monitor, saves crt_monitor.blend and renders crt_monitor.png (transparent).

Run:  blender --background --python build_crt.py
The screen is rendered dark on purpose: the website draws the live terminal over it.
Prints SCREEN_RECT: where the screen opening sits in the image, as fractions of its size.
"""
import bpy, math, os, json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

OUT = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

A, B, Z0 = 2.4, 1.6, 0.3          # screen half-width, half-height, centre height (4:3)
FRONT = 0.3                        # y of the casing's front face; smaller y is nearer the camera
TOP, BOTTOM, HALF_W, DEPTH = 2.65, -2.95, 3.2, 4.8


def squircle(a, b, y, n=5.0, count=160):
    pts = []
    for k in range(count):
        t = 2 * math.pi * k / count
        c, s = math.cos(t), math.sin(t)
        pts.append((a * math.copysign(abs(c) ** (2 / n), c), y, Z0 + b * math.copysign(abs(s) ** (2 / n), s)))
    return pts


def material(name, color, rough=0.5, metallic=0.0, bumpy=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if bumpy:  # the fine grain moulded plastic has
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 140.0
        nz.inputs["Detail"].default_value = 2.0
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.12
        bump.inputs["Distance"].default_value = 0.02
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        nt.links.new(nz.outputs[0], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def add(name, verts, faces, mat, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


plastic = material("Plastic", (0.4, 0.36, 0.29), rough=0.48, bumpy=True)
dark = material("Dark Plastic", (0.05, 0.048, 0.045), rough=0.4)
metal = material("Badge", (0.6, 0.56, 0.48), rough=0.3, metallic=1.0)

# casing: a box that narrows toward the back, with soft moulded edges
bw, bz = HALF_W * 0.72, TOP - (TOP - BOTTOM) * 0.72
cv = [(-HALF_W, FRONT, BOTTOM), (HALF_W, FRONT, BOTTOM), (HALF_W, FRONT, TOP), (-HALF_W, FRONT, TOP),
      (-bw, DEPTH, bz), (bw, DEPTH, bz), (bw, DEPTH, TOP), (-bw, DEPTH, TOP)]
cf = [(0, 1, 2, 3), (5, 4, 7, 6), (4, 0, 3, 7), (1, 5, 6, 2), (3, 2, 6, 7), (4, 5, 1, 0)]
casing = add("CRT Casing", cv, cf, plastic)
bev = casing.modifiers.new("Bevel", "BEVEL")
bev.width, bev.segments = 0.28, 10
casing.modifiers.new("Normals", "WEIGHTED_NORMAL")

# bezel: a raised ring around the screen whose inner slope catches the screen's glow
rings = [squircle(A + 0.62, B + 0.62, FRONT + 0.02, n=7), squircle(A + 0.5, B + 0.5, -0.12, n=6.5),
         squircle(A + 0.34, B + 0.34, -0.16, n=6), squircle(A + 0.26, B + 0.26, -0.1, n=5.5),
         squircle(A, B, 0.24, n=5)]
bv, bf = [], []
count = len(rings[0])
for ring in rings:
    bv += ring
for r in range(len(rings) - 1):
    for k in range(count):
        a, b = r * count + k, r * count + (k + 1) % count
        bf.append((a, b, b + count, a + count))
add("CRT Bezel", bv, bf, plastic)

# glass: bulges toward the viewer; the camera sees it dark, but it lights the bezel amber
gv, gf, n = [], [], 40
for j in range(n + 1):
    for i in range(n + 1):
        u, v = i / n * 2 - 1, j / n * 2 - 1
        gv.append(((A + 0.08) * u, 0.26 - 0.2 * (1 - (u * u + v * v) / 2), Z0 + (B + 0.08) * v))
for j in range(n):
    for i in range(n):
        a = j * (n + 1) + i
        gf.append((a, a + 1, a + n + 2, a + n + 1))
gm = bpy.data.materials.new("Screen")
gm.use_nodes = True
nt = gm.node_tree
nt.nodes.remove(nt.nodes["Principled BSDF"])
lp = nt.nodes.new("ShaderNodeLightPath")
seen = nt.nodes.new("ShaderNodeEmission")
seen.inputs["Color"].default_value = (0.05, 0.028, 0.004, 1)
glow = nt.nodes.new("ShaderNodeEmission")
glow.inputs["Color"].default_value = (1.0, 0.55, 0.06, 1)
glow.inputs["Strength"].default_value = 2.4
mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
nt.links.new(glow.outputs[0], mix.inputs[1])
nt.links.new(seen.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
add("CRT Screen", gv, gf, gm)


def cyl(name, loc, radius, depth, mat, axis_y=True, scale=(1, 1, 1), verts=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    if axis_y:
        ob.rotation_euler = (math.radians(90), 0, 0)
    ob.scale = scale
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = True
    b = ob.modifiers.new("Bevel", "BEVEL")
    b.width, b.segments, b.limit_method = 0.03, 4, "ANGLE"
    return ob


def box(name, loc, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    ob.data.materials.append(mat)
    b = ob.modifiers.new("Bevel", "BEVEL")
    b.width, b.segments = 0.015, 3
    return ob


chin = (BOTTOM + (Z0 - B - 0.62)) / 2  # middle of the strip under the bezel
cyl("Knob 1", (1.85, FRONT - 0.07, chin), 0.15, 0.16, dark)
cyl("Knob 2", (2.3, FRONT - 0.07, chin), 0.15, 0.16, dark)
box("Badge", (-2.35, FRONT - 0.01, chin), (0.8, 0.04, 0.17), metal)
box("Power Switch", (1.25, FRONT - 0.02, chin), (0.3, 0.06, 0.16), dark)
led = bpy.data.materials.new("LED")
led.use_nodes = True
lb = led.node_tree.nodes["Principled BSDF"]
lb.inputs["Emission Color"].default_value = (1.0, 0.5, 0.05, 1)
lb.inputs["Emission Strength"].default_value = 14.0
cyl("LED", (2.75, FRONT - 0.02, chin), 0.05, 0.06, led, verts=24)
for i in range(15):  # cooling slots on top
    box(f"Vent {i:02d}", (-2.1 + i * 0.3, 2.3, TOP + 0.005), (0.11, 2.2, 0.03), dark)
cyl("Neck", (0, 2.1, BOTTOM - 0.2), 0.95, 0.5, plastic, axis_y=False)
cyl("Base", (0, 2.0, BOTTOM - 0.52), 2.1, 0.26, plastic, axis_y=False, scale=(1, 0.85, 1))

# lights
def area(name, loc, target, power, size, color):
    d = bpy.data.lights.new(name, "AREA")
    d.energy, d.size, d.color = power, size, color
    ob = bpy.data.objects.new(name, d)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(ob)


area("Key", (-9, -8, 9), (0, 0, 0), 3600, 6, (1.0, 0.93, 0.8))
area("Fill", (9, -6, 0), (0, 0, 0), 260, 6, (0.7, 0.85, 1.0))
area("Top", (0, 3, 10), (0, 2, 0), 1300, 6, (1.0, 0.86, 0.6))
world = bpy.data.worlds.new("World")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.01, 0.01, 0.01, 1)
scene.world = world

# camera: raised but not tilted (lens shift), so the screen stays a true rectangle
RES_X, RES_Y = 1800, 1800
cam_d = bpy.data.cameras.new("Camera")
cam_d.lens, cam_d.sensor_fit, cam_d.sensor_width = 122, "VERTICAL", 36
cam_d.sensor_height = 36
dist, cam_z = 26.0, 3.4
frame_h = dist * 36 / 122
centre = (TOP + 0.5 + BOTTOM - 0.75) / 2
cam_d.shift_y = (centre - cam_z) / frame_h
cam = bpy.data.objects.new("Camera", cam_d)
cam.location = (0, -dist + FRONT, cam_z)
cam.rotation_euler = (math.radians(90), 0, 0)
scene.collection.objects.link(cam)
scene.camera = cam

r = scene.render
r.engine = "CYCLES"
r.resolution_x, r.resolution_y = RES_X, RES_Y
r.resolution_percentage = int(os.environ.get("CRT_SCALE", "100"))
r.film_transparent = True
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGBA"
scene.cycles.samples = int(os.environ.get("CRT_SAMPLES", "160"))
scene.cycles.use_denoising = True
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
            break
except Exception as e:
    print("GPU setup skipped:", e)

bpy.context.view_layer.update()
pts = [world_to_camera_view(scene, cam, Vector(p)) for p in rings[-1]]
xs, ys = [p.x for p in pts], [p.y for p in pts]
rect = {"left": round(min(xs), 4), "top": round(1 - max(ys), 4), "width": round(max(xs) - min(xs), 4), "height": round(max(ys) - min(ys), 4)}
print("SCREEN_RECT " + json.dumps(rect))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "crt_monitor.blend"))
r.filepath = os.path.join(OUT, "crt_monitor.png")
bpy.ops.render.render(write_still=True)
print("DONE")
