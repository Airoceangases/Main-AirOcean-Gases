"""Geometry batching and reusable props for the Airocean hero scene.

Primitives are built in small bmeshes and merged into one mesh per material (Batch);
props (buildings, tanks, cages ...) are composed from those primitives and place
their own brand logos through scene_logos. Static scenery goes into the shared batch
B; anything that moves is built inside use_batch() so it becomes separate objects.
"""
import logging
import math
from contextlib import contextmanager

import bmesh
import bpy
from mathutils import Matrix, Vector

import scene_logos as logo

log = logging.getLogger('scene')

Z0 = 0.12               # top of block pads; buildings stand here


# ── Geometry batching ─────────────────────────────────────────────────────
# Each primitive is built in its own small bmesh, then its raw geometry is
# appended to a per-material list. Running bmesh operators on one ever-growing
# bmesh is O(n) per operator (tool-flag layers are cleared mesh-wide), which
# made scene construction take ~20 minutes; this keeps it linear.
NO_BEVEL = ('water', 'ground', 'road', 'mark', 'foam')


class Batch:
    def __init__(self) -> None:
        self.geo = {}

    def add(self, key: str, bm) -> None:
        g = self.geo.setdefault(key, {'v': [], 'f': [], 'smooth': [], 'sharp': []})
        base = len(g['v'])
        bm.verts.index_update()
        g['v'].extend(v.co[:] for v in bm.verts)
        for f in bm.faces:
            g['f'].append([base + v.index for v in f.verts])
            g['smooth'].append(f.smooth)
        g['sharp'].extend((base + e.verts[0].index, base + e.verts[1].index)
                          for e in bm.edges if not e.smooth)
        bm.free()

    def finalize(self, mats: dict, col, prefix: str = '') -> list:
        """Turn the collected geometry into one object per material; return the objects."""
        objects = []
        for key, g in self.geo.items():
            name = f'{prefix}{key}'
            me = bpy.data.meshes.new(name)
            me.from_pydata(g['v'], [], g['f'])
            me.polygons.foreach_set('use_smooth', g['smooth'])
            _mark_sharp(me, g['sharp'])
            me.update()
            me.materials.append(mats[key])
            ob = bpy.data.objects.new(name, me)
            col.objects.link(ob)
            if key not in NO_BEVEL:
                bev = ob.modifiers.new('bevel', 'BEVEL')
                bev.width = 0.045
                bev.segments = 2
                bev.limit_method = 'ANGLE'
            objects.append(ob)
            if not prefix:
                log.info('mesh %-8s %7d verts', key, len(g['v']))
        self.geo = {}
        return objects


def _mark_sharp(me, pairs: list) -> None:
    if not pairs:
        return
    lookup = {tuple(sorted(e.vertices)): e.index for e in me.edges}
    flags = [False] * len(me.edges)
    for a, b in pairs:
        idx = lookup.get((a, b) if a < b else (b, a))
        if idx is not None:
            flags[idx] = True
    attr = me.attributes.get('sharp_edge') or me.attributes.new('sharp_edge', 'BOOLEAN', 'EDGE')
    attr.data.foreach_set('value', flags)


B = Batch()


@contextmanager
def use_batch(batch: Batch):
    """Route every primitive built inside the block into `batch` instead of the shared one."""
    global B
    previous, B = B, batch
    try:
        yield batch
    finally:
        B = previous


AXIS_ROT = {
    'Z': None,
    'X': Matrix.Rotation(math.pi / 2, 3, 'Y'),
    'Y': Matrix.Rotation(math.pi / 2, 3, 'X'),
}


def _place(bm, loc: tuple, rot=None) -> None:
    if rot is not None:
        bmesh.ops.rotate(bm, verts=bm.verts[:], cent=(0, 0, 0), matrix=rot)
    bmesh.ops.translate(bm, verts=bm.verts[:], vec=loc)


