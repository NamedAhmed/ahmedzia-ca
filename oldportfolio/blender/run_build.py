"""Builds the tree from scratch and saves erdtree.blend next to this file.

Run:  blender --background --python run_build.py
"""
import bpy, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_erdtree

print("BUILT", build_erdtree.build(seed=2))
path = os.path.join(HERE, "erdtree.blend")
bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
bpy.ops.file.make_paths_relative()   # so the textures are found wherever the folder is moved
bpy.ops.wm.save_mainfile(compress=True)
print("SAVED", round(os.path.getsize(path) / 1e6, 1), "MB")
