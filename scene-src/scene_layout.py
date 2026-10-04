"""Ground, roads, blocks and static scenery of the Airocean hero scene.

Story, left to right: Hongyuan production in China (air separation, rare-gas
purification, automated filling, tank farm, tanker depot) -> a wide ocean channel ->
Airocean USA (HQ, Pennsylvania distribution centre) -> the six customer industries.
The camera gives these roughly 30 % / 20 % / 50 % of the frame.

The grid uses wide two-lane roads (vehicles keep right) and big blocks. Major plants
take a lot of two blocks along the channel (built over the cross street between them),
so the map has a clear hierarchy. Blocks without a story zone are filled by district:
the China side is an industrial estate around Hongyuan's plant (tank rows, production
halls, cylinder yards, green belts); the US side has a logistics belt along the port
(warehouses, plants) and a city further inland (offices, campuses, parks).
"""
import math
import random

import scene_logos as logo
import scene_vehicles as veh
from scene_props import (
    GAS_CAPS, Z0, bottle, box, cage, cold_box_tower, column, cooling_tower, cryo_tank, cyl,
    flat_building, framed_window, gable, gable_building, iso_tank, lab_instrument, lamp_post,
    lattice_pylon, launch_tower, nmr_magnet, rocket, sphere, sphere_tank, storage_tank, strut,
    transformer, tree, tree_row, windows,
)
from scene_vehicles import Lane

# ── Grid ──────────────────────────────────────────────────────────────────
WATER_Z = -0.5
CHANNEL = 9.5                          # half-width of the ocean channel: wide enough to read as sea
QUAY_W = 4.4                           # wharf strip between the channel and the first road
ROAD_W = 3.6                           # two lanes
LANE = 0.95                            # lane centre offset from the road centre line
PITCH = 18.0                           # road spacing: big blocks leave calm white space
PAD = PITCH - ROAD_W                   # block pad size
X0 = CHANNEL + QUAY_W + ROAD_W / 2     # first road centre line on each side
EXTENT = 200                           # ground reaches this far from the channel and along it
ROADS = 9                              # roads laid on each side (and cross streets each way)
BLOCKS_X, BLOCKS_Y = range(8), range(-12, 10)   # block indices scanned for visible filler
SQRT2 = math.sqrt(2)
VIS_MARGIN = 9.0
CN, US = -1, 1
# Cross street each side's turning truck drives along (beyond that side's road 1): lots are
# never merged across it.
TURN_ROAD = {CN: -1, US: 0}
INDUSTRY_PAD = 'industry'              # pale-blue lot surface marking the six customer industries

HOTSPOTS = {}
_window = {'u': (-80.0, 80.0), 'v': (-80.0, 80.0)}   # visible plan window, set by set_window()


def set_window(u_range: tuple, v_range: tuple) -> None:
    _window.update(u=u_range, v=v_range)


def uv(x: float, y: float) -> tuple:
    """Plan coords aligned with the camera: u grows right, v grows up-screen."""
    return (x + y) / SQRT2, (y - x) / SQRT2


def is_visible(x: float, y: float, margin: float = VIS_MARGIN) -> bool:
    u, v = uv(x, y)
    (u0, u1), (v0, v1) = _window['u'], _window['v']
    return u0 - margin < u < u1 + margin and v0 - margin < v < v1 + margin


def road_x(side: int, k: int) -> float:
    """Centre line of the k-th road running along Y on one side of the channel."""
    return side * (X0 + k * PITCH)


def road_y(k: int) -> float:
    """Centre line of the k-th road running along X."""
    return k * PITCH


def block(side: int, ix: int, iy: int) -> tuple:
    return side * (X0 + ROAD_W / 2 + PAD / 2 + ix * PITCH), PITCH / 2 + iy * PITCH


def lot(side: int, ix: int, iy: int, cells: int = 1) -> tuple:
    """Centre of a lot of `cells` blocks running along the channel from block (ix, iy)."""
    x, y = block(side, ix, iy)
    return x, y + (cells - 1) * PITCH / 2


def pad(x: float, y: float, mat: str = 'pad', cells: int = 1) -> None:
    """Raised lot surface; a multi-block lot also covers the cross streets inside it."""
    box(mat, x, y, 0, PAD, PAD + (cells - 1) * PITCH, Z0)


def industry_pad(x: float, y: float, cells: int = 1, inset: float = 0.45, line: float = 0.28) -> None:
    """Customer-industry lot: pale-blue surface framed by a thin blue line, so the six industries
    read as one highlighted group on the map."""
    pad(x, y, INDUSTRY_PAD, cells)
    lx, ly = PAD - 2 * inset, PAD + (cells - 1) * PITCH - 2 * inset
    for s in (-1, 1):
        box('blue', x, y + s * (ly - line) / 2, Z0, lx, line, 0.015)
        box('blue', x + s * (lx - line) / 2, y, Z0, line, ly, 0.015)