def box(mat: str, x: float, y: float, z: float, sx: float, sy: float, sz: float,
        rz: float = 0.0) -> None:
    """Axis-aligned box; (x, y) is the centre, z is the bottom."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts[:])
    _place(bm, (x, y, z + sz / 2), Matrix.Rotation(rz, 3, 'Z') if rz else None)
    B.add(mat, bm)


def cyl(mat: str, x: float, y: float, z: float, r: float, h: float, axis: str = 'Z',
        r2: float = None, segs: int = 40) -> None:
    """Cylinder/cone. Vertical: z is the bottom. Horizontal: z is the centre."""
    bm = bmesh.new()
    top = r if r2 is None else max(r2, 0.001)
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                          radius1=r, radius2=top, depth=h)
    for f in bm.faces:
        f.normal_update()
        f.smooth = abs(f.normal.z) < 0.7
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) == 2 and lf[0].smooth != lf[1].smooth:
            e.smooth = False
    loc = (x, y, z + h / 2) if axis == 'Z' else (x, y, z)
    _place(bm, loc, AXIS_ROT[axis])
    B.add(mat, bm)


def sphere(mat: str, x: float, y: float, z: float, r: float, squash: float = 1.0) -> None:
    """Sphere centred at (x, y, z)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=r)
    for f in bm.faces:
        f.smooth = True
    if squash != 1.0:
        bmesh.ops.scale(bm, vec=(1, 1, squash), verts=bm.verts[:])
    _place(bm, (x, y, z))
    B.add(mat, bm)


def extrude_poly(mat: str, pts: list, vec: tuple) -> None:
    """Closed prism from a planar outline `pts` (3D) swept along `vec`."""
    bm = bmesh.new()
    bot = [bm.verts.new(p) for p in pts]
    top = [bm.verts.new(Vector(p) + Vector(vec)) for p in pts]
    bm.faces.new(bot[::-1])
    bm.faces.new(top)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    B.add(mat, bm)


def strut(mat: str, p0: tuple, p1: tuple, w: float = 0.12) -> None:
    """Square-section beam of width w from p0 to p1 in any direction (lattice towers, braces)."""
    a, b = Vector(p0), Vector(p1)
    span = b - a
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(w, w, span.length), verts=bm.verts[:])
    _place(bm, tuple((a + b) / 2), Vector((0, 0, 1)).rotation_difference(span).to_matrix())
    B.add(mat, bm)


def gable(mat: str, x: float, y: float, z: float, sx: float, sy: float, rise: float,
          ridge: str = 'X', overhang: float = 0.25) -> None:
    sx2, sy2 = sx / 2 + overhang, sy / 2 + overhang
    if ridge == 'X':
        pts = [(x - sx2, y - sy2, z), (x - sx2, y + sy2, z), (x - sx2, y, z + rise)]
        extrude_poly(mat, pts, (2 * sx2, 0, 0))
    else:
        pts = [(x - sx2, y - sy2, z), (x + sx2, y - sy2, z), (x, y - sy2, z + rise)]
        extrude_poly(mat, pts, (0, 2 * sy2, 0))


# ── Reusable props ────────────────────────────────────────────────────────
def windows(x: float, y: float, sx: float, sy: float, z0: float, floors: int, fh: float,
            nx: int, ny: int, ww: float = 0.55, wh: float = 0.5, faces: str = 'SE') -> None:
    """Window grid on the camera-facing facades: 'S' = -Y, 'E' = +X."""
    for f in range(floors):
        zc = z0 + f * fh + (fh - wh) / 2
        if 'S' in faces:
            for i in range(nx):
                box('glass', x - sx / 2 + (i + 0.5) * sx / nx, y - sy / 2 - 0.03, zc, ww, 0.08, wh)
        if 'E' in faces:
            for j in range(ny):
                box('glass', x + sx / 2 + 0.03, y - sy / 2 + (j + 0.5) * sy / ny, zc, 0.08, ww, wh)


