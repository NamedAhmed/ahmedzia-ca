"""Procedural golden tree, built into the current Blender scene inside an "Erdtree" collection.

From a terminal (builds and saves erdtree.blend):
    blender --background --python run_build.py

Or inside Blender's Python console:
    import sys; sys.path.insert(0, r"<this folder>")
    import build_erdtree; build_erdtree.build()

Re-running replaces only the objects in the "Erdtree" collection.

The trunk, main limbs and roots are one real mesh with the bark sculpted into it, using a scanned
pine bark height map (Poly Haven, CC0, in textures/). The bark is applied in two layers:

  - a Displace modifier pushes a softened copy of the scan into the mesh, so the plates are real
    geometry you can see in the viewport and adjust in the modifier panel;
  - the material then displaces what the softened copy left out (the sharp edges and fine cracks)
    per pixel at render time, through the adaptive Subdivision modifier at the end of the stack.
"""
import bpy, math, os, random, time
import numpy as np
from mathutils import Vector

import bark_field

HERE = os.path.dirname(os.path.abspath(__file__))
TEX_HEIGHT = os.path.join(HERE, "textures", "pine_bark_disp_2k.png")
TEX_COLOR = os.path.join(HERE, "textures", "pine_bark_diff_2k.jpg")
TEX_SOFT = os.path.join(HERE, "textures", "pine_bark_disp_soft.exr")

MAXD = 8
UP = [0.0, 0.05, 0.03, 0.012, 0.0, -0.01, -0.02, -0.03, -0.04]
WOB = [0.03, 0.06, 0.08, 0.10, 0.13, 0.16, 0.20, 0.24, 0.28]
ANG = {0: (42, 66), 1: (22, 42), 2: (22, 42), 3: (22, 45), 4: (22, 48), 5: (22, 50), 6: (25, 55), 7: (25, 58)}
TRUNK_H = 20.0

BARK_MAX_DEPTH = 2   # branches up to this depth get real bark; finer ones are glowing twigs
VOXEL = 0.09         # the body is rebuilt from cubes this size
TILE_W = 8.5         # width of one repeat of the bark scan on the trunk, in scene units
TILE_ASPECT = 1.5    # stretch along the grain, for taller plates
BARK_DEPTH = 0.06    # how far the bark stands out, as a fraction of the local repeat width
HEIGHT_MID = 0.62    # the scan value that stays put; lighter moves out, darker cuts in
SOFT_SIZE = 128      # resolution of the softened scan the mesh itself can hold


def _perp(v):
    a = Vector((1, 0, 0)) if abs(v.x) < 0.9 else Vector((0, 1, 0))
    return v.cross(a).normalized()


def _turned(d, ang, az):
    a = _perp(d)
    b = d.cross(a)
    return (d * math.cos(ang) + (a * math.cos(az) + b * math.sin(az)) * math.sin(ang)).normalized()