# ── Ground and roads ──────────────────────────────────────────────────────
def build_ground() -> None:
    for side in (CN, US):
        box('ground', side * (CHANNEL + EXTENT / 2), 0, -1.6, EXTENT, 2 * EXTENT, 1.6)
        box('quay', side * (CHANNEL + QUAY_W / 2), 0, 0, QUAY_W, 2 * EXTENT, 0.06)
    box('water', 0, 0, WATER_Z - 1.0, 2 * CHANNEL + 0.2, 2 * EXTENT, 1.0)
    for side in (CN, US):
        for k in range(ROADS):
            x = road_x(side, k)
            box('road', x, 0, 0, ROAD_W, 2 * EXTENT, 0.02)
            _centre_dashes(x, -EXTENT, x, EXTENT)
        x_start, x_end = side * (CHANNEL + QUAY_W), side * (X0 + ROADS * PITCH)
        for k in range(-ROADS, ROADS + 1):
            y = road_y(k)
            box('road', (x_start + x_end) / 2, y, 0, abs(x_end - x_start), ROAD_W, 0.02)
            _centre_dashes(x_start, y, x_end, y)


def _centre_dashes(x0: float, y0: float, x1: float, y1: float, step: float = 3.2,
                   length: float = 1.4) -> None:
    n = int(math.hypot(x1 - x0, y1 - y0) / step)
    horizontal = abs(x1 - x0) > abs(y1 - y0)
    for i in range(n):
        t = (i + 0.5) / n
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        if not is_visible(x, y, 2.0):
            continue
        if horizontal:
            box('mark', x, y, 0.02, length, 0.14, 0.005)
        else:
            box('mark', x, y, 0.02, 0.14, length, 0.005)


# ── China side: Hongyuan production ───────────────────────────────────────
def zone_asu(cx: float, cy: float) -> None:
    """Air separation unit, modelled on the Hongyuan plant photos."""
    pad(cx, cy)
    cold_box_tower(cx - 2.8, cy + 2.4, 1.7, 13.0, side='E', logo_brand='hy')
    cold_box_tower(cx + 2.9, cy + 2.9, 1.5, 11.0, side='S', logo_brand='hy')
    storage_tank(cx - 0.2, cy - 1.0, 1.9, 4.4, band='blue', brand='hy')
    storage_tank(cx + 3.0, cy - 2.6, 1.5, 3.8, band='yellow', brand='hy')
    gable_building(cx - 3.3, cy - 2.4, 2.6, 3.4, 2.0, rise=0.6, ridge='Y')
    cooling_tower(cx + 0.4, cy + 3.7, 2.4, 1.2)
    cyl('steel', cx - 1.8, cy + 2.4, Z0 + 5.5, 0.16, 2.2, axis='X')
    HOTSPOTS['asu'] = (cx - 2.8, cy + 2.4, Z0 + 14.2)


def zone_purification(cx: float, cy: float) -> None:
    pad(cx, cy)
    for i, h in enumerate((9.5, 11.0, 8.0, 10.0, 7.0)):
        column(cx - 3.3 + i * 1.45, cy + 2.6, 0.45, h)
    for x in (cx - 3.6, cx - 1.2, cx + 1.2, cx + 3.6):
        box('steel', x, cy + 0.9, Z0, 0.18, 0.18, 3.0)
    for k, z in enumerate((2.6, 2.95, 3.3)):
        cyl(('blue', 'steel', 'white')[k], cx, cy + 0.9, Z0 + z, 0.13, 7.6, axis='X')
    flat_building(cx + 1.6, cy - 2.4, 5.2, 3.2, 2.6, floors=2)
    cryo_tank(cx - 3.0, cy - 2.6, 0.8, 3.2, brand='hy')
    HOTSPOTS['purification'] = (cx - 3.3 + 1.45, cy + 2.6, Z0 + 11.6)


def zone_filling(cx: float, cy: float) -> None:
    """Filling hall and Hongyuan's product warehouse: filled rare-gas cylinders stand in cages on
    the yard in front of its doors (the two-block warehouse next door handles the trucks)."""
    pad(cx, cy)
    gable_building(cx - 1.0, cy + 1.8, 7.0, 4.4, 3.0, ridge='X', doors=3, logo_brand='hy', logo_width=2.6)
    flat_building(cx + 3.75, cy + 1.8, 2.3, 3.6, 2.6, floors=2)
    # Rooftop sign sits right of the hall's roof overhang (x > cx + 2.75) so the roof can't occlude it.
    box('blue', cx + 3.85, cy + 0.2, Z0 + 2.65, 2.2, 0.1, 0.85)
    box('white', cx + 3.85, cy + 0.12, Z0 + 2.73, 2.04, 0.1, 0.69)
    logo.on_wall('hy', cx + 3.85, cy + 0.07, Z0 + 3.075, 1.45, 'S')
    box('paving', cx - 1.2, cy - 3.2, Z0, 9.0, 4.4, 0.01)                       # product yard
    for i, x in enumerate((cx - 4.2, cx - 2.2, cx - 0.2, cx + 1.8)):
        for j, y in enumerate((cy - 2.2, cy - 4.1)):
            cage(x, y, GAS_CAPS[(i + j) % len(GAS_CAPS)])
    HOTSPOTS['filling'] = (cx - 1.0, cy + 1.8, Z0 + 4.4)


