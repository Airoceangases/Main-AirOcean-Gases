"""Vehicles and motion for the Airocean hero scene: trucks, ships, the quay crane, water.

Every vehicle is built once at the origin facing +X into its own Batch, turned into
objects parented to an Empty, then parked or driven along a lane path. Motion is baked
as one keyframe per frame so the video loops exactly: a lane carries `count` identical
vehicles spaced evenly, each taking `loops` video loops to drive the whole path
(count is a multiple of loops), so after one loop every vehicle stands where another
one stood at the start.
"""
import math
from dataclasses import dataclass

import bpy
from mathutils import Vector

import scene_logos as logo
from scene_props import Batch, box, cyl, extrude_poly, use_batch

ROAD_Z = 0.03                                   # wheels sit on the road surface
LIVERY = {'hy': 'orange', 'airocean': 'blue'}   # Hongyuan tankers are orange-striped (plant photos)
SHIP_LENGTH, SHIP_WIDTH, SHIP_DECK = 19.0, 5.0, 1.2
# Trucks are modelled at a chunky toy scale; shrunk so they sit inside one lane and stay
# smaller than the buildings at the zoomed-out framing.
TRUCK_SCALE = 0.7
TRUCK_REAR = 3.5 * TRUCK_SCALE                  # origin to rear bumper (chassis ends at x = -3.5)

_ctx = {}


def init(mats: dict, collection) -> None:
    _ctx.update(mats=mats, col=collection)


def _instance(name: str, build) -> bpy.types.Object:
    """Build a model into its own batch and parent the resulting objects (and decals) to an Empty."""
    batch = Batch()
    with use_batch(batch), logo.capture() as decals:
        build()
    root = bpy.data.objects.new(name, None)
    _ctx['col'].objects.link(root)
    for ob in batch.finalize(_ctx['mats'], _ctx['col'], prefix=f'{name}.') + decals:
        ob.parent = root
    return root


# ── Models (local frame: forward +X, ground / waterline at z = 0) ─────────
def _cab(livery: str) -> None:
    box('white', 2.4, 0, 0.4, 1.5, 1.7, 1.9)                 # taller than the load: always visible
    box(livery, 2.4, 0, 1.0, 1.52, 1.72, 0.2)
    box('glass', 3.16, 0, 1.45, 0.05, 1.45, 0.6)              # windscreen
    for s in (-1, 1):
        box('glass', 2.65, s * 0.86, 1.5, 0.7, 0.05, 0.5)     # side windows
    box('dark', 3.16, 0, 0.45, 0.06, 1.5, 0.3)                # bumper


def _wheels(xs: tuple) -> None:
    for x in xs:
        for s in (-1, 1):
            cyl('dark', x, s * 0.72, 0.36, 0.36, 0.26, axis='Y', segs=16)


def _tanker(brand: str) -> None:
    livery = LIVERY[brand]
    box('dark', -0.3, 0, 0.3, 6.4, 1.3, 0.2)
    _cab(livery)
    cyl('white', -1.1, 0, 1.32, 0.72, 4.6, axis='X')
    for x in (-3.0, 0.8):
        cyl(livery, x, 0, 1.32, 0.74, 0.22, axis='X')
    for s in (-1, 1):
        logo.on_flank(brand, (-1.1, 0, 1.32), (0, s, 0), 0.72, 2.0, lift=math.radians(15))
    _wheels((2.5, -1.6, -2.6))


def _box_truck(brand: str) -> None:
    livery = LIVERY[brand]
    box('dark', -0.3, 0, 0.3, 6.2, 1.3, 0.2)
    _cab(livery)
    box('white', -1.0, 0, 0.55, 4.6, 1.8, 2.0)
    box(livery, -1.0, 0, 0.55, 4.62, 1.82, 0.16)
    for s in (-1, 1):
        logo.on_face(brand, (-1.0, s * 0.9, 1.65), (0, s, 0), 3.0)
    _wheels((2.5, -1.7, -2.7))


