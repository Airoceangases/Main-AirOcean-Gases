"""Encode the rendered frame loop into the MP4 the hero plays, using Blender's built-in FFmpeg.

Usage (from the site root, after airocean_scene.py --final or --anim-preview):
    blender -b -P scene-src/encode_video.py                    desktop loop
    blender -b -P scene-src/encode_video.py -- --portrait      phone loop

Reads scene-src/out/hero-scene[-portrait].json (frame count, fps, size) and
scene-src/out/frames[-portrait]/f_####.png; writes images/hero-scene[-portrait].mp4 (H.264, no
audio). build_preview.py then moves the MP4 index to the front of the file so playback can start
before the download finishes.
"""
import glob
import json
import logging
import os
import sys

import bpy

logging.basicConfig(level=logging.INFO, format='[encode] %(message)s')
log = logging.getLogger('encode')

ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SUFFIX = '-portrait' if '--portrait' in ARGV else ''
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
INFO_JSON = os.path.join(HERE, 'out', f'hero-scene{SUFFIX}.json')
FRAMES_DIR = os.path.join(HERE, 'out', f'frames{SUFFIX}')
TMP_PREFIX = os.path.join(HERE, 'out', f'encode{SUFFIX}_')
OUT_MP4 = os.path.join(SITE, 'images', f'hero-scene{SUFFIX}.mp4')
QUALITY = 'HIGH'                # Blender's CRF preset: HIGH keeps the small, zoomed-out details crisp


def frame_files() -> tuple:
    with open(INFO_JSON, encoding='utf-8') as fh:
        info = json.load(fh)
    if not info.get('frames'):
        raise SystemExit('no frame loop recorded: render with --final or --anim-preview first')
    files = [os.path.join(FRAMES_DIR, f'f_{i:04d}.png') for i in range(info['frames'])]
    missing = [f for f in files if not os.path.exists(f)]
    if missing:
        raise SystemExit(f'{len(missing)} frames missing, e.g. {missing[0]}')
    return files, info['fps'], info['video']


def setup_sequence(scene, files: list, fps: int, size: list) -> None:
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.frame_start, scene.frame_end = 1, len(files)
    editor = scene.sequence_editor_create()
    # Blender 5 renamed `sequences` to `strips`; test the attribute, not truthiness (it starts empty).
    strips = editor.strips if hasattr(editor, 'strips') else editor.sequences
    strip = strips.new_image(name='loop', filepath=files[0], channel=1, frame_start=1)
    for path in files[1:]:
        strip.elements.append(os.path.basename(path))
    scene.view_settings.view_transform = 'Standard'   # frames already carry the AgX look
    scene.view_settings.look = 'None'


def setup_output(scene, fps: int) -> None:
    settings = scene.render.image_settings
    if hasattr(settings, 'media_type'):              # Blender 4.5+ splits image / video output
        settings.media_type = 'VIDEO'
    settings.file_format = 'FFMPEG'
    ff = scene.render.ffmpeg
    ff.format = 'MPEG4'
    ff.codec = 'H264'
    ff.constant_rate_factor = QUALITY
    ff.ffmpeg_preset = 'BEST'
    ff.gopsize = fps * 2
    ff.audio_codec = 'NONE'
    scene.render.filepath = TMP_PREFIX


def main() -> None:
    files, fps, size = frame_files()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    setup_sequence(scene, files, fps, size)
    setup_output(scene, fps)
    for stale in glob.glob(TMP_PREFIX + '*.mp4'):
        os.remove(stale)
    bpy.ops.render.render(animation=True)
    produced = glob.glob(TMP_PREFIX + '*.mp4')
    if len(produced) != 1:
        raise SystemExit(f'expected one encoded file, found {produced}')
    os.replace(produced[0], OUT_MP4)
    log.info('wrote %s (%d frames @ %d fps, %.2f MB)', OUT_MP4, len(files), fps,
             os.path.getsize(OUT_MP4) / 1048576)


main()