def zone_tank_farm(cx: float, cy: float) -> None:
    """Hongyuan tank farm on a two-block lot: two rows of storage tanks either side of a pipe rack."""
    pad(cx, cy, cells=2)
    for k, y in enumerate((cy - 9.0, cy - 1.5, cy + 6.0)):
        storage_tank(cx - 3.4, y, 1.9, 4.4, band=('blue', 'yellow')[k % 2], brand='hy')
        storage_tank(cx + 2.6, y + 1.2, 1.7, 3.8, band=('yellow', 'blue')[k % 2], brand='hy')
    for dy in range(-11, 12, 3):                                  # pipe rack along the lot
        box('steel', cx - 0.4, cy + dy, Z0, 0.16, 0.16, 2.4)
    for k, z in enumerate((2.3, 2.6)):
        cyl(('blue', 'steel')[k], cx - 0.4, cy, Z0 + z, 0.12, 23.0, axis='Y')
    for x in (cx - 3.4, cx - 1.4):
        cryo_tank(x, cy + 12.6, 0.8, 3.0, band=False, brand='hy')
    tree_row(cx - 5.7, cy - 15.0, cx + 5.7, cy - 15.0, 6)


LOGO_WIDTHS = {'airocean': (4.4, 4.2), 'hy': (3.4, 3.2)}    # dock wall, end wall: ~1.5 tall


def distribution_hall(hx: float, hy: float, sy: float, brand: str, truck: str) -> float:
    """Long gable hall (ridge along Y) with six loading docks on its +X side facing the camera,
    two of the brand's trucks backed onto them and its logo on both camera-facing walls.
    Shared by Hongyuan's warehouse and Airocean's distribution centre; returns the wall height."""
    sx, sz = 7.2, 3.6
    box('white', hx, hy, Z0, sx, sy, sz)
    gable('blue', hx, hy, Z0 + sz, sx, sy, 1.6, ridge='Y')
    wall = hx + sx / 2
    docks = [hy - sy / 2 + (i + 0.5) * sy / 6 for i in range(6)]
    for y in docks:
        box('dark', wall + 0.04, y, Z0, 0.08, 1.4, 1.6)
    for y in (docks[1], docks[4]):
        veh.park(truck, wall + 0.1 + veh.TRUCK_REAR, y, 0, z=Z0)       # rear at the dock
    dock_logo, end_logo = LOGO_WIDTHS[brand]
    logo.on_wall(brand, wall, (docks[2] + docks[3]) / 2, Z0 + 2.65, dock_logo, 'E')
    logo.on_wall(brand, hx, hy - sy / 2, Z0 + 2.2, end_logo, 'S')
    return sz


def zone_hy_warehouse(cx: float, cy: float) -> None:
    """Hongyuan's logistics warehouse on a two-block lot, the mirror of Airocean's: the docked hall
    with HY trucks at its doors, and HY tankers parked in painted bays on the apron in front."""
    pad(cx, cy, cells=2)
    distribution_hall(cx - 2.4, cy + 3.0, 22.0, 'hy', 'hy_box')
    box('paving', cx - 2.4, cy - 11.9, Z0, 7.6, 6.2, 0.01)             # tanker apron
    for x in (cx - 5.4, cx - 3.4, cx - 1.4, cx + 0.6):
        box('mark', x, cy - 11.9, Z0 + 0.01, 0.08, 5.4, 0.005)        # bay lines
    for x in (cx - 4.4, cx - 2.4, cx - 0.4):
        veh.park('hy', x, cy - 12.0, -90, z=Z0 + 0.01)                 # nose to the camera


def china_wharf() -> None:
    """Hongyuan quay: two ISO tank containers waiting for export, nothing else."""
    x0 = -(CHANNEL + QUAY_W / 2)
    for y in (-7.6, -4.2):
        iso_tank(x0 + 0.4, y, axis='Y', brand='hy')


# ── US side: Airocean ─────────────────────────────────────────────────────
CRANE_Y = 1.5


def us_wharf() -> dict:
    """Quay with a gantry crane over the moored ship; returns the trolley's travel for animation."""
    x0 = CHANNEL + QUAY_W / 2
    for lx in (x0 - 1.4, x0 + 1.4):
        for ly in (CRANE_Y - 1.6, CRANE_Y + 1.6):
            box('blue', lx, ly, Z0, 0.4, 0.4, 7.0)
    box('blue', x0 - 3.5, CRANE_Y - 0.8, Z0 + 7.0, 12.0, 0.4, 0.55)
    box('blue', x0 - 3.5, CRANE_Y + 0.8, Z0 + 7.0, 12.0, 0.4, 0.55)
    box('white', x0 + 1.9, CRANE_Y, Z0 + 7.55, 2.2, 2.0, 1.0)
    for i, y in enumerate((-7.0, -4.0)):
        for j in range(2):
            box(('blue', 'white', 'steel')[(i + j) % 3], x0 - 0.6 + j * 1.2, y, Z0, 1.05, 2.7, 1.0)
    box('white', x0 - 0.6, -7.0, Z0 + 1.0, 1.05, 2.7, 1.0)
    iso_tank(x0 + 0.5, 8.5, axis='Y')
    ship_x = CHANNEL - veh.SHIP_WIDTH / 2 - 0.4           # moored alongside the quay, under the boom
    HOTSPOTS['ship'] = tuple(veh.docked_ship(ship_x, 0.5, WATER_Z))
    return {'y': CRANE_Y, 'z': Z0 + 6.2, 'x_ship': ship_x, 'x_quay': x0 + 0.2}


