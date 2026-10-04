"""Airocean hero scene: build, frame, light and render with EEVEE (still poster and video loop).

Usage (from the site root):
    blender -b -P scene-src/airocean_scene.py -- --preview        still 1600x900, no animation
    blender -b -P scene-src/airocean_scene.py -- --anim-preview   960x540 frame loop + still
    blender -b -P scene-src/airocean_scene.py -- --final          1920x1080 frame loop + 2880x1620 poster
Add --portrait for the phone video (9:16: 1080x1920 loop, 1440x2560 poster, 900x1600 previews).
then
    blender -b -P scene-src/encode_video.py [-- --portrait]   (frames -> images/hero-scene[-portrait].mp4)
    python scene-src/build_preview.py

Outputs in scene-src/out/: hero-scene[-portrait].png (poster = frame 0), hero-scene[-portrait].json
(hotspots, frame count), frames[-portrait]/f_0000.png ...; plus scene-src/airocean_scene[-portrait].blend
for manual tweaks.
"""
import json
import logging
import math
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

logging.basicConfig(level=logging.INFO, format='[scene] %(message)s')
log = logging.getLogger('scene')

# ── Config ────────────────────────────────────────────────────────────────
ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
MODE = 'final' if '--final' in ARGV else 'anim-preview' if '--anim-preview' in ARGV else 'preview'
VARIANT = 'portrait' if '--portrait' in ARGV else 'landscape'
FPS = 24
LOOP_SECONDS = 24       # one ship crossing the whole channel per loop needs this long to look calm
FRAMES = FPS * LOOP_SECONDS
VIDEO_SAMPLES = {'final': 64, 'anim-preview': 16}                 # EEVEE TAA samples per mode
STILL_SAMPLES = {'final': 128, 'anim-preview': 64, 'preview': 64}

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)            # make the sibling scene_* modules importable under Blender
import scene_layout as lay          # noqa: E402
import scene_logos as logo          # noqa: E402
import scene_vehicles as veh        # noqa: E402
from scene_props import B           # noqa: E402

# Two videos of the same map. Desktop frames about 30 % China, 20 % open water and 50 % USA; the
# phone video is almost all Airocean, with the moored ship (and a glimpse of Hongyuan's shore)
# across a strip of sea at the top. `share` of the frame lies on `side` of the channel, which
# places the camera across it; `along` (plan y of the frame centre) or `ship_x` (where the moored
# ship sits across the frame) slides it along the channel. Hotspots must land inside `bands`
# (x, y fractions of the image; the transparent header covers the top).
VARIANTS = {
    'landscape': {
        'aspect': 16 / 9, 'ortho': 129.0, 'side': lay.CN, 'share': 0.30, 'along': 7.0,
        'video': {'final': (1920, 1080), 'anim-preview': (960, 540)},
        'still': {'final': (2880, 1620), 'anim-preview': (1600, 900), 'preview': (1600, 900)},
        'bands': ((0.08, 0.92), (0.19, 0.86)), 'suffix': '',
    },
    'portrait': {
        'aspect': 9 / 16, 'ortho': 60.0, 'side': lay.US, 'share': 0.85, 'ship_x': 0.335,
        'video': {'final': (1080, 1920), 'anim-preview': (540, 960)},
        'still': {'final': (1440, 2560), 'anim-preview': (900, 1600), 'preview': (900, 1600)},
        'bands': ((0.08, 0.92), (0.14, 0.88)), 'suffix': '-portrait',
    },
}
CFG = VARIANTS[VARIANT]

OUT_DIR = os.path.join(HERE, 'out')
OUT_PNG = os.path.join(OUT_DIR, f'hero-scene{CFG["suffix"]}.png')
OUT_JSON = os.path.join(OUT_DIR, f'hero-scene{CFG["suffix"]}.json')
FRAMES_DIR = os.path.join(OUT_DIR, f'frames{CFG["suffix"]}')
OUT_BLEND = os.path.join(HERE, f'airocean_scene{CFG["suffix"]}.blend')