def _ship(wake: bool) -> None:
    l2, w2, deck = SHIP_LENGTH / 2, SHIP_WIDTH / 2, SHIP_DECK
    outline = [(-l2, -w2), (l2 - 3.6, -w2), (l2, 0), (l2 - 3.6, w2), (-l2, w2)]
    extrude_poly('navy', [(x, y, -0.6) for x, y in outline], (0, 0, 1.5))
    extrude_poly('white', [(x, y, 0.9) for x, y in outline], (0, 0, 0.3))
    box('white', -l2 + 1.6, 0, deck, 2.2, SHIP_WIDTH - 0.6, 2.6)
    box('glass', -l2 + 2.72, 0, deck + 1.8, 0.06, SHIP_WIDTH - 0.9, 0.45)
    box('white', -l2 + 1.6, 0, deck + 2.6, 1.6, SHIP_WIDTH - 1.4, 0.8)
    cyl('blue', -l2 + 0.8, 0, deck + 2.6, 0.35, 1.5)
    _ship_cargo(-l2 + 3.4, deck)
    if wake:
        for side in (-1, 1):
            streak = [(-l2, side * (w2 - 0.6), 0.01), (-l2, side * (w2 - 0.25), 0.01),
                      (-l2 - 6.5, side * (w2 + 0.9), 0.01)]
            extrude_poly('foam', streak, (0, 0, 0.02))


def _ship_cargo(x_start: float, deck: float) -> None:
    ys = (-1.65, -0.55, 0.55, 1.65)
    palette = ('blue', 'white', 'steel', 'blue', 'white')
    for r in range(4):
        x = x_start + 1.5 + r * 2.85
        for c, y in enumerate(ys):
            if r == 1 and c in (1, 2):                        # an ISO tank amid the boxes
                cyl('white', x, y, deck + 0.6, 0.5, 2.6, axis='X')
                box('steel', x, y, deck, 2.7, 1.0, 0.12)
                continue
            stack = 2 if (r + c) % 3 else 1
            branded = c in (0, len(ys) - 1) and r in (0, 2)  # outer containers carry the logo
            for s in range(stack):
                colour = 'white' if branded and s == stack - 1 else palette[(r * 2 + c + s) % len(palette)]
                box(colour, x, y, deck + s * 1.0, 2.65, 1.02, 0.98)
            if branded:
                sign = -1 if c == 0 else 1
                logo.on_face('airocean', (x, y + sign * 0.51, deck + (stack - 1) + 0.49), (0, sign, 0), 2.3)


MODELS = {
    'hy': lambda: _tanker('hy'),
    'hy_box': lambda: _box_truck('hy'),         # Hongyuan warehouse truck
    'airocean': lambda: _box_truck('airocean'),
    'ship': lambda: _ship(wake=True),
    'ship_docked': lambda: _ship(wake=False),
}
TRUCKS = ('hy', 'hy_box', 'airocean')
_counter = {}


def spawn(kind: str) -> bpy.types.Object:
    n = _counter[kind] = _counter.get(kind, 0) + 1
    root = _instance(f'{kind}_{n:02d}', MODELS[kind])
    if kind in TRUCKS:
        root.scale = (TRUCK_SCALE,) * 3
    return root


def park(kind: str, x: float, y: float, heading_deg: float, z: float = ROAD_Z) -> bpy.types.Object:
    root = spawn(kind)
    root.location = (x, y, z)
    root.rotation_euler = (0, 0, math.radians(heading_deg))
    return root


def docked_ship(x: float, y: float, z: float, heading_deg: float = 90.0) -> Vector:
    """Moor a ship; return the world position of its hotspot (above the cargo)."""
    park('ship_docked', x, y, heading_deg, z)
    a = math.radians(heading_deg)
    return Vector((x + 2.0 * math.cos(a), y + 2.0 * math.sin(a), z + SHIP_DECK + 2.6))