def zone_hq(cx: float, cy: float) -> None:
    pad(cx, cy)
    tx, ty, th = cx - 1.3, cy + 1.2, 13.0
    box('glass', tx, ty, Z0, 4.4, 4.4, th)
    for k in range(1, 10):
        box('white', tx, ty, Z0 + k * 1.3 - 0.12, 4.6, 4.6, 0.24)
    box('blue', tx, ty, Z0 + th, 4.6, 4.6, 1.3)
    # White sign plates on both camera-facing sides of the crown, each carrying the Airocean logo.
    box('white', tx, ty - 2.33, Z0 + th + 0.09, 3.9, 0.06, 1.12)
    box('white', tx + 2.33, ty, Z0 + th + 0.09, 0.06, 3.9, 1.12)
    logo.on_wall('airocean', tx, ty - 2.36, Z0 + th + 0.65, 3.0, 'S')
    logo.on_wall('airocean', tx + 2.36, ty, Z0 + th + 0.65, 3.0, 'E')
    flat_building(cx + 1.8, cy - 2.2, 5.8, 3.4, 2.2, floors=1)
    tree_row(cx - 4.5, cy - 4.6, cx + 4.5, cy - 4.6, 6)
    HOTSPOTS['hq'] = (tx, ty, Z0 + th + 1.5)


def zone_inventory(cx: float, cy: float) -> None:
    """Airocean's Pennsylvania distribution centre on a two-block lot: a long hall whose street side
    has loading docks with Airocean trucks backed onto them, and the rare-gas cylinder cages."""
    pad(cx, cy, cells=2)
    hx, hy = cx - 2.4, cy + 2.0
    sz = distribution_hall(hx, hy, 24.0, 'airocean', 'airocean')
    for x, cap in ((cx - 4.6, 'kr'), (cx - 2.6, 'xe'), (cx - 0.6, 'ne')):
        cage(x, cy - 13.4, cap)
    HOTSPOTS['inventory'] = (hx, hy, Z0 + sz + 2.2)


def zone_semiconductor(cx: float, cy: float) -> None:
    """Semiconductor fab on a two-block lot: a long cleanroom building with rooftop air handlers,
    its utility plant, and the bulk-gas yard that Airocean's specialty gases feed."""
    industry_pad(cx, cy, cells=2)
    fx, fy, sx, sy, sz = cx - 1.4, cy + 3.0, 9.4, 19.0, 3.6
    box('white', fx, fy, Z0, sx, sy, sz)
    box('blue', fx, fy, Z0 + sz, sx - 0.4, sy - 0.4, 0.1)
    box('glass', fx, fy - sy / 2 - 0.03, Z0 + 1.7, sx - 1.0, 0.08, 0.8)
    box('glass', fx + sx / 2 + 0.03, fy, Z0 + 1.7, 0.08, sy - 1.0, 0.8)
    for i in range(3):
        for j in range(6):
            box('white', fx - 2.8 + i * 2.8, fy - 7.5 + j * 3.0, Z0 + sz + 0.1, 1.2, 1.2, 0.6)
    for j in range(4):
        cyl('steel', fx + 3.8, fy - 6.0 + j * 4.0, Z0 + sz + 0.1, 0.3, 2.2, segs=16)   # exhaust stacks
    flat_building(cx + 2.6, cy - 11.2, 6.0, 5.0, 3.0, floors=1)                     # utility plant
    for x in (cx - 5.0, cx - 3.2):
        cryo_tank(x, cy - 11.6, 0.7, 3.2)                                            # bulk-gas yard
    cryo_tank(cx - 4.1, cy - 13.8, 0.6, 2.6)
    HOTSPOTS['semiconductor'] = (fx, fy, Z0 + sz + 1.2)


def zone_scientific(cx: float, cy: float) -> None:
    """Research lab: the domed lab building behind an open instrument floor (NMR magnet, GC-MS and
    ICP-MS benches, fume hood, helium cylinders) and the bulk liquid-helium dewar."""
    industry_pad(cx, cy)
    lx, ly = cx - 1.8, cy + 3.6
    dx, dy = lx - 0.6, ly + 0.6                                                    # rooftop dome
    flat_building(lx, ly, 6.4, 5.0, 3.4, floors=2, roof='white')
    sphere('white', dx, dy, Z0 + 3.5, 1.5, squash=0.9)
    box('blue', dx, ly - 0.85, Z0 + 3.5, 0.5, 0.15, 1.4)
    cyl('steel', dx, dy, Z0 + 3.4, 1.6, 0.15)
    box('quay', cx - 0.2, cy - 2.6, Z0, 11.6, 6.4, 0.06)                          # instrument floor
    zf = Z0 + 0.06
    nmr_magnet(cx - 4.0, cy - 2.4, zf)
    for by in (cy - 1.0, cy - 3.8):
        box('white', cx + 0.2, by, zf, 3.4, 0.9, 0.85)                            # lab benches
        box('dark', cx + 0.2, by, zf + 0.85, 3.4, 0.9, 0.05)
    for x, y, sx, sy, sz in ((cx - 0.8, cy - 1.0, 1.0, 0.7, 0.6),                 # GC
                             (cx + 0.6, cy - 1.0, 0.8, 0.7, 0.45),                # MS
                             (cx - 0.4, cy - 3.8, 1.4, 0.8, 0.85),                # ICP-MS
                             (cx + 1.2, cy - 3.8, 0.6, 0.6, 1.1)):                # LC stack
        lab_instrument(x, y, zf + 0.9, sx, sy, sz)
    box('white', cx + 4.0, cy - 1.4, zf, 1.4, 0.9, 2.1)                           # fume hood
    box('glass', cx + 4.0, cy - 1.88, zf + 0.9, 1.1, 0.04, 0.9)
    for i in range(4):
        bottle(cx + 3.4 + i * 0.5, cy - 4.0, 'he', zf, s=1.3)                     # helium cylinders
    cryo_tank(cx + 5.2, cy + 4.0, 0.7, 2.8)                                       # liquid-helium dewar
    HOTSPOTS['scientific'] = (dx, dy, Z0 + 6.1)                                   # above the dome