def flat_building(x: float, y: float, sx: float, sy: float, sz: float, floors: int = 2,
                  roof: str = 'blue', nx: int = None, ny: int = None) -> None:
    box('white', x, y, Z0, sx, sy, sz)
    box(roof, x, y, Z0 + sz, sx - 0.3, sy - 0.3, 0.1)
    if floors:
        windows(x, y, sx, sy, Z0 + 0.3, floors, (sz - 0.5) / floors,
                nx or max(2, int(sx / 1.1)), ny or max(2, int(sy / 1.1)))


def gable_building(x: float, y: float, sx: float, sy: float, sz: float, rise: float = 1.2,
                   ridge: str = 'X', doors: int = 0, logo_brand: str = None, logo_width: float = 0.0) -> None:
    """Pitched-roof shed. With a logo, the -Y facade carries the logo above the doors instead of windows."""
    box('white', x, y, Z0, sx, sy, sz)
    gable('blue', x, y, Z0 + sz, sx, sy, rise, ridge)
    windows(x, y, sx, sy, Z0 + sz * 0.55, 1, sz * 0.4, max(2, int(sx / 1.3)), max(2, int(sy / 1.3)),
            faces='E' if logo_brand else 'SE')
    for i in range(doors):
        box('dark', x - sx / 2 + (i + 0.5) * sx / doors, y - sy / 2 - 0.04, Z0, 1.1, 0.08, 1.4)
    if logo_brand:
        door_top = Z0 + 1.4 if doors else Z0
        logo.on_wall(logo_brand, x, y - sy / 2, (door_top + Z0 + sz) / 2, logo_width, 'S')


def tree(x: float, y: float, s: float = 1.0) -> None:
    cyl('white', x, y, Z0, 0.07 * s, 0.4 * s, segs=10)
    cyl('tree', x, y, Z0 + 0.3 * s, 0.42 * s, 1.25 * s, r2=0.0, segs=16)