# ── Paths ─────────────────────────────────────────────────────────────────
class Path:
    """Polyline in plan with rounded corners; sample(s) returns (x, y, heading) for s in [0, 1)."""

    def __init__(self, points: list, radius: float = 2.5) -> None:
        self.points = _round_corners([Vector(p) for p in points], radius)
        self.lengths = [(b - a).length for a, b in zip(self.points, self.points[1:])]
        self.total = sum(self.lengths)

    def sample(self, s: float) -> tuple:
        d = (s % 1.0) * self.total
        last = len(self.lengths) - 1
        for i, (a, b, seg) in enumerate(zip(self.points, self.points[1:], self.lengths)):
            if d <= seg or i == last:
                p = a.lerp(b, min(d / seg, 1.0) if seg else 0.0)
                return p.x, p.y, math.atan2(b.y - a.y, b.x - a.x)
            d -= seg
        raise ValueError('empty path')


def _round_corners(pts: list, radius: float, steps: int = 8) -> list:
    out = [pts[0]]
    for prev, corner, nxt in zip(pts, pts[1:], pts[2:]):
        t1 = corner - (corner - prev).normalized() * radius
        t2 = corner + (nxt - corner).normalized() * radius
        for i in range(steps + 1):               # quadratic Bezier t1 -> corner -> t2
            t = i / steps
            out.append(t1 * (1 - t) ** 2 + corner * 2 * (1 - t) * t + t2 * t ** 2)
    out.append(pts[-1])
    return out


@dataclass(frozen=True)
class Lane:
    kind: str            # 'hy' tanker, 'airocean' box truck or 'ship'
    points: tuple        # plan polyline, ends off-screen
    count: int = 2       # identical vehicles spaced evenly along the path
    loops: int = 2       # video loops each vehicle needs for the whole path (count % loops == 0)
    phase: float = 0.0
    z: float = ROAD_Z


def populate(lanes: list) -> list:
    """Spawn every lane's vehicles; return (root, path, start offset, loops, z) movers."""
    movers = []
    for lane in lanes:
        if lane.count % lane.loops:
            raise ValueError(f'lane {lane.points}: count {lane.count} is not a multiple of loops {lane.loops}')
        path = Path(list(lane.points))
        for i in range(lane.count):
            movers.append((spawn(lane.kind), path, lane.phase + i / lane.count, lane.loops, lane.z))
    return movers


# ── Baking the loop ───────────────────────────────────────────────────────
def bake(movers: list, frames: int, crane=None, water_nodes: tuple = ()) -> None:
    """One keyframe per frame for every mover, the crane trolley and the water phase."""
    for f in range(frames):
        t = f / frames
        for root, path, start, loops, z in movers:
            x, y, heading = path.sample(start + t / loops)
            root.location = (x, y, z)
            root.rotation_euler = (0, 0, heading)
            root.keyframe_insert('location', frame=f)
            root.keyframe_insert('rotation_euler', frame=f)
        if crane:
            trolley, x_ship, x_quay = crane
            trolley.location.x = x_ship + (x_quay - x_ship) * (0.5 - 0.5 * math.cos(2 * math.pi * t))
            trolley.keyframe_insert('location', frame=f)
        for node, turns in water_nodes:
            node.inputs['Phase Offset'].default_value = 2 * math.pi * turns * t
            node.inputs['Phase Offset'].keyframe_insert('default_value', frame=f)


def crane_trolley(x: float, y: float, z: float) -> bpy.types.Object:
    """Trolley riding the quay crane's boom, carrying a container on its cables."""
    def build() -> None:
        # Cables are short enough that the lifted box clears the two-high stacks on the moored
        # ship (deck tops out ~2.7 above datum; the trolley rides at ~6.3, the box bottom at ~2.9).
        # The box lies along Y, like the containers on the moored ship.
        box('white', 0, 0, 0, 1.6, 1.4, 0.8)
        for s in (-1, 1):
            box('dark', s * 0.35, 0, -2.2, 0.06, 0.06, 2.2)    # hoist cables
        box('steel', 0, 0, -2.45, 1.1, 2.9, 0.25)              # spreader
        box('blue', 0, 0, -3.43, 1.02, 2.65, 0.98)             # the container it lifts
    root = _instance('crane_trolley', build)
    root.location = (x, y, z)
    return root