def zone_aerospace(cx: float, cy: float) -> None:
    """Launch site on a two-block lot. The rocket on its pad is the landmark, held by the swing
    arms of its service tower; spherical propellant tanks and a smaller assembly hangar sit back."""
    industry_pad(cx, cy, cells=2)
    box('quay', cx + 0.8, cy + 7.6, Z0, 6.6, 6.6, 0.6)                        # launch pad
    zp = Z0 + 0.6
    rx, ry, tx, ty = cx + 1.6, cy + 7.0, cx - 0.8, cy + 8.6
    launch_tower(tx, ty, zp, 14.4)
    height = rocket(rx, ry, zp)
    dx, dy = rx - tx, ry - ty
    reach = math.hypot(dx, dy)
    for z in (7.6, 10.4):                                                     # swing arms
        strut('blue', (tx, ty, zp + z), (rx - dx / reach * 0.95, ry - dy / reach * 0.95, zp + z), 0.22)
    gable_building(cx + 1.2, cy - 10.2, 5.4, 6.2, 4.2, rise=1.3, ridge='Y', doors=1)   # assembly hangar
    box('paving', cx + 1.2, cy - 1.4, Z0, 2.4, 11.4, 0.01)                   # crawlerway to the pad
    sphere_tank(cx - 4.4, cy - 1.0, 1.3)
    sphere_tank(cx - 4.4, cy + 2.6, 1.1)
    HOTSPOTS['aerospace'] = (rx, ry, zp + height + 1.8)


def zone_window(cx: float, cy: float) -> None:
    """Window plant: a glass hall gridded like a window wall (the HQ's look), and finished
    insulated-glass windows standing on racks in the yard."""
    industry_pad(cx, cy)
    gx, gy, sx, sy, sz = cx - 1.4, cy + 3.0, 8.6, 5.0, 3.4
    box('glass', gx, gy, Z0, sx, sy, sz)
    box('white', gx, gy, Z0 + sz, sx + 0.1, sy + 0.1, 0.25)                   # roof slab
    box('white', gx, gy, Z0 + sz / 2 - 0.06, sx + 0.06, sy + 0.06, 0.12)      # floor band
    for i in range(1, 9):
        box('white', gx - sx / 2 + i * sx / 9, gy - sy / 2 - 0.02, Z0, 0.1, 0.06, sz)   # mullions
    for j in range(1, 5):
        box('white', gx + sx / 2 + 0.02, gy - sy / 2 + j * sy / 5, Z0, 0.06, 0.1, sz)
    for row_y in (cy - 1.6, cy - 4.4):
        box('steel', cx - 0.2, row_y + 0.1, Z0, 8.0, 0.6, 0.12)               # rack base
        for i in range(4):
            framed_window(cx - 3.0 + i * 1.9, row_y, Z0 + 0.12)
    HOTSPOTS['window'] = (gx - sx / 2 + 0.6, gy + sy / 2 - 0.6, Z0 + sz + 2.0)


def zone_electrical(cx: float, cy: float) -> None:
    """Substation: a transmission line crosses the back of the yard on two lattice towers;
    transformers and the SF6 gas-insulated switchgear stand in front, the control room aside."""
    industry_pad(cx, cy)
    hangs = lattice_pylon(cx - 4.6, cy + 4.4)
    lattice_pylon(cx + 3.8, cy + 4.4)
    for _, y, z in hangs:
        cyl('dark', cx, y, z, 0.035, PAD - 0.6, axis='X', segs=8)            # conductors
    for x in (cx - 2.4, cx + 1.4):
        transformer(x, cy + 0.2)
    for y in (cy - 2.8, cy - 3.6):
        cyl('sf6', cx + 0.9, y, Z0 + 0.9, 0.28, 6.4, axis='X', segs=24)       # GIS bus ducts
    for x in (cx - 2.0, cx + 0.9, cx + 3.8):
        box('steel', x, cy - 3.2, Z0, 0.2, 1.5, 0.6)
        cyl('white', x, cy - 3.2, Z0 + 1.15, 0.1, 1.1, segs=10)               # bushing
    flat_building(cx - 4.6, cy - 4.4, 2.8, 2.6, 2.2, floors=1)               # control room
    HOTSPOTS['electrical'] = (cx - 2.4, cy + 0.2, Z0 + 4.2)