CAM_AZIMUTH = 45.0      # degrees; camera sits on the +X / -Y side
CAM_ELEVATION = 36.0
VIEW_LOOK = 'AgX - Medium High Contrast'
EXPOSURE = 0.25


# ── Colour + materials ────────────────────────────────────────────────────
def lin(hex_str: str) -> tuple:
    h = hex_str.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    conv = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*conv, 1.0)


def set_input(node, names: list, value) -> None:
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return


def make_mat(name: str, hex_col: str, rough: float = 0.5, metal: float = 0.0,
             emit: float = 0.0, alpha: float = 1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = lin(hex_col)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emit:
        set_input(bsdf, ['Emission Color', 'Emission'], lin(hex_col))
        set_input(bsdf, ['Emission Strength'], emit)
    if alpha < 1.0:
        set_input(bsdf, ['Alpha'], alpha)
    return m


def water_mat() -> tuple:
    """Blue water with two crossing wave bands; animating their phase makes the surface move.
    Returns the material and its wave nodes (phase is looped by scene_vehicles.bake)."""
    m = make_mat('water', '#1f55d0', rough=0.12)
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    coord = nt.nodes.new('ShaderNodeTexCoord')
    waves = []
    for direction, scale, distortion in (('X', 0.25, 6.0), ('Y', 0.15, 4.0)):
        wave = nt.nodes.new('ShaderNodeTexWave')
        wave.wave_type = 'BANDS'
        wave.bands_direction = direction
        wave.inputs['Scale'].default_value = scale
        wave.inputs['Distortion'].default_value = distortion
        wave.inputs['Detail'].default_value = 2.0
        nt.links.new(coord.outputs['Object'], wave.inputs['Vector'])
        waves.append(wave)
    add = nt.nodes.new('ShaderNodeMath')
    add.operation = 'ADD'
    nt.links.new(waves[0].outputs['Fac'], add.inputs[0])
    nt.links.new(waves[1].outputs['Fac'], add.inputs[1])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.18
    nt.links.new(add.outputs['Value'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return m, waves


def build_materials() -> tuple:
    water, waves = water_mat()
    mats = {
        'white': make_mat('white', '#eef1f5', 0.5),
        'pad': make_mat('pad', '#fafbfc', 0.6),               # near-white plazas: the calm space
        'quay': make_mat('quay', '#e3e8ee', 0.7),
        'ground': make_mat('ground', '#eef2f6', 0.8),
        # Near-black slate asphalt (navy-tinted to match the brand) with crisp white markings;
        # pure black would read as holes in the map and lose all shading.
        'road': make_mat('road', '#2f3744', 0.8),
        'mark': make_mat('mark', '#ffffff', 0.5, emit=0.8),
        'paving': make_mat('paving', '#a3acb8', 0.8),         # on-lot concrete: aprons, car parks
        'foam': make_mat('foam', '#e8f0ff', 0.4, alpha=0.4),
        'blue': make_mat('blue', '#1747e6', 0.4),
        'navy': make_mat('navy', '#14254a', 0.45),
        'glass': make_mat('glass', '#2349b8', 0.15),
        'steel': make_mat('steel', '#c3ccd7', 0.35, metal=0.4),
        'dark': make_mat('dark', '#3a4352', 0.6),
        'tree': make_mat('tree', '#2fbf63', 0.65),
        'grass': make_mat('grass', '#7fd99a', 0.8),
        'lawn': make_mat('lawn', '#c4ead0', 0.85),            # park blocks: pale, so green stays calm
        'industry': make_mat('industry', '#adc6f4', 0.7),     # customer-industry lots: marked as one group
        'yellow': make_mat('yellow', '#f2c230', 0.45),
        'orange': make_mat('orange', '#f08a24', 0.45),
        'cooling': make_mat('cooling', '#27a35a', 0.5),
        'kr': make_mat('kr', '#6d28d9', 0.4),
        'xe': make_mat('xe', '#1d4ed8', 0.4),
        'ne': make_mat('ne', '#b91c1c', 0.4),
        'he': make_mat('he', '#047857', 0.4),
        'sf6': make_mat('sf6', '#0e7490', 0.4),
        'glow_ne': make_mat('glow_ne', '#ff6a3d', 0.5, emit=8.0),
        'glow_kr': make_mat('glow_kr', '#a78bfa', 0.5, emit=8.0),
        'glow_xe': make_mat('glow_xe', '#7cb3ff', 0.5, emit=8.0),
        'lamp': make_mat('lamp', '#fff1d0', 0.5, emit=5.0),
        'water': water,
    }
    return mats, waves


# ── Framing, camera, light ────────────────────────────────────────────────
def _half_height_v() -> float:
    """Half the frame height, measured in plan v units on the ground."""
    return CFG['ortho'] / CFG['aspect'] / 2 / math.sin(math.radians(CAM_ELEVATION))


def side_share(tx: float, grid: int = 120) -> float:
    """Fraction of the frame showing the variant's side of the channel when the camera aims at x = tx
    (sliding along the channel does not change it)."""
    side, ortho, half_v = CFG['side'], CFG['ortho'], _half_height_v()
    hits = 0
    for i in range(grid):
        du = ((i + 0.5) / grid - 0.5) * ortho
        for j in range(grid):
            dv = ((j + 0.5) / grid * 2 - 1) * half_v
            hits += side * (tx + (du - dv) / lay.SQRT2) > lay.CHANNEL
    return hits / grid ** 2


def frame_composition() -> dict:
    """Camera target giving the variant's side `share` of the frame (placed along the channel by
    `along` or by the moored ship's `ship_x`), plus the visible ground window in plan (u, v) coords."""
    ortho = CFG['ortho']
    lo, hi = -150.0, 150.0
    for _ in range(32):
        mid = (lo + hi) / 2
        # Moving the target east (+x) shrinks the China share and grows the US share.
        if (side_share(mid) > CFG['share']) == (CFG['side'] == lay.CN):
            lo = mid
        else:
            hi = mid
    tx = (lo + hi) / 2
    if 'ship_x' in CFG:
        u_ship = lay.uv(*lay.HOTSPOTS['ship'][:2])[0]
        along = (u_ship + (0.5 - CFG['ship_x']) * ortho) * lay.SQRT2 - tx
    else:
        along = CFG['along']
    u_c, v_c = lay.uv(tx, along)
    half_v = _half_height_v()
    return {
        'target': (tx, along, 0.0),
        'ortho': ortho,
        'u': (u_c - ortho / 2, u_c + ortho / 2),
        'v': (v_c - half_v, v_c + half_v),
    }


def setup_camera(scene, framing: dict):
    cam_data = bpy.data.cameras.new('cam')
    cam_data.type = 'ORTHO'
    cam_data.sensor_fit = 'HORIZONTAL'      # ortho_scale is the frame width, portrait frames included
    cam_data.ortho_scale = framing['ortho']
    cam_data.clip_end = 1000
    cam = bpy.data.objects.new('cam', cam_data)
    scene.collection.objects.link(cam)
    az, el = math.radians(CAM_AZIMUTH), math.radians(CAM_ELEVATION)
    direction = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    target = Vector(framing['target'])
    cam.location = target + direction * 150
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    log.info('camera ortho %.1f target (%.1f, %.1f)', framing['ortho'], *framing['target'][:2])
    return cam


def setup_light(scene) -> None:
    sun_data = bpy.data.lights.new('sun', 'SUN')
    sun_data.energy = 3.6
    sun_data.angle = math.radians(9)
    for attr, value in (('use_shadow_jitter', True), ('shadow_jitter_overblur', 10.0)):
        if hasattr(sun_data, attr):                # EEVEE soft shadows
            setattr(sun_data, attr, value)
    sun = bpy.data.objects.new('sun', sun_data)
    scene.collection.objects.link(sun)
    travel = Vector((0.75, -0.25, -1.0)).normalized()
    sun.rotation_euler = travel.to_track_quat('-Z', 'Y').to_euler()

    world = bpy.data.worlds.new('world')
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = lin('#dde6f1')
    bg.inputs['Strength'].default_value = 1.0
    scene.world = world


def setup_render(scene, resolution: tuple, samples: int) -> None:
    for engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = samples
    if hasattr(scene.eevee, 'use_raytracing'):
        scene.eevee.use_raytracing = True
    for vt in ('AgX', 'Filmic'):
        try:
            scene.view_settings.view_transform = vt
            break
        except TypeError:
            continue
    try:
        scene.view_settings.look = VIEW_LOOK
    except TypeError:
        log.warning('look %r not available, keeping default', VIEW_LOOK)
    scene.view_settings.exposure = EXPOSURE
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 15


def export_screen_coords(scene, cam) -> None:
    # The projection follows the render's aspect ratio, so set the variant's size first.
    scene.render.resolution_x, scene.render.resolution_y = CFG['still'][MODE]
    scene.render.resolution_percentage = 100
    bpy.context.view_layer.update()  # camera matrix_world is stale until the depsgraph updates

    def proj(co: tuple) -> dict:
        v = world_to_camera_view(scene, cam, Vector(co))
        return {'x': round(v.x * 100, 2), 'y': round((1 - v.y) * 100, 2)}

    data = {
        'hotspots': {k: proj(v) for k, v in lay.HOTSPOTS.items()},
        'frames': FRAMES if MODE in CFG['video'] else 0,
        'fps': FPS,
        'video': list(CFG['video'][MODE]) if MODE in CFG['video'] else None,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2)
    (x0, x1), (y0, y1) = CFG['bands']
    for k, p in data['hotspots'].items():
        if not (x0 * 100 <= p['x'] <= x1 * 100 and y0 * 100 <= p['y'] <= y1 * 100):
            log.warning('hotspot %s outside the safe bands: %s', k, p)
    log.info('wrote %s', OUT_JSON)


# ── Build + render ────────────────────────────────────────────────────────
def build_scene(scene) -> dict:
    mats, waves = build_materials()
    logo.load_logos()
    veh.init(mats, scene.collection)
    layout = lay.LAYOUTS[VARIANT]
    crane = lay.build_zones(layout)                 # records HOTSPOTS and the crane's travel
    framing = frame_composition()
    lay.set_window(framing['u'], framing['v'])
    lay.build_ground()
    lay.build_decor(layout)
    B.finalize(mats, scene.collection)
    trolley = veh.crane_trolley(crane['x_ship'], crane['y'], crane['z'])
    movers = veh.populate(lay.traffic_lanes())
    log.info('%d moving vehicles', len(movers))
    veh.bake(movers, FRAMES, crane=(trolley, crane['x_ship'], crane['x_quay']),
             water_nodes=((waves[0], 2), (waves[1], -1)))
    return framing


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    framing = build_scene(scene)
    cam = setup_camera(scene, framing)
    setup_light(scene)
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 0, FRAMES - 1
    scene.frame_set(0)
    export_screen_coords(scene, cam)
    bpy.context.preferences.filepaths.save_version = 0   # no .blend1 backup next to the scene
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

    if MODE in CFG['video']:
        os.makedirs(FRAMES_DIR, exist_ok=True)
        setup_render(scene, CFG['video'][MODE], VIDEO_SAMPLES[MODE])
        scene.render.filepath = os.path.join(FRAMES_DIR, 'f_')
        bpy.ops.render.render(animation=True)
        log.info('wrote %d frames to %s', FRAMES, FRAMES_DIR)

    scene.frame_set(0)                                  # the poster is the loop's first frame
    setup_render(scene, CFG['still'][MODE], STILL_SAMPLES[MODE])
    scene.render.filepath = OUT_PNG
    bpy.ops.render.render(write_still=True)
    log.info('wrote %s', OUT_PNG)


main()
