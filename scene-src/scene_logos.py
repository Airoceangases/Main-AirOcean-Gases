"""Logo decals for the Airocean hero scene.

Brands:
    'hy'        Hongyuan product logo (blue HY swoosh)          -> assets/hy-logo.png
    'airocean'  Airocean Gases logo (colour mark + dark text)   -> assets/airocean-logo.png

Each decal is a thin image-textured mesh floated just off its surface. Static props
place decals facing the camera (which sits on the +X / -Y side); vehicles place them
on both flanks in their own local frame and collect them with capture() so they can
be parented to the moving vehicle.
"""
import math
import os
from contextlib import contextmanager

import bpy
from mathutils import Vector

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
LOGO_FILES = {'hy': 'hy-logo.png', 'airocean': 'airocean-logo.png'}
OFFSET = 0.025                 # lift off the surface to avoid z-fighting
FACE_CAMERA = -math.pi / 4     # plan angle of the direction pointing at the camera
UP = Vector((0, 0, 1))
FACING_NORMALS = {'S': Vector((0, -1, 0)), 'E': Vector((1, 0, 0))}

_materials = {}
_aspect = {}
_captures = []                 # stack of lists collecting decals made inside capture()


def load_logos() -> None:
    for brand, name in LOGO_FILES.items():
        img = bpy.data.images.load(os.path.join(ASSET_DIR, name), check_existing=True)
        _aspect[brand] = img.size[0] / img.size[1]
        _materials[brand] = _material(brand, img)


def _material(brand: str, img):
    m = bpy.data.materials.new(f'logo_{brand}')
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    tex.extension = 'CLIP'
    tex.interpolation = 'Cubic'
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
    bsdf.inputs['Roughness'].default_value = 0.45
    return m


@contextmanager
def capture():
    """Collect every decal created inside the block (e.g. to parent them to a vehicle)."""
    made = []
    _captures.append(made)
    try:
        yield made
    finally:
        _captures.pop()


def _add(brand: str, verts: list, faces: list, uvs: list):
    me = bpy.data.meshes.new(f'logo_{brand}')
    me.from_pydata([tuple(v) for v in verts], [], faces)
    layer = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        layer.data[loop.index].uv = uvs[loop.vertex_index]
    me.materials.append(_materials[brand])
    ob = bpy.data.objects.new(f'logo_{brand}', me)
    bpy.context.scene.collection.objects.link(ob)
    if _captures:
        _captures[-1].append(ob)
    return ob


def height_for(brand: str, width: float) -> float:
    return width / _aspect[brand]


def _reading_direction(normal: Vector) -> Vector:
    """Left-to-right direction for a viewer facing a surface with this outward normal."""
    return (-normal).cross(UP).normalized()


def on_face(brand: str, centre: tuple, normal: tuple, width: float) -> None:
    """Flat logo centred on a vertical face with the given outward normal."""
    n = Vector(normal).normalized()
    right = _reading_direction(n)
    h = height_for(brand, width)
    c = Vector(centre) + n * OFFSET
    corners = [c + right * sx * width / 2 + UP * sz * h / 2
               for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    _add(brand, corners, [(0, 1, 2, 3)], [(0, 0), (1, 0), (1, 1), (0, 1)])


def on_wall(brand: str, x: float, y: float, z: float, width: float, facing: str = 'S') -> None:
    """Flat logo centred at (x, y, z) on a wall facing -Y ('S') or +X ('E')."""
    on_face(brand, (x, y, z), FACING_NORMALS[facing], width)


def on_tank(brand: str, x: float, y: float, r: float, z: float, width: float, segs: int = 12) -> None:
    """Logo wrapped round a vertical cylinder of radius r, centred at height z on the camera side."""
    h = height_for(brand, width)
    half = width / (2 * r)
    verts, uvs = [], []
    for i in range(segs + 1):
        t = i / segs
        a = FACE_CAMERA - half + 2 * half * t
        p = Vector((x + (r + OFFSET) * math.cos(a), y + (r + OFFSET) * math.sin(a), z))
        verts += [p - UP * h / 2, p + UP * h / 2]
        uvs += [(t, 0), (t, 1)]
    _add(brand, verts, [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(segs)], uvs)


def on_flank(brand: str, centre: tuple, side: tuple, r: float, width: float,
             lift: float = 0.0, segs: int = 8) -> None:
    """Logo on the flank of a horizontal cylinder whose axis is perpendicular to `side`
    (the flank's outward horizontal normal); it reads along the axis and is tilted up by `lift`."""
    side_n = Vector(side).normalized()
    along = _reading_direction(side_n)
    h = height_for(brand, width)
    half = h / (2 * r)
    c = Vector(centre)
    verts, uvs = [], []
    for j in range(segs + 1):
        t = j / segs
        phi = lift - half + 2 * half * t
        n = side_n * math.cos(phi) + UP * math.sin(phi)
        for u in (0, 1):
            verts.append(c + along * (u - 0.5) * width + n * (r + OFFSET))
            uvs.append((u, t))
    _add(brand, verts, [(2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2) for j in range(segs)], uvs)


def on_lying_tank(brand: str, x: float, y: float, z: float, r: float, width: float, axis: str,
                  lift: float = math.radians(20)) -> None:
    """Static horizontal tank (axis 'X' or 'Y'): logo on the flank that faces the camera."""
    side = FACING_NORMALS['S'] if axis == 'X' else FACING_NORMALS['E']
    on_flank(brand, (x, y, z), side, r, width, lift)