def zone_lighting(cx: float, cy: float) -> None:
    """Lamp plant: a hall whose whole roof is lined with glowing neon, krypton and xenon tubes,
    and lit street lamps along the front."""
    industry_pad(cx, cy)
    bx, by, sx, sy, sz = cx - 0.6, cy + 1.8, 9.0, 6.0, 3.0
    flat_building(bx, by, sx, sy, sz, floors=2, roof='dark')
    glows, rows = ('glow_ne', 'glow_kr', 'glow_xe'), 6                       # spaced out, not crowded
    for k in range(rows):
        y = by - sy / 2 + 0.5 + k * (sy - 1.0) / (rows - 1)
        cyl(glows[k % 3], bx, y, Z0 + sz + 0.3, 0.1, sx - 1.0, axis='X', segs=12)
    for x in (bx - sx / 2 + 0.7, bx + sx / 2 - 0.7):
        box('steel', x, by, Z0 + sz, 0.12, sy - 0.8, 0.22)                    # tube rails
    for i in range(5):
        lamp_post(cx - 5.6 + i * 2.8, cy - 5.6)
    HOTSPOTS['lighting'] = (bx - sx / 2 + 0.6, by + sy / 2 - 0.6, Z0 + sz + 2.0)


# Where each story zone stands, per video. Key: first block; value: (builder, blocks along the channel).
LAYOUTS = {
    # Desktop: China zones run along the wharf; Airocean's HQ and distribution centre face the port
    # and the customer industries fan out inland.
    'landscape': {
        (CN, 0, -2): (zone_asu, 1),
        (CN, 0, -1): (zone_purification, 1),
        (CN, 0, 0): (zone_filling, 1),
        (CN, 0, 1): (zone_tank_farm, 2),
        (CN, 1, -1): (zone_hy_warehouse, 2),
        (US, 0, -2): (zone_scientific, 1),
        (US, 0, -1): (zone_window, 1),
        (US, 0, 0): (zone_hq, 1),
        (US, 0, 1): (zone_inventory, 2),
        (US, 1, -2): (zone_aerospace, 2),
        (US, 1, 0): (zone_electrical, 1),
        (US, 1, 1): (zone_semiconductor, 2),
        (US, 2, 0): (zone_lighting, 1),
    },
    # Phones: Airocean only. The distribution centre and HQ sit by the port at the top; the
    # industries step down the tall frame in two staggered columns (each step down the screen is
    # one block further from the wharf and one block back along it).
    'portrait': {
        (US, 0, -2): (zone_inventory, 2),
        (US, 1, -1): (zone_hq, 1),
        (US, 1, -3): (zone_semiconductor, 2),
        (US, 2, -1): (zone_lighting, 1),
        (US, 2, -4): (zone_window, 1),
        (US, 3, -4): (zone_aerospace, 2),
        (US, 3, -5): (zone_scientific, 1),
        (US, 4, -3): (zone_electrical, 1),
    },
}


def zone_cells(layout: dict) -> set:
    """Every (side, ix, iy) block a story zone stands on."""
    return {(side, ix, iy + k) for (side, ix, iy), (_, cells) in layout.items() for k in range(cells)}


def build_zones(layout: dict) -> dict:
    """Story zones and both wharves (records HOTSPOTS); returns the crane trolley's travel."""
    for (side, ix, iy), (builder, cells) in layout.items():
        builder(*lot(side, ix, iy, cells))
    china_wharf()
    return us_wharf()


# ── District filler for the remaining visible blocks ──────────────────────
def _edge_trees(cx: float, cy: float, rng: random.Random) -> None:
    """One tidy tree line on a green strip along one of the block's two street-facing edges."""
    half = PAD / 2
    if rng.random() < 0.5:
        edge = cy - half + 1.0                        # along the -Y edge
        tree_row(cx - half + 1.5, edge, cx + half - 1.5, edge, 6)
    else:
        edge = cx + half - 1.0                        # along the +X edge
        tree_row(edge, cy - half + 1.5, edge, cy + half - 1.5, 6)


def decor_green(cx: float, cy: float, rng: random.Random) -> None:
    """Lawn crossed by two footpaths with loose tree clusters: the calm, green breaks in the map."""
    pad(cx, cy, 'lawn')
    box('pad', cx, cy, Z0, PAD - 2.4, 1.0, 0.02)
    box('pad', cx, cy, Z0, 1.0, PAD - 2.4, 0.02)
    for qx in (-1, 1):
        for qy in (-1, 1):
            for _ in range(rng.randint(1, 3)):
                tree(cx + qx * rng.uniform(1.8, 5.6), cy + qy * rng.uniform(1.8, 5.6), rng.uniform(0.85, 1.25))


def decor_cylinder_yard(cx: float, cy: float, rng: random.Random) -> None:
    """Hongyuan cylinder yard: a branded dispatch shed and rows of rare-gas cylinder cages."""
    pad(cx, cy)
    gable_building(cx - 1.2, cy + 3.4, 7.4, 4.0, 2.6, rise=1.0, ridge='X', doors=2,
                   logo_brand='hy', logo_width=2.4)
    for i in range(4):
        for j in range(2):
            cage(cx - 4.6 + i * 2.4, cy - 0.6 - j * 2.4, rng.choice(GAS_CAPS))
    _edge_trees(cx, cy, rng)


def decor_hy_tank_row(cx: float, cy: float, rng: random.Random) -> None:
    """Three Hongyuan storage tanks standing in a straight row."""
    pad(cx, cy)
    for i, x in enumerate((cx - 4.0, cx, cx + 4.0)):
        storage_tank(x, cy + 1.2, 1.6, 3.4 + rng.random() * 0.8, band=('blue', 'yellow')[i % 2], brand='hy')
    _edge_trees(cx, cy, rng)