def tree_row(x0: float, y0: float, x1: float, y1: float, n: int, hedge: bool = True) -> None:
    for i in range(n):
        t = i / max(n - 1, 1)
        tree(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
    if hedge:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        lx, ly = abs(x1 - x0) + 0.6, abs(y1 - y0) + 0.6
        box('grass', cx, cy, Z0, max(lx, 0.6), max(ly, 0.6), 0.06)


def bottle(x: float, y: float, cap: str, z: float = Z0, s: float = 1.0) -> None:
    cyl('white', x, y, z, 0.17 * s, 0.95 * s, segs=14)
    sphere('white', x, y, z + 0.95 * s, 0.17 * s)
    cyl(cap, x, y, z + 1.05 * s, 0.09 * s, 0.18 * s, segs=10)


GAS_CAPS = ('kr', 'xe', 'ne', 'he')


def bottle_grid(x: float, y: float, cols: int, rows: int, gap: float = 0.42, z: float = Z0,
                caps: tuple = GAS_CAPS) -> None:
    for i in range(cols):
        for j in range(rows):
            bottle(x + (i - (cols - 1) / 2) * gap, y + (j - (rows - 1) / 2) * gap,
                   caps[(i + j) % len(caps)], z)


def cage(x: float, y: float, cap: str) -> None:
    box('dark', x, y, Z0, 1.5, 1.5, 0.12)
    bottle_grid(x, y, 3, 3, gap=0.42, z=Z0 + 0.12, caps=(cap,))
    for dx in (-0.7, 0.7):
        for dy in (-0.7, 0.7):
            box('steel', x + dx, y + dy, Z0, 0.07, 0.07, 1.45)
    box('steel', x, y - 0.7, Z0 + 1.4, 1.5, 0.07, 0.07)
    box('steel', x + 0.7, y, Z0 + 1.4, 0.07, 1.5, 0.07)


def cryo_tank(x: float, y: float, r: float, h: float, band: bool = True, brand: str = None) -> None:
    cyl('white', x, y, Z0, r, h)
    sphere('white', x, y, Z0 + h, r, squash=0.45)
    if band:
        cyl('blue', x, y, Z0 + h * 0.72, r + 0.02, 0.35)
    if brand:
        logo.on_tank(brand, x, y, r, Z0 + h * 0.42, r * 1.3)


def storage_tank(x: float, y: float, r: float, h: float, band: str = 'blue', brand: str = None) -> None:
    """Flat-bottom LIN/LOX/LAR storage tank on a plinth, as in the Hongyuan photos."""
    cyl('steel', x, y, Z0, r * 0.92, 0.5)
    cyl('white', x, y, Z0 + 0.5, r, h)
    sphere('white', x, y, Z0 + 0.5 + h, r, squash=0.12)
    cyl(band, x, y, Z0 + 0.5 + h * 0.8, r + 0.02, 0.16)
    cyl('steel', x, y, Z0 + 0.5 + h + 0.35, r + 0.03, 0.06)
    for k in range(12):
        a = k * math.pi / 6
        box('steel', x + math.cos(a) * r, y + math.sin(a) * r, Z0 + 0.5 + h, 0.05, 0.05, 0.4)
    if brand:
        logo.on_tank(brand, x, y, r, Z0 + 0.5 + h * 0.5, r * 1.2)


def cold_box_tower(x: float, y: float, w: float, h: float, side: str = 'E', logo_brand: str = None) -> None:
    """Slender cold-box column with stepped ladder platforms on one side (logo on the clear face)."""
    box('white', x, y, Z0, w, w, h)
    box('white', x, y, Z0 + h, w * 0.6, w * 0.6, 0.9)
    for k in range(1, int(h / 1.5) + 1):
        z = Z0 + k * 1.5
        if side == 'E':
            box('steel', x + w / 2 + 0.3, y, z, 0.6, w + 0.2, 0.08)
            box('steel', x + w / 2 + 0.58, y, z, 0.04, w + 0.2, 0.4)
        else:
            box('steel', x, y - w / 2 - 0.3, z, w + 0.2, 0.6, 0.08)
            box('steel', x, y - w / 2 - 0.58, z, w + 0.2, 0.04, 0.4)
    box('steel', x, y, Z0 + h + 0.9, w * 0.8, w * 0.8, 0.06)
    if logo_brand:
        if side == 'E':
            logo.on_wall(logo_brand, x, y - w / 2, Z0 + h - 1.5, w * 0.82, 'S')
        else:
            logo.on_wall(logo_brand, x + w / 2, y, Z0 + h - 1.5, w * 0.82, 'E')


def column(x: float, y: float, r: float, h: float, rings: int = 3) -> None:
    cyl('white', x, y, Z0, r, h)
    sphere('white', x, y, Z0 + h, r, squash=0.5)
    for k in range(1, rings + 1):
        cyl('blue', x, y, Z0 + h * k / (rings + 1), r + 0.22, 0.1)


def cooling_tower(x: float, y: float, sx: float, sy: float) -> None:
    box('cooling', x, y, Z0, sx, sy, 1.3)
    for i in range(int(sx / 1.1)):
        cyl('dark', x - sx / 2 + 0.55 + i * 1.1, y, Z0 + 1.3, 0.4, 0.12, segs=20)


def iso_tank(x: float, y: float, axis: str = 'X', brand: str = None) -> None:
    lx, ly = (3.0, 1.2) if axis == 'X' else (1.2, 3.0)
    box('steel', x, y, Z0, lx, ly, 0.12)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box('steel', x + sx * (lx / 2 - 0.06), y + sy * (ly / 2 - 0.06), Z0, 0.1, 0.1, 1.25)
    cyl('white', x, y, Z0 + 0.68, 0.52, 2.7, axis=axis)
    if brand:
        logo.on_lying_tank(brand, x, y, Z0 + 0.68, 0.52, 1.5, axis)


# ── Industry props: each customer industry gets an object people recognise ──
def lattice_pylon(x: float, y: float, h: float = 10.5, base: float = 2.2, top: float = 0.7,
                  arms: tuple = ((7.4, 2.4), (9.2, 1.8))) -> list:
    """Steel lattice transmission tower with cross arms along Y and hanging insulator strings.
    Returns the points where the conductors attach, one per insulator."""
    def at(sx: int, sy: int, z: float) -> tuple:     # corner of the tapered shaft at height z
        half = (base + (top - base) * z / h) / 2
        return x + sx * half, y + sy * half, Z0 + z

    corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    for sx, sy in corners:
        strut('steel', at(sx, sy, 0.0), at(sx, sy, h), 0.16)
    levels = (0.0, 0.26 * h, 0.5 * h, 0.7 * h, 0.86 * h, h)
    for z0, z1 in zip(levels, levels[1:]):
        for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
            strut('steel', at(ax, ay, z1), at(bx, by, z1), 0.1)          # ring
            strut('steel', at(ax, ay, z0), at(bx, by, z1), 0.1)          # X brace
            strut('steel', at(bx, by, z0), at(ax, ay, z1), 0.1)
    hangs = []
    for z, reach in arms:
        box('steel', x, y, Z0 + z, 0.18, 2 * reach, 0.18)
        for s in (-1, 1):
            cyl('white', x, y + s * reach, Z0 + z - 0.9, 0.09, 0.9, segs=10)   # insulator string
            hangs.append((x, y + s * reach, Z0 + z - 0.9))
    cyl('steel', x, y, Z0 + h, 0.16, 1.2, r2=0.02, segs=8)                    # earth-wire peak
    return hangs


def transformer(x: float, y: float) -> None:
    """Power transformer: tank with radiator fins toward the camera, conservator and three bushings."""
    box('steel', x, y, Z0, 2.0, 1.4, 1.7)
    for i in range(6):
        box('steel', x - 0.75 + i * 0.3, y - 0.95, Z0 + 0.2, 0.07, 0.5, 1.3)       # radiator fins
    cyl('steel', x - 0.2, y + 0.45, Z0 + 2.15, 0.26, 1.5, axis='X', segs=20)     # conservator
    for k in (-0.6, 0.0, 0.6):
        cyl('white', x + k, y - 0.1, Z0 + 1.7, 0.1, 0.9, segs=12)
        for d in range(3):
            cyl('white', x + k, y - 0.1, Z0 + 1.85 + d * 0.25, 0.17, 0.05, segs=12)   # bushing sheds


def framed_window(x: float, y: float, z: float, w: float = 1.4, h: float = 1.8) -> None:
    """Insulated-glass window unit facing the camera (-Y): white frame, blue glass, cross mullion."""
    f = 0.12
    box('glass', x, y, z + f / 2, w - f, 0.06, h - f)
    for dz in (0.0, h - f):
        box('white', x, y - 0.02, z + dz, w, 0.1, f)                   # sill and head
    for dx in (-(w - f) / 2, (w - f) / 2):
        box('white', x + dx, y - 0.02, z, f, 0.1, h)                   # jambs
    box('white', x, y - 0.03, z + h / 2 - 0.04, w - f, 0.1, 0.08)      # transom
    box('white', x, y - 0.03, z, 0.08, 0.1, h)                         # mullion


def nmr_magnet(x: float, y: float, z: float = Z0) -> None:
    """NMR spectrometer: the big white helium-cooled magnet with blue bands, on a low platform."""
    box('steel', x, y, z, 1.9, 1.9, 0.18)
    cyl('white', x, y, z + 0.18, 0.75, 1.8, segs=32)
    sphere('white', x, y, z + 1.98, 0.75, squash=0.3)
    for zz in (0.55, 1.3):
        cyl('blue', x, y, z + 0.18 + zz, 0.78, 0.12, segs=32)
    for dx in (-0.25, 0.25):
        cyl('steel', x + dx, y, z + 2.1, 0.1, 0.45, segs=10)           # helium fill turrets


def lab_instrument(x: float, y: float, z: float, sx: float, sy: float, sz: float) -> None:
    """Benchtop analyser (GC-MS, ICP-MS, LC): white case, blue display and trim on its front."""
    box('white', x, y, z, sx, sy, sz)
    box('glass', x - sx * 0.15, y - sy / 2 - 0.02, z + sz * 0.45, sx * 0.45, 0.04, sz * 0.35)
    box('blue', x, y - sy / 2 - 0.02, z + sz - 0.12, sx, 0.04, 0.08)


def lamp_post(x: float, y: float, h: float = 2.6) -> None:
    box('steel', x, y, Z0, 0.08, 0.08, h)
    box('steel', x + 0.25, y, Z0 + h - 0.08, 0.5, 0.08, 0.08)
    sphere('lamp', x + 0.45, y, Z0 + h - 0.16, 0.16)


def rocket(x: float, y: float, z: float, r: float = 0.95, h: float = 10.0) -> float:
    """Launch vehicle standing at (x, y, z): white core with blue bands, a nose fairing and two
    strap-on boosters left and right of it as the camera sees it. Returns its height."""
    nose = 2.6
    cyl('white', x, y, z, r, h)
    cyl('white', x, y, z + h, r, nose, r2=0.0)
    cyl('dark', x, y, z + h * 0.8, r + 0.02, 0.2)                     # interstage
    for zz in (h * 0.3, h * 0.55):
        cyl('blue', x, y, z + zz, r + 0.02, 0.4)
    d = (r + 0.51) / math.sqrt(2)                                     # boosters on the screen's left/right
    for s in (-1, 1):
        bx, by = x + s * d, y + s * d
        cyl('white', bx, by, z, 0.5, 6.2)
        cyl('white', bx, by, z + 6.2, 0.5, 1.3, r2=0.0)
        cyl('blue', bx, by, z + 4.4, 0.52, 0.3)
    return h + nose


def launch_tower(x: float, y: float, z: float, h: float, w: float = 1.5) -> None:
    """Service tower beside the pad: four steel legs, a deck every 1.8 units, cross bracing on the
    camera-facing faces, a blue top deck and a lightning mast."""
    hw = w / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            box('steel', x + sx * hw, y + sy * hw, z, 0.16, 0.16, h)
    decks = [z + 1.8 * k for k in range(1, int(h / 1.8) + 1)]
    for zz in decks:
        for s in (-1, 1):
            box('steel', x, y + s * hw, zz, w, 0.12, 0.12)
            box('steel', x + s * hw, y, zz, 0.12, w, 0.12)
    for z0, z1 in zip([z] + decks, decks):
        strut('steel', (x - hw, y - hw, z0), (x + hw, y - hw, z1), 0.09)      # south face
        strut('steel', (x + hw, y - hw, z0), (x + hw, y + hw, z1), 0.09)      # east face
    box('blue', x, y, z + h, w + 0.4, w + 0.4, 0.25)
    cyl('steel', x, y, z + h + 0.25, 0.06, 2.6, segs=8)


def sphere_tank(x: float, y: float, r: float) -> None:
    """Spherical cryogenic propellant tank on four legs, banded at the equator."""
    for sx in (-1, 1):
        for sy in (-1, 1):
            box('steel', x + sx * r * 0.6, y + sy * r * 0.6, Z0, 0.16, 0.16, r * 1.3)
    sphere('white', x, y, Z0 + r * 1.9, r)
    cyl('blue', x, y, Z0 + r * 1.9 - 0.1, r + 0.02, 0.2)