def _skeleton(seed):
    """The tree as lines: a list of (depth, [(point, radius), ...]) for branches, and the same for roots.

    Radii never feed back into the random choices, so thickening a branch does not move anything.
    """
    random.seed(seed)
    branches = []

    def grow(start, d, length, r0, depth, r_start=None, side=False):
        n = max(4, int(length / 0.6))
        seg = length / n
        pts = []
        p = start.copy()
        d = d.normalized()
        for i in range(n + 1):
            t = i / n
            r = max(r0 * (1 - 0.42 * t), 0.022)
            if r_start:  # swell where it leaves its parent, easing down over the first third
                k = min(t / 0.33, 1.0)
                r += (r_start - r) * (1 - k * k * (3 - 2 * k))
            pts.append((p.copy(), r))
            if i == n:
                break
            wob = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))) * WOB[depth]
            radial = Vector((p.x, p.y, 0))
            radial = radial.normalized() if radial.length > 0.5 else Vector((0, 0, 0))
            d = (d + wob + radial * 0.09 + Vector((0, 0, 1)) * UP[depth]).normalized()
            p = p + d * seg
        branches.append((depth, pts))
        end, r_end = pts[-1]
        if depth >= MAXD:
            return
        k = 3 if depth == 1 else (random.choice([2, 3]) if depth <= 4 else 2)
        base_az = random.uniform(0, 2 * math.pi)
        for j in range(k):
            az = base_az + j * 2 * math.pi / k + random.uniform(-0.4, 0.4)
            ang = math.radians(random.uniform(*ANG[depth]))
            cr = r_end * (0.78 if k <= 2 else 0.66)
            grow(end, _turned(d, ang, az), length * random.uniform(0.66, 0.82), cr, depth + 1, r_start=r_end * 0.92, side=side)
        if not side and 1 <= depth <= 5:
            for _ in range(random.randint(1, 2)):
                i = random.randint(max(1, n // 4), n - 1)
                sp, sr = pts[i]
                nd = _turned(d, math.radians(random.uniform(40, 75)), random.uniform(0, 2 * math.pi))
                grow(sp, nd, length * 0.42, sr * 0.3, min(depth + 3, MAXD), side=True)

    trunk = []
    n = 56
    for i in range(n + 1):
        z = -0.4 + (TRUNK_H + 0.4) * i / n
        r = 2.4 + 0.6 * (1 - i / n) + 3.0 * math.exp(-max(z, 0) / 1.9)
        trunk.append((Vector((math.sin(z * 0.3) * 0.3, math.cos(z * 0.24) * 0.25, z)), r))
    top, top_r = trunk[-1]
    for i in range(1, 7):
        a = i / 6 * math.pi / 2
        trunk.append((top + Vector((0, 0, math.sin(a) * top_r * 0.7)), max(top_r * math.cos(a), 0.05)))
    branches.append((0, trunk))
    base_az = random.uniform(0, 2 * math.pi)
    for j in range(6):
        az = base_az + j * 2 * math.pi / 6 + random.uniform(-0.2, 0.2)
        ang = math.radians(random.uniform(*ANG[0]))
        grow(top, _turned(Vector((0, 0, 1)), ang, az), random.uniform(12, 14.5), 0.924, 1, r_start=top_r * 0.8)
    grow(top, Vector((0.04, 0.02, 1)), 9, 1.155, 1, r_start=top_r * 0.85)

    roots = []
    for j in range(11):
        a = j * 2 * math.pi / 11 + random.uniform(-0.2, 0.2)
        p = Vector((math.cos(a) * 1.8, math.sin(a) * 1.8, 2.2))
        d = Vector((math.cos(a), math.sin(a), -0.6)).normalized()
        length = random.uniform(10, 16)
        m = int(length / 0.45)
        pts = []
        for i in range(m + 1):
            t = i / m
            pts.append((p.copy(), 1.5 * (1 - t) ** 1.3 + 0.06))
            d = (d + Vector((random.gauss(0, 0.1), random.gauss(0, 0.1), -0.04))).normalized()
            if p.z < 0.15:
                d.z = max(d.z, -0.01)
                d.normalize()
            p = p + d * (length / m)
            p.z = max(p.z, -0.15)
        roots.append((0, pts))
    return branches, roots


# ------------------------------------------------------------------ the sculpted body
def _prepare(items):
    """Per branch: points, radii, and a frame (N, B) carried along it without twisting."""
    out = []
    for _, pts in items:
        P = np.array([p[:] for p, _ in pts], dtype=np.float64)
        R = np.array([r for _, r in pts], dtype=np.float64)
        T = np.empty_like(P)
        T[0], T[-1], T[1:-1] = P[1] - P[0], P[-1] - P[-2], P[2:] - P[:-2]
        T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
        N = np.empty_like(P)
        ref = np.array([1.0, 0, 0]) if abs(T[0, 0]) < 0.9 else np.array([0, 1.0, 0])
        n0 = np.cross(T[0], ref)
        N[0] = n0 / np.linalg.norm(n0)
        for i in range(1, len(P)):
            v = N[i - 1] - np.dot(N[i - 1], T[i]) * T[i]
            N[i] = v / max(np.linalg.norm(v), 1e-9)
        out.append({"P": P, "R": R, "N": N, "B": np.cross(T, N)})
    return out


def _tubes(branches, sides=28):
    """Every branch as a closed tube. They overlap freely; the remesh step fuses them."""
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    ca, sa = np.cos(ang), np.sin(ang)
    verts, faces, off = [], [], 0
    for br in branches:
        P, R, N, B = br["P"], br["R"], br["N"], br["B"]
        m = len(P)
        ring = P[:, None, :] + R[:, None, None] * (ca[None, :, None] * N[:, None, :] + sa[None, :, None] * B[:, None, :])
        verts.append(ring.reshape(-1, 3))
        verts.append(np.stack([P[0], P[-1]]))
        i = np.arange(m - 1)[:, None] * sides
        k = np.arange(sides)[None, :]
        k1 = (k + 1) % sides
        quads = np.stack([i + k, i + k1, i + sides + k1, i + sides + k], axis=-1).reshape(-1, 4) + off
        faces.extend(map(tuple, quads.tolist()))
        c0, c1, last = off + m * sides, off + m * sides + 1, off + (m - 1) * sides
        for a in range(sides):
            b = (a + 1) % sides
            faces.append((c0, off + b, off + a))
            faces.append((c1, last + a, last + b))
        off += m * sides + 2
    return np.concatenate(verts), faces


def _fused_mesh(branches, col):
    """Tubes -> one watertight surface with softened joins."""
    verts, faces = _tubes(branches)
    src = bpy.data.meshes.new("ErdtreeBodySource")
    src.from_pydata(verts.tolist(), [], faces)
    src.update()
    ob = bpy.data.objects.new("Erdtree Body Source", src)
    col.objects.link(ob)
    rm = ob.modifiers.new("Remesh", "REMESH")
    rm.mode, rm.voxel_size, rm.adaptivity = "VOXEL", VOXEL, 0.0
    sm = ob.modifiers.new("Smooth", "SMOOTH")
    sm.factor, sm.iterations = 0.5, 14
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.name = "ErdtreeBody"
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(src)
    return me


def _owners(X, branches):
    """For every vertex: which branch's surface it sits on, where along it, and how near the runner-up is."""
    nv = len(X)
    best = np.full(nv, 1e9, dtype=np.float32)
    second = np.full(nv, 1e9, dtype=np.float32)
    own_b = np.zeros(nv, dtype=np.int32)
    own_s = np.zeros(nv, dtype=np.int32)
    own_u = np.zeros(nv, dtype=np.float32)
    for bi, br in enumerate(branches):
        P, R = br["P"].astype(np.float32), br["R"].astype(np.float32)
        A, AB = P[:-1], P[1:] - P[:-1]
        L2 = np.maximum(np.einsum("ij,ij->i", AB, AB), 1e-12)
        pad = float(R.max()) + 0.8
        idx = np.nonzero(np.all((X > P.min(0) - pad) & (X < P.max(0) + pad), axis=1))[0]
        for c in range(0, len(idx), 30000):
            ids = idx[c:c + 30000]
            AX = X[ids, None, :] - A[None]
            u = np.clip(np.einsum("nsk,sk->ns", AX, AB) / L2, 0, 1)
            D = AX - u[..., None] * AB[None]
            dist = np.sqrt(np.einsum("nsk,nsk->ns", D, D))
            # The segment is the one whose axis is nearest. (Nearest surface picks the wrong one
            # wherever the radius changes fast, such as the root flare.)
            j = np.argmin(dist, axis=1)
            row = np.arange(len(ids))
            mb = dist[row, j] - (R[:-1][j] + u[row, j] * (R[1:][j] - R[:-1][j]))
            win = mb < best[ids]
            second[ids] = np.where(win, best[ids], np.minimum(second[ids], mb))
            w = ids[win]
            best[w], own_b[w], own_s[w], own_u[w] = mb[win], bi, j[win], u[row, j][win]
    return own_b, own_s, own_u, second - best


def _map_bark(me, branches, seed):
    """Lays the bark scan over the mesh (a UV map) and works out how deep it should press at each vertex.

    Returns that depth per vertex, in scene units per unit of scan height.
    """
    nv = len(me.vertices)
    X = np.empty(nv * 3, dtype=np.float32)
    me.vertices.foreach_get("co", X)
    X = X.reshape(-1, 3)
    Nrm = np.empty(nv * 3, dtype=np.float32)
    me.vertex_normals.foreach_get("vector", Nrm)
    Nrm = Nrm.reshape(-1, 3)

    own_b, own_s, own_u, gap = _owners(X, branches)

    # per vertex: angle around its branch, local radius, and distance along it in "repeats"
    rng = np.random.default_rng(seed + 100)  # its own generator: must not disturb the leaves' randomness
    U = np.zeros(nv, dtype=np.float32)
    V = np.zeros(nv, dtype=np.float32)
    width = np.ones(nv, dtype=np.float32)
    repeats = np.ones(nv, dtype=np.float32)
    for bi, br in enumerate(branches):
        m = own_b == bi
        if not m.any():
            continue
        P, R, N, B = br["P"], br["R"], br["N"], br["B"]
        r_ref = float(np.median(R))
        n_rep = max(1, round(2 * math.pi * r_ref / TILE_W))
        seg_len = np.linalg.norm(P[1:] - P[:-1], axis=1)
        r_mid = np.clip((R[:-1] + R[1:]) / 2, 0.35 * r_ref, 2.4 * r_ref)
        dv = seg_len / (TILE_ASPECT * 2 * math.pi * r_mid / n_rep)   # plates keep their shape as girth changes
        v0 = np.concatenate([[0], np.cumsum(dv)])
        s, u = own_s[m], own_u[m]
        axis = P[s] + u[:, None] * (P[s + 1] - P[s])
        o = X[m] - axis
        theta = np.arctan2(np.einsum("ij,ij->i", o, B[s]), np.einsum("ij,ij->i", o, N[s]))
        U[m] = theta / (2 * math.pi) * n_rep + rng.random()
        V[m] = v0[s] + u * dv[s] + rng.random()
        r_loc = np.clip(R[s] + u * (R[s + 1] - R[s]), 0.35 * r_ref, 2.4 * r_ref)
        width[m] = 2 * math.pi * r_loc / n_rep
        repeats[m] = n_rep

    # slow folds in the trunk itself, so it is not a perfect column. These are baked into the mesh.
    fold = bark_field.fbm(X * np.array([0.2, 0.2, 0.085], dtype=np.float32) + 40.0, octaves=3, seed=30) - 0.5
    me.vertices.foreach_set("co", (X + Nrm * (fold * 0.075 * width)[:, None]).reshape(-1))

    join = 0.3 + 0.7 * bark_field.smoothstep(0.0, 0.4, gap)      # calmer where two branches meet
    depth = (join * BARK_DEPTH * width).astype(np.float32)

    # UVs live on face corners. A face that straddles the wrap-around, or two branches, would smear
    # the whole scan across itself, so pull its corners next to the first one.
    nl = len(me.loops)
    lv = np.empty(nl, dtype=np.int32)
    me.loops.foreach_get("vertex_index", lv)
    npoly = len(me.polygons)
    start = np.empty(npoly, dtype=np.int32)
    total = np.empty(npoly, dtype=np.int32)
    me.polygons.foreach_get("loop_start", start)
    me.polygons.foreach_get("loop_total", total)
    first = lv[np.repeat(start, total)]
    cu, cv = U[lv], V[lv]
    cu = cu - repeats[first] * np.round((cu - U[first]) / repeats[first])
    stray = own_b[lv] != own_b[first]
    cu[stray], cv[stray] = U[first][stray], V[first][stray]
    uv = me.uv_layers.new(name="bark")
    uv.data.foreach_set("uv", np.stack([cu, cv], axis=1).astype(np.float32).reshape(-1))
    # the material needs the depth too, and a UV map is the one thing sure to survive subdivision
    amount = me.uv_layers.new(name="bark_depth")
    amount.data.foreach_set("uv", np.stack([depth[lv], np.zeros(nl, dtype=np.float32)], axis=1).reshape(-1))

    me.polygons.foreach_set("use_smooth", np.ones(npoly, dtype=bool))
    me.update()
    return depth


def _soft_scan():
    """A small, blurred copy of the bark scan: the part of the bark coarse enough for the mesh to hold."""
    img = bpy.data.images.load(TEX_HEIGHT, check_existing=True)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    a = px.reshape(h, w, 4)[:, :, 0]
    while a.shape[0] > SOFT_SIZE:
        a = (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) * 0.25
    old = bpy.data.images.get("Erdtree Bark Soft")
    if old:
        bpy.data.images.remove(old)
    soft = bpy.data.images.new("Erdtree Bark Soft", SOFT_SIZE, SOFT_SIZE, alpha=False, float_buffer=True, is_data=True)
    rgba = np.ones((SOFT_SIZE, SOFT_SIZE, 4), dtype=np.float32)
    rgba[:, :, :3] = a[:, :, None]
    soft.pixels.foreach_set(rgba.reshape(-1))
    soft.filepath_raw = TEX_SOFT
    soft.file_format = "OPEN_EXR"
    soft.save()
    soft.colorspace_settings.name = "Non-Color"
    return soft


# ------------------------------------------------------------------ materials
def _twig_material():
    m = bpy.data.materials.new("Erdtree Twigs")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    out = nt.nodes["Material Output"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 1.0, 0.06)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 7.0
    nz.inputs["Detail"].default_value = 8.0
    streak = nt.nodes.new("ShaderNodeMapRange")
    streak.inputs["From Min"].default_value = 0.35
    streak.inputs["From Max"].default_value = 0.75
    streak.inputs["To Min"].default_value = 0.3
    streak.inputs["To Max"].default_value = 1.3
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    rim = nt.nodes.new("ShaderNodeMath")
    rim.operation = "MULTIPLY_ADD"
    rim.inputs[1].default_value = 1.5
    rim.inputs[2].default_value = 1.0
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1.0, 0.8, 0.36, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs[0], streak.inputs["Value"])
    nt.links.new(lw.outputs["Facing"], rim.inputs[0])
    nt.links.new(streak.outputs[0], mul.inputs[0])
    nt.links.new(rim.outputs[0], mul.inputs[1])
    nt.links.new(mul.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def _bark_material(soft):
    """Recolours the brown pine scan to pale gold, and displaces the detail the mesh is too coarse to hold."""
    m = bpy.data.materials.new("Erdtree Bark")
    m.use_nodes = True
    m.displacement_method = "BOTH"   # real displacement, plus bump for anything finer than a pixel
    nt = m.node_tree
    N, L = nt.nodes.new, nt.links.new
    bsdf = nt.nodes["Principled BSDF"]
    uv = N("ShaderNodeUVMap")
    uv.uv_map = "bark"
    height = N("ShaderNodeTexImage")
    height.image = bpy.data.images.load(TEX_HEIGHT, check_existing=True)
    height.image.colorspace_settings.name = "Non-Color"
    blurred = N("ShaderNodeTexImage")
    blurred.image = soft
    color = N("ShaderNodeTexImage")
    color.image = bpy.data.images.load(TEX_COLOR, check_existing=True)
    for tex in (height, blurred, color):
        L(uv.outputs["UV"], tex.inputs["Vector"])

    # how far out of the crevices this point is, 0..1
    proud = N("ShaderNodeMapRange")
    proud.interpolation_type = "SMOOTHSTEP"
    proud.inputs["From Min"].default_value = 0.5
    proud.inputs["From Max"].default_value = 0.7
    L(height.outputs["Color"], proud.inputs["Value"])

    gold = N("ShaderNodeMix")
    gold.data_type = "RGBA"
    gold.inputs[6].default_value = (0.2, 0.15, 0.05, 1)    # down in the cracks
    gold.inputs[7].default_value = (1.0, 0.84, 0.44, 1)    # the face of a plate
    L(proud.outputs[0], gold.inputs[0])

    # keep the scan's light-and-dark mottling, drop its brown
    grey = N("ShaderNodeRGBToBW")
    L(color.outputs["Color"], grey.inputs["Color"])
    mottle = N("ShaderNodeMapRange")
    mottle.inputs["From Min"].default_value = 0.05
    mottle.inputs["From Max"].default_value = 0.32
    mottle.inputs["To Min"].default_value = 0.62
    mottle.inputs["To Max"].default_value = 1.15
    L(grey.outputs[0], mottle.inputs["Value"])
    shaded = N("ShaderNodeMix")
    shaded.data_type = "RGBA"
    shaded.blend_type = "MULTIPLY"
    shaded.inputs[0].default_value = 1.0
    L(gold.outputs[2], shaded.inputs[6])
    L(mottle.outputs[0], shaded.inputs[7])
    L(shaded.outputs[2], bsdf.inputs["Base Color"])

    # The Displace modifier has already pushed the blurred scan into the mesh. What is left is the
    # difference between the sharp scan and the blurred one: plate edges and fine cracks.
    fine = N("ShaderNodeMath")
    fine.operation = "SUBTRACT"
    L(height.outputs["Color"], fine.inputs[0])
    L(blurred.outputs["Color"], fine.inputs[1])
    depth_uv = N("ShaderNodeUVMap")
    depth_uv.uv_map = "bark_depth"
    depth = N("ShaderNodeSeparateXYZ")
    L(depth_uv.outputs["UV"], depth.inputs[0])
    disp = N("ShaderNodeDisplacement")
    disp.inputs["Midlevel"].default_value = 0.0
    L(fine.outputs[0], disp.inputs["Height"])
    L(depth.outputs["X"], disp.inputs["Scale"])
    L(disp.outputs["Displacement"], nt.nodes["Material Output"].inputs["Displacement"])

    glow = N("ShaderNodeMath")
    glow.operation = "MULTIPLY"
    glow.inputs[1].default_value = 0.26
    L(proud.outputs[0], glow.inputs[0])
    L(glow.outputs[0], bsdf.inputs["Emission Strength"])
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.78, 0.36, 1)
    bsdf.inputs["Roughness"].default_value = 0.78
    return m


def _leaf_material():
    m = bpy.data.materials.new("Erdtree Leaf")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    out = nt.nodes["Material Output"]
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "var"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].color = (1.0, 0.33, 0.03, 1)
    e[1].color = (1.0, 0.86, 0.3, 1)
    mid = e.new(0.5)
    mid.color = (1.0, 0.6, 0.08, 1)
    st = nt.nodes.new("ShaderNodeMath")
    st.operation = "MULTIPLY_ADD"
    st.inputs[1].default_value = 1.1
    st.inputs[2].default_value = 0.35
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(at.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(at.outputs["Fac"], st.inputs[0])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(st.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def _mist_material():
    m = bpy.data.materials.new("Erdtree Mist")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    out = nt.nodes["Material Output"]
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (0.62, 0.9, 0.7, 1)
    vol.inputs["Anisotropy"].default_value = 0.55
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.09
    nz.inputs["Detail"].default_value = 5.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.38
    mr.inputs["From Max"].default_value = 0.72
    mr.inputs["To Min"].default_value = 0.0012
    mr.inputs["To Max"].default_value = 0.015
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs[0], mr.inputs["Value"])
    nt.links.new(mr.outputs[0], vol.inputs["Density"])
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    return m


# ------------------------------------------------------------------ the scene
def build(seed=2):
    t0 = time.time()
    scene = bpy.context.scene
    np.random.seed(seed)

    col = bpy.data.collections.get("Erdtree")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    else:
        col = bpy.data.collections.new("Erdtree")
        scene.collection.children.link(col)
    for name in ("Erdtree Bark", "Erdtree Twigs", "Erdtree Leaf", "Erdtree Mist"):
        old = bpy.data.materials.get(name)
        if old:
            bpy.data.materials.remove(old)
    for name in ("ErdtreeBody", "ErdtreeLeaves", "ErdtreeMist"):
        old = bpy.data.meshes.get(name)
        if old and not old.users:
            bpy.data.meshes.remove(old)

    branches, roots = _skeleton(seed)

    # the body: trunk, main limbs and roots fused into one mesh, with the bark sculpted in
    body = _prepare([b for b in branches if b[0] <= BARK_MAX_DEPTH] + roots)
    body_me = _fused_mesh(body, col)
    depth = _map_bark(body_me, body, seed)
    soft = _soft_scan()
    body_me.materials.append(_bark_material(soft))
    wood = bpy.data.objects.new("Erdtree", body_me)
    col.objects.link(wood)
    body_verts = len(body_me.vertices)

    # the bark, as a modifier stack you can switch off or re-tune:
    # subdivide once -> press the softened scan in -> let the renderer split faces down to a pixel
    deepest = float(depth.max())
    group = wood.vertex_groups.new(name="bark_depth")
    for i, w in enumerate((depth / deepest).tolist()):
        group.add((i,), w, "REPLACE")
    sub = wood.modifiers.new("Subdivide", "SUBSURF")
    sub.levels = sub.render_levels = 1
    tex = bpy.data.textures.get("Erdtree Bark Soft") or bpy.data.textures.new("Erdtree Bark Soft", "IMAGE")
    tex.image = soft
    tex.extension = "REPEAT"
    press = wood.modifiers.new("Bark", "DISPLACE")
    press.texture = tex
    press.texture_coords = "UV"
    press.uv_layer = "bark"
    press.direction = "NORMAL"
    press.mid_level = HEIGHT_MID
    press.strength = deepest
    press.vertex_group = "bark_depth"
    fine = wood.modifiers.new("Fine detail (render)", "SUBSURF")
    fine.levels = 0
    fine.use_adaptive_subdivision = True
    fine.adaptive_space = "PIXEL"
    fine.adaptive_pixel_size = 1.5

    # everything finer glows
    curve = bpy.data.curves.new("ErdtreeTwigs", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 1.0
    curve.bevel_resolution = 2
    curve.use_fill_caps = True
    for depth, pts in branches:
        if depth <= BARK_MAX_DEPTH:
            continue
        sp = curve.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for sp_pt, (co, r) in zip(sp.points, pts):
            sp_pt.co = (co.x, co.y, co.z, 1.0)
            sp_pt.radius = r
    curve.materials.append(_twig_material())
    twigs = bpy.data.objects.new("Erdtree Twigs", curve)
    twigs.parent = wood
    col.objects.link(twigs)

    # leaves: only in the upper, outer crown, so the lower branches stay bare
    tips = [co for depth, pts in branches if depth >= 7 for co, _ in pts]
    z_all = np.array([c.z for c in tips])
    z_lo, z_top = float(np.percentile(z_all, 5)), float(np.percentile(z_all, 99.5))
    centers, var = [], []
    for co in tips:
        h = min(max((co.z - z_lo) / (z_top - z_lo), 0), 1)
        p = min(max((h - 0.3) / 0.4, 0), 1)
        p = p * p * (3 - 2 * p)
        for _ in range(int(17 * p + random.random())):
            off = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 0.7))) * 0.9
            centers.append(co + off)
            var.append(random.random() ** 1.4)
    n_crown = len(centers)
    for _ in range(700):
        a = random.uniform(0, 2 * math.pi)
        rr = random.uniform(2, 26)
        centers.append(Vector((math.cos(a) * rr, math.sin(a) * rr, random.uniform(0.5, z_top * 0.85))))
        var.append(random.uniform(0.5, 1.0))
    N = len(centers)
    C = np.array([c[:] for c in centers], dtype=np.float32)
    U = np.random.normal(size=(N, 3)).astype(np.float32)
    U /= np.linalg.norm(U, axis=1, keepdims=True)
    V = np.cross(U, np.random.normal(size=(N, 3)).astype(np.float32))
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    L = np.random.uniform(0.13, 0.27, size=(N, 1)).astype(np.float32)
    L[n_crown:] *= 1.5
    verts = np.empty((N, 4, 3), dtype=np.float32)
    verts[:, 0] = C + U * L * 0.5
    verts[:, 1] = C + V * L * 0.22
    verts[:, 2] = C - U * L * 0.5
    verts[:, 3] = C - V * L * 0.22
    me = bpy.data.meshes.new("ErdtreeLeaves")
    me.vertices.add(N * 4)
    me.vertices.foreach_set("co", verts.reshape(-1))
    me.loops.add(N * 4)
    me.loops.foreach_set("vertex_index", np.arange(N * 4, dtype=np.int32))
    me.polygons.add(N)
    me.polygons.foreach_set("loop_start", np.arange(0, N * 4, 4, dtype=np.int32))
    me.polygons.foreach_set("loop_total", np.full(N, 4, dtype=np.int32))
    me.update(calc_edges=True)
    attr = me.color_attributes.new("var", "FLOAT_COLOR", "POINT")
    v = np.repeat(np.array(var, dtype=np.float32), 4)
    attr.data.foreach_set("color", np.stack([v, v, v, np.ones_like(v)], axis=1).reshape(-1))
    leaves = bpy.data.objects.new("Erdtree Leaves", me)
    leaves.parent = wood
    col.objects.link(leaves)
    me.materials.append(_leaf_material())

    # mist volume
    x0, x1, y0, y1, z0, z1 = -70, 70, -26, 60, -0.2, z_top + 14
    vs = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    fs = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mme = bpy.data.meshes.new("ErdtreeMist")
    mme.from_pydata(vs, [], fs)
    mist = bpy.data.objects.new("Erdtree Mist", mme)
    mist.display_type = "WIRE"
    col.objects.link(mist)
    mme.materials.append(_mist_material())

    # light shafts from above the crown
    sun_data = bpy.data.lights.new("Erdtree Shafts", "SUN")
    sun_data.energy = 7.0
    sun_data.color = (1.0, 0.86, 0.5)
    sun_data.angle = math.radians(1.5)
    sun = bpy.data.objects.new("Erdtree Shafts", sun_data)
    sun.rotation_euler = (math.radians(-16), math.radians(7), 0)
    sun.location = (0, 0, z_top + 20)
    col.objects.link(sun)

    # key light raking across from the front left: this is what makes the bark's relief read
    key_data = bpy.data.lights.new("Erdtree Key", "SUN")
    key_data.energy = 4.8
    key_data.color = (1.0, 0.9, 0.66)
    key_data.angle = math.radians(4)
    key = bpy.data.objects.new("Erdtree Key", key_data)
    key.rotation_euler = Vector((0.88, 0.42, -0.3)).to_track_quat("-Z", "Y").to_euler()
    key.location = (-30, -40, z_top)
    col.objects.link(key)

    # world and camera
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0015, 0.004, 0.0035, 1)
    z_a, z_b = -1.2, z_top + 2.5
    H = z_b - z_a
    cam_data = bpy.data.cameras.new("Erdtree Camera")
    cam_data.lens = 85
    cam_data.sensor_fit = "VERTICAL"
    cam_data.sensor_height = 36
    cam_data.clip_end = 1000
    cam = bpy.data.objects.new("Erdtree Camera", cam_data)
    cam.location = (0, -(H / 2) / math.tan(math.atan(18 / 85)), (z_a + z_b) / 2)
    cam.rotation_euler = (math.radians(90), 0, 0)
    col.objects.link(cam)
    scene.camera = cam

    # the default cube and lamp would show up in the render: hide them, don't delete
    for name in ("Cube", "Light"):
        ob = bpy.data.objects.get(name)
        if ob:
            ob.hide_render = True
            ob.hide_set(True)

    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1440, 3360, 100
    scene.cycles.samples = 192
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.cycles.volume_bounces = 1
    try:
        scene.view_settings.view_transform = "AgX"
    except Exception:
        pass
    return {"branches": len(branches), "roots": len(roots), "leaves": N, "body_vertices": body_verts,
            "height": round(H, 1), "seconds": round(time.time() - t0, 1)}
