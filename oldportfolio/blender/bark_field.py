"""Numpy helpers for the bark: smooth noise for the trunk's slow folds, and a sampler for the bark scan.

Kept free of Blender imports so it can be tested with plain Python.
"""
import itertools
import numpy as np

_M1, _M2, _M3 = np.uint32(0x8DA6B343), np.uint32(0xD8163841), np.uint32(0xCB1AB31F)


def _hash(ix, iy, iz, seed):
    """Integer lattice point -> well-mixed uint32."""
    with np.errstate(over="ignore"):
        h = (ix.astype(np.uint32) * _M1) ^ (iy.astype(np.uint32) * _M2) ^ (iz.astype(np.uint32) * _M3)
        h ^= np.uint32((seed * 0x9E3779B9) & 0xFFFFFFFF)
        h = h ^ (h >> np.uint32(15))
        h = h * np.uint32(0x2C1B3C6D)
        h = h ^ (h >> np.uint32(12))
        h = h * np.uint32(0x297A2D39)
        return h ^ (h >> np.uint32(15))


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def vnoise(p, seed=0):
    """Smooth value noise in [0, 1] at points p (N, 3)."""
    pi = np.floor(p).astype(np.int64)
    f = (p - pi).astype(np.float32)
    u = f * f * f * (f * (f * 6 - 15) + 10)
    out = np.zeros(len(p), dtype=np.float32)
    for dx, dy, dz in itertools.product((0, 1), repeat=3):
        w = (u[:, 0] if dx else 1 - u[:, 0]) * (u[:, 1] if dy else 1 - u[:, 1]) * (u[:, 2] if dz else 1 - u[:, 2])
        h = _hash(pi[:, 0] + dx, pi[:, 1] + dy, pi[:, 2] + dz, seed)
        out += w * ((h >> np.uint32(8)).astype(np.float32) / np.float32(1 << 24))
    return out


def fbm(p, octaves=4, seed=0, gain=0.5):
    """Several octaves of vnoise, still in [0, 1]."""
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total = total + amp * vnoise(p * (2.0 ** o) + o * 17.13, seed + o)
        norm += amp
        amp *= gain
    return total / norm


class HeightMap:
    """A tiling height image with smaller copies of itself (mips), sampled at arbitrary points.

    The mesh is far coarser than the scan, so each vertex reads from the copy whose pixels are
    about the size of the mesh's spacing there; reading the full-size scan would just be noise.
    """

    def __init__(self, pixels):
        self.levels = [np.asarray(pixels, dtype=np.float32)]
        while self.levels[-1].shape[0] > 16:
            a = self.levels[-1]
            self.levels.append((a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) * 0.25)

    @staticmethod
    def _bilinear(a, u, v):
        res = a.shape[0]
        x = (u % 1.0) * res - 0.5
        y = (v % 1.0) * res - 0.5
        x0 = np.floor(x).astype(np.int64)
        y0 = np.floor(y).astype(np.int64)
        fx = (x - x0).astype(np.float32)
        fy = (y - y0).astype(np.float32)
        x0 %= res
        y0 %= res
        x1 = (x0 + 1) % res
        y1 = (y0 + 1) % res
        return (a[y0, x0] * (1 - fx) + a[y0, x1] * fx) * (1 - fy) + (a[y1, x0] * (1 - fx) + a[y1, x1] * fx) * fy

    def sample(self, u, v, level):
        """Height at (u, v), blended between the two mips either side of the fractional level."""
        level = np.clip(level, 0, len(self.levels) - 1.001)
        lo = np.floor(level).astype(np.int64)
        t = (level - lo).astype(np.float32)
        out = np.zeros(len(u), dtype=np.float32)
        for l in np.unique(lo):
            m = lo == l
            a = self._bilinear(self.levels[l], u[m], v[m])
            b = self._bilinear(self.levels[l + 1], u[m], v[m])
            out[m] = a * (1 - t[m]) + b * t[m]
        return out