def decor_factory(cx: float, cy: float, rng: random.Random) -> None:
    """Long white production hall with a blue roof, like the big halls on the Hangyang map."""
    pad(cx, cy)
    length, depth = 8.0 + rng.random() * 3.5, 4.5 + rng.random() * 1.5
    flat_building(cx + rng.uniform(-1.0, 1.0), cy + 1.5, length, depth, 2.8 + rng.random() * 1.0, floors=1)
    _edge_trees(cx, cy, rng)


def decor_offices(cx: float, cy: float, rng: random.Random) -> None:
    """City block: an office tower set back from the street (below the HQ's height), often a low
    annex beside it, and street trees along the front."""
    pad(cx, cy)
    floors = rng.randint(4, 7)
    tx = cx + rng.uniform(-3.0, -1.0)
    flat_building(tx, cy + 2.4, 4.2, 4.2, 1.2 * floors + 0.4, floors=floors)
    if rng.random() < 0.6:
        flat_building(tx + 5.0, cy + 1.0, 3.4, 4.6, 2.2, floors=1)
    tree_row(cx - 5.7, cy - 6.0, cx + 5.7, cy - 6.0, 6)


def decor_warehouse(cx: float, cy: float, rng: random.Random) -> None:
    pad(cx, cy)
    gable_building(cx + rng.uniform(-1.0, 1.0), cy + 1.2, 7.0 + rng.random() * 2.5, 5.0, 2.8,
                   ridge='X', doors=3)
    _edge_trees(cx, cy, rng)


# ── Two-block lots (cx, cy is the lot centre; the lot is PAD x (PAD + PITCH)) ──
def big_hy_plant(cx: float, cy: float, rng: random.Random) -> None:
    """Hongyuan production complex: a long process hall with a cold box column and a storage tank
    behind it."""
    pad(cx, cy, cells=2)
    hx, hy, sx, sy, sz = cx - 2.2, cy - 2.0, 7.0, 18.0, 3.4
    box('white', hx, hy, Z0, sx, sy, sz)
    gable('blue', hx, hy, Z0 + sz, sx, sy, 1.4, ridge='Y')
    windows(hx, hy, sx, sy, Z0 + sz * 0.55, 1, sz * 0.4, 2, 12, faces='E')
    logo.on_wall('hy', hx, hy - sy / 2, Z0 + 1.7, 2.6, 'S')
    cold_box_tower(cx + 3.6, cy + 10.5, 1.5, 9.0 + rng.random() * 2.0, side='S', logo_brand='hy')
    storage_tank(cx - 3.2, cy + 11.5, 1.8, 4.0, band='yellow' if rng.random() < 0.5 else 'blue', brand='hy')


def big_plant(cx: float, cy: float, rng: random.Random) -> None:
    """Manufacturing plant: a long production hall (flat roof with air handlers, or twin pitched
    spans), a front office and a car park."""
    pad(cx, cy, cells=2)
    hx, hy, sx, sy, sz = cx - 1.6, cy + 3.0, 9.0, 20.0, 3.4 + rng.random() * 0.8
    if rng.random() < 0.5:
        box('white', hx, hy, Z0, sx, sy, sz)
        box('blue', hx, hy, Z0 + sz, sx - 0.3, sy - 0.3, 0.1)
        for i in range(2):
            for j in range(5):
                box('white', hx - 2.0 + i * 4.0, hy - 8.0 + j * 4.0, Z0 + sz + 0.1, 1.4, 1.4, 0.6)
    else:
        for k in (-1, 1):                                                 # twin-span shed
            box('white', hx + k * sx / 4, hy, Z0, sx / 2, sy, sz)
            gable('blue', hx + k * sx / 4, hy, Z0 + sz, sx / 2, sy, 1.2, ridge='Y', overhang=0.1)
    windows(hx, hy, sx, sy, Z0 + 0.4, 1, sz - 0.8, 6, 14)
    flat_building(cx + 2.4, cy - 11.0, 6.0, 4.0, 2.6, floors=2)          # front office
    box('paving', cx - 3.6, cy - 11.4, Z0, 6.0, 5.6, 0.01)               # car park


def big_campus(cx: float, cy: float, rng: random.Random) -> None:
    """Office campus: towers of different heights around a central lawn with trees."""
    pad(cx, cy, cells=2)
    box('lawn', cx, cy, Z0, PAD - 2.0, 9.0, 0.02)
    for x, y, w, floors in ((cx - 3.0, cy + 9.5, 4.6, rng.randint(6, 8)),
                            (cx + 2.8, cy + 11.0, 4.0, rng.randint(4, 6)),
                            (cx - 2.4, cy - 10.0, 5.0, rng.randint(3, 5))):
        flat_building(x, y, w, w, 1.2 * floors + 0.4, floors=floors)
    for _ in range(7):
        tree(cx + rng.uniform(-5.4, 5.4), cy + rng.uniform(-3.6, 3.6), rng.uniform(0.85, 1.2))


# Each district draws its blocks at random (fixed seed) from what belongs there, so the map
# reads by area: often a two-block lot, otherwise a single block whose type is made much less
# likely when a neighbouring block already has it.
SINGLES = {
    'industrial': ((decor_hy_tank_row, 0.3), (decor_factory, 0.25), (decor_cylinder_yard, 0.25),
                   (decor_green, 0.2)),
    'logistics': ((decor_warehouse, 0.45), (decor_factory, 0.3), (decor_green, 0.25)),
    'city': ((decor_offices, 0.55), (decor_green, 0.25), (decor_factory, 0.2)),
}
DOUBLES = {
    'industrial': (big_hy_plant,),
    'logistics': (big_plant,),
    'city': (big_plant, big_campus),
}
DOUBLE_ODDS = 0.5                      # chance a free block starts a two-block lot when it can
REPEAT_PENALTY = 0.15                  # weight factor per neighbouring block of the same type
DONE_NEIGHBOURS = ((-1, -1), (-1, 0), (-1, 1), (0, -1))   # already decided when (ix, iy) is


def district(side: int, ix: int) -> str:
    """China is one industrial estate; the US goes logistics -> city moving inland from the port."""
    if side == CN:
        return 'industrial'
    return 'logistics' if ix < 2 else 'city'


def _can_merge(side: int, ix: int, iy: int) -> bool:
    """Blocks (ix, iy) and (ix, iy + 1) may share a lot unless a truck turns along the street between."""
    return not (ix >= 1 and iy + 1 == TURN_ROAD[side])


def build_decor(layout: dict) -> None:
    rng = random.Random(7)
    taken = zone_cells(layout)
    picked = {}
    for side in (CN, US):
        for ix in BLOCKS_X:
            name = district(side, ix)
            builders, weights = zip(*SINGLES[name])
            for iy in BLOCKS_Y:
                cell, nxt = (side, ix, iy), (side, ix, iy + 1)
                if cell in taken or not is_visible(*block(side, ix, iy)):
                    continue
                if nxt not in taken and _can_merge(side, ix, iy) and rng.random() < DOUBLE_ODDS:
                    builder = picked[cell] = picked[nxt] = rng.choice(DOUBLES[name])
                    taken |= {cell, nxt}
                    builder(*lot(side, ix, iy, 2), rng)
                    continue
                near = [picked.get((side, ix + dx, iy + dy)) for dx, dy in DONE_NEIGHBOURS]
                odds = [w * REPEAT_PENALTY ** near.count(b) for b, w in zip(builders, weights)]
                builder = picked[cell] = rng.choices(builders, odds)[0]
                taken.add(cell)
                builder(*block(side, ix, iy), rng)


# ── Traffic ───────────────────────────────────────────────────────────────
def _y_span(x: float, margin: float) -> tuple:
    """Visible stretch (plus margin) of a road running along Y at x; lo > hi if never visible."""
    (u0, u1), (v0, v1) = _window['u'], _window['v']
    lo = max(SQRT2 * u0 - x, SQRT2 * v0 + x) - margin
    hi = min(SQRT2 * u1 - x, SQRT2 * v1 + x) + margin
    return lo, hi


def _x_span(y: float, margin: float) -> tuple:
    """Visible stretch (plus margin) of a road running along X at y; lo > hi if never visible."""
    (u0, u1), (v0, v1) = _window['u'], _window['v']
    lo = max(SQRT2 * u0 - y, y - SQRT2 * v1) - margin
    hi = min(SQRT2 * u1 - y, y - SQRT2 * v0) + margin
    return lo, hi


def traffic_lanes(margin: float = 9.0) -> list:
    """Light traffic: one vehicle per lane, each lane entering and leaving the frame, plus one ship.
    Six trucks: a Hongyuan and an Airocean truck on the road along each wharf, an L-turn on each
    side, and one on each side's outer road so the map's edges have traffic coming and going.
    Every vehicle crosses its whole lane once per loop (count = loops = 1), so the loop is seamless."""
    min_span = 2 * margin + 6                      # at least a few units actually on screen
    lanes = []

    def straight(kind: str, x: float, northbound: bool, phase: float) -> None:
        lo, hi = _y_span(x, margin)
        if hi - lo < min_span:
            return
        lane_x = x + LANE if northbound else x - LANE   # keep right
        ends = ((lane_x, lo), (lane_x, hi)) if northbound else ((lane_x, hi), (lane_x, lo))
        lanes.append(Lane(kind, ends, count=1, loops=1, phase=phase))

    def turn(kind: str, side: int, phase: float) -> None:
        """Down the side's second road, then along its turning street away from the wharf."""
        x2, yt = road_x(side, 1) - LANE, road_y(TURN_ROAD[side]) - side * LANE
        lo, hi = _y_span(x2, margin)
        if hi - lo < min_span or not lo < yt < hi:
            return                                   # this junction is off this video's frame
        lo_x, hi_x = _x_span(yt, margin)
        lanes.append(Lane(kind, ((x2, hi), (x2, yt), (lo_x if side == CN else hi_x, yt)),
                          count=1, loops=1, phase=phase))

    straight('hy', road_x(CN, 0), True, 0.0)
    straight('airocean', road_x(US, 0), False, 0.3)
    straight('hy', road_x(CN, 2), False, 0.4)
    straight('airocean', road_x(US, 2), True, 0.6)
    turn('hy', CN, 0.55)          # Hongyuan tanker: right turn west, out of the left edge
    turn('airocean', US, 0.8)     # Airocean truck: left turn east to the customers
    # One cargo ship heads down the channel's China half, clear of the moored ship; phase 0.2
    # keeps it in the upper channel on frame 0 (the poster), away from the moored ship.
    lo, hi = _y_span(-CHANNEL / 2, 16.0)
    lanes.append(Lane('ship', ((-CHANNEL / 2, hi), (-CHANNEL / 2, lo)), count=1, loops=1, phase=0.2, z=WATER_Z))
    return lanes
