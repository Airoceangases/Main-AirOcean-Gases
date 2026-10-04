"""Build the scene hero into hero-preview.html and, with --index, into index.html itself.

The hero section replaces index.html's old hero slider, or refreshes the scene hero once it is
installed, so the script can be re-run after every new render. Steps:
  1. Convert the posters scene-src/out/hero-scene.png (desktop) and hero-scene-portrait.png
     (phones), both from airocean_scene.py, into the WebP files the page loads, versioned by a
     content hash for cache-busting.
  2. Crop the hover-card photos from existing site images into images/hero-cards/.
  3. Fast-start both encoded loops (images/hero-scene.mp4 and hero-scene-portrait.mp4).
  4. Fill scene-src/hero-section.html with each hotspot's desktop and phone coordinates (from
     scene-src/out/hero-scene.json and hero-scene-portrait.json), the poster, video and card
     photo paths.
  5. Write hero-preview.html (noindex, no analytics) and, with --index, index.html (analytics and
     indexing kept; the previous index.html is first copied to scene-src/backup/, which is not
     deployed).

Usage (from the site root):
    python scene-src/build_preview.py            preview page only
    python scene-src/build_preview.py --index    also install the hero in index.html
"""
import hashlib
import json
import logging
import re
import shutil
import struct
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

logging.basicConfig(level=logging.INFO, format='[preview] %(message)s')
log = logging.getLogger('preview')

SITE = Path(__file__).resolve().parent.parent
SRC_PAGE = SITE / 'index.html'
OUT_PAGE = SITE / 'hero-preview.html'
BACKUP_DIR = SITE / 'scene-src' / 'backup'                      # .assetsignore keeps scene-src/ off the site
HERO_TEMPLATE = SITE / 'scene-src' / 'hero-section.html'
RENDER_DIR = SITE / 'scene-src' / 'out'
COORDS_JSON = RENDER_DIR / 'hero-scene.json'                     # desktop video
PORTRAIT_JSON = RENDER_DIR / 'hero-scene-portrait.json'          # phone video
# Each video's poster (its first frame): template placeholder -> (published WebP, width or None = full).
POSTERS = {
    'hero-scene.png': {'poster': ('hero-scene.webp', None), 'poster_1600': ('hero-scene-1600.webp', 1600)},
    'hero-scene-portrait.png': {'poster_portrait': ('hero-scene-portrait.webp', 1080)},
}
WEBP_QUALITY = 84

CARD_DIR = SITE / 'images' / 'hero-cards'
CARD_SIZE = (640, 300)
CARD_QUALITY = 80
# spot -> (source photo in images/, focal point x, y as fractions of the photo)
CARD_PHOTOS = {
    'asu':           ('about_page_1.jpg', 0.42, 0.72),          # Hongyuan plant, aerial
    'purification':  ('iso9001.jpg', 0.50, 0.45),               # Hongyuan cold boxes + tanks
    'filling':       ('gas-equipment.jpg', 0.42, 0.62),         # HY tanks + HY tanker truck
    'ship':          ('1780045380333.jpg', 0.60, 0.40),         # Airocean cages packed for shipment
    'hq':            ('gallery-gawda-handshake.jpg', 0.50, 0.48),
    'inventory':     ('gallery-neon-warehouse.jpg', 0.50, 0.50),
    'semiconductor': ('applications_page_90.jpg', 0.50, 0.50),
    'scientific':    ('industry_research.jpg', 0.50, 0.50),
    'aerospace':     ('applications_page_89.jpg', 0.50, 0.55),
    'window':        ('industry_window.jpg', 0.50, 0.50),
    'electrical':    ('applications_page_GIS.jpg', 0.50, 0.50),
    'lighting':      ('industry_lighting.jpg', 0.50, 0.50),
}
BLANK_GIF = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
VIDEOS = {'video': SITE / 'images' / 'hero-scene.mp4',                    # placeholder -> encoded loop
          'video_portrait': SITE / 'images' / 'hero-scene-portrait.mp4'}
MP4_CONTAINERS = {b'moov', b'trak', b'mdia', b'minf', b'stbl', b'edts', b'dinf', b'mvex', b'udta'}

HERO_BLOCK = re.compile(                        # index.html's original hero slider
    r'[ \t]*<!-- ═+\s*HERO SLIDER\s*═+ -->\s*'
    r'<section class="hero-slider-container hm-hero-wrap">.*?</section>\n',
    re.DOTALL,
)
SCENE_BLOCK = re.compile(                       # the scene hero, once installed (no nested <section>)
    r'[ \t]*<!-- ═+\s*HERO — SUPPLY-CHAIN SCENE.*?<section class="hs-hero".*?</section>\n',
    re.DOTALL,
)
HEADER_LOGO = '<img src="images/logo.png" alt="Airocean Gases Logo" class="logo-img">'
GTAG_BLOCK = re.compile(r'\s*<!-- Google tag \(gtag\.js\) -->.*?</script>\s*<script>.*?</script>', re.DOTALL)
PLACEHOLDER_POS = re.compile(r'\{\{pos:([a-z_]+)\}\}')


def versioned(path: Path) -> str:
    """Site-relative URL of a file with a short content hash as the ?v= cache-buster."""
    digest = hashlib.blake2b(path.read_bytes(), digest_size=4).hexdigest()
    return f'{path.relative_to(SITE).as_posix()}?v={digest}'


def export_posters() -> dict:
    """Write every poster WebP; return placeholder -> versioned URL."""
    urls = {}
    for render, outputs in POSTERS.items():
        with Image.open(RENDER_DIR / render) as img:
            rgb = img.convert('RGB')
        for key, (name, width) in outputs.items():
            out = rgb if width is None else rgb.resize(
                (width, round(rgb.height * width / rgb.width)), Image.LANCZOS)
            path = SITE / 'images' / name
            out.save(path, 'WEBP', quality=WEBP_QUALITY, method=6)
            urls[key] = versioned(path)
            log.info('wrote images/%s (%dx%d, %d KB)', name, out.width, out.height, path.stat().st_size // 1024)
    return urls


def crop_to(img: Image.Image, aspect: float, fx: float, fy: float) -> Image.Image:
    """Largest crop of `aspect` (w/h) centred as close to the focal point (fx, fy) as the image allows."""
    w, h = img.size
    cw, ch = (round(h * aspect), h) if w / h > aspect else (w, round(w / aspect))
    left = min(max(round(fx * w - cw / 2), 0), w - cw)
    top = min(max(round(fy * h - ch / 2), 0), h - ch)
    return img.crop((left, top, left + cw, top + ch))


def export_card_photos() -> dict:
    """Write one 640x300 WebP per hotspot card; return spot -> versioned URL."""
    CARD_DIR.mkdir(exist_ok=True)
    urls = {}
    for spot, (name, fx, fy) in CARD_PHOTOS.items():
        with Image.open(SITE / 'images' / name) as img:
            photo = crop_to(img.convert('RGB'), CARD_SIZE[0] / CARD_SIZE[1], fx, fy)
        path = CARD_DIR / f'{spot}.webp'
        photo.resize(CARD_SIZE, Image.LANCZOS).save(path, 'WEBP', quality=CARD_QUALITY, method=6)
        urls[spot] = versioned(path)
    total_kb = sum(p.stat().st_size for p in CARD_DIR.glob('*.webp')) // 1024
    log.info('wrote %d card photos to images/hero-cards/ (%d KB total)', len(urls), total_kb)
    return urls


def _mp4_boxes(data, start: int, end: int):
    """Yield (type, offset, size, header length) for the MP4 boxes in data[start:end]."""
    pos = start
    while pos + 8 <= end:
        size, kind = struct.unpack('>I4s', data[pos:pos + 8])
        header = 8
        if size == 1:
            size, header = struct.unpack('>Q', data[pos + 8:pos + 16])[0], 16
        elif size == 0:
            size = end - pos
        if size < header:
            raise ValueError(f'corrupt MP4 box {kind!r} at {pos}')
        yield kind, pos, size, header
        pos += size


def _shift_chunk_offsets(moov: bytearray, delta: int) -> None:
    """Add delta to every stco/co64 chunk offset inside the moov box."""
    def walk(start: int, end: int) -> None:
        for kind, pos, size, header in _mp4_boxes(moov, start, end):
            body = pos + header
            if kind in MP4_CONTAINERS:
                walk(body, pos + size)
            elif kind in (b'stco', b'co64'):
                fmt, width = ('>I', 4) if kind == b'stco' else ('>Q', 8)
                count = struct.unpack('>I', moov[body + 4:body + 8])[0]
                for i in range(count):
                    at = body + 8 + width * i
                    struct.pack_into(fmt, moov, at, struct.unpack(fmt, moov[at:at + width])[0] + delta)
    walk(0, len(moov))


def faststart(path: Path) -> bool:
    """Move the moov index in front of the media data (like `qt-faststart`) so browsers can
    start playing before the whole file has downloaded. Returns True if the file changed."""
    data = path.read_bytes()
    top = list(_mp4_boxes(data, 0, len(data)))
    kinds = [kind for kind, *_ in top]
    if b'moov' not in kinds or b'mdat' not in kinds:
        raise ValueError(f'{path.name} is not a playable MP4 (boxes: {kinds})')
    if kinds.index(b'moov') < kinds.index(b'mdat'):
        return False
    _, moov_pos, moov_size, _ = top[kinds.index(b'moov')]
    moov = bytearray(data[moov_pos:moov_pos + moov_size])
    _shift_chunk_offsets(moov, moov_size)
    out = bytearray()
    for kind, pos, size, _ in top:
        if kind == b'moov':
            continue
        if kind == b'mdat':
            out += moov
        out += data[pos:pos + size]
    path.write_bytes(bytes(out))
    return True


def prepare_videos() -> dict:
    """Fast-start both encoded loops; return placeholder -> versioned URL."""
    urls = {}
    for key, path in VIDEOS.items():
        if not path.exists():
            raise SystemExit(f'images/{path.name} is missing: run scene-src/encode_video.py first')
        moved = faststart(path)
        log.info('video images/%s: %.2f MB%s', path.name, path.stat().st_size / 1048576,
                 ', index moved to front' if moved else '')
        urls[key] = versioned(path)
    return urls


def spot_positions() -> dict:
    """Hotspot -> CSS custom properties: desktop --x/--y and phone --px/--py. A hotspot the phone
    video does not show (Hongyuan's) gets --pdisplay:none and is hidden on phones."""
    desktop = json.loads(COORDS_JSON.read_text(encoding='utf-8'))['hotspots']
    phone = json.loads(PORTRAIT_JSON.read_text(encoding='utf-8'))['hotspots']
    extra = set(phone) - set(desktop)
    if extra:
        log.warning('hotspots only in the phone video (not placed): %s', sorted(extra))
    positions = {}
    for key, p in desktop.items():
        q = phone.get(key)
        on_phone = f"--px:{q['x']}%;--py:{q['y']}%" if q else '--pdisplay:none'
        positions[key] = f"--x:{p['x']}%;--y:{p['y']}%;{on_phone}"
    return positions


def fill(pattern: str, values: dict, html: str, what: str) -> str:
    def lookup(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            raise KeyError(f'{what} {key!r} is in the template but has no value')
        return values[key]
    return re.sub(pattern, lookup, html)


def render_hero(media: dict, photos: dict) -> str:
    positions = spot_positions()
    html = HERO_TEMPLATE.read_text(encoding='utf-8').replace('{{blank}}', BLANK_GIF)
    html = fill(r'\{\{((?:poster|video)[a-z0-9_]*)\}\}', media, html, 'poster/video')
    html = fill(PLACEHOLDER_POS.pattern, positions, html, 'hotspot')
    html = fill(r'\{\{photo:([a-z_]+)\}\}', photos, html, 'card photo')
    leftover = re.findall(r'\{\{[^}]*\}\}', html)
    if leftover:
        raise ValueError(f'unfilled placeholders in {HERO_TEMPLATE.name}: {leftover}')
    unplaced = set(positions) - set(re.findall(r'data-spot="([a-z_]+)"', html))
    if unplaced:
        log.warning('hotspots rendered but not placed on the page: %s', sorted(unplaced))
    return html


def replace_once(text: str, old, new: str, label: str) -> str:
    """Replace exactly one occurrence of `old` (plain string or compiled regex); fail loudly otherwise."""
    if isinstance(old, re.Pattern):
        result, count = old.subn(lambda _m: new, text)
    else:
        count = text.count(old)
        result = text.replace(old, new)
    if count != 1:
        raise ValueError(f'{label}: expected exactly 1 match in {SRC_PAGE.name}, found {count}')
    return result


def ensure(text: str, marker: str, old: str, new: str, label: str) -> str:
    """replace_once(old -> new) unless `marker` shows the change is already there."""
    return text if marker in text else replace_once(text, old, new, label)


def install_hero(page: str, hero_html: str) -> str:
    """Swap the scene hero in for the old slider, or refresh the scene hero already installed."""
    slider, scene = len(HERO_BLOCK.findall(page)), len(SCENE_BLOCK.findall(page))
    if (slider, scene) not in ((1, 0), (0, 1)):
        raise ValueError(f'{SRC_PAGE.name}: expected one hero slider or one scene hero, '
                         f'found {slider} and {scene}')
    return replace_once(page, HERO_BLOCK if slider else SCENE_BLOCK, hero_html, 'hero block')


def build_page(hero_html: str, preview: bool) -> str:
    """index.html with the scene hero installed; the preview copy also drops analytics and indexing."""
    viewport = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    styles = '<link rel="stylesheet" href="styles.css">'
    script = '<script src="script.js"></script>'
    page = install_hero(SRC_PAGE.read_text(encoding='utf-8'), hero_html)
    page = ensure(page, 'href="hero-scene.css"', styles,
                  styles + '\n    <link rel="stylesheet" href="hero-scene.css">', 'stylesheet link')
    # Transparent header over the light scene: dark-text logo at the top, the usual white one once scrolled.
    page = ensure(page, '<header class="hs-on-light">', '<header>', '<header class="hs-on-light">', 'header tag')
    page = ensure(page, 'logo-img logo-dark', HEADER_LOGO,
                  HEADER_LOGO.replace('class="logo-img"', 'class="logo-img logo-light"')
                  + '<img src="images/logo_1.png" alt="Airocean Gases Logo" class="logo-img logo-dark">',
                  'header logo')
    page = ensure(page, 'src="hero-scene.js"', script,
                  script + '\n    <script src="hero-scene.js"></script>', 'script tag')
    if preview:
        page = replace_once(page, GTAG_BLOCK, '', 'analytics tag')
        page = replace_once(page, '<title>', '<title>[Preview] ', 'title')
        page = replace_once(page, viewport, viewport + '\n    <meta name="robots" content="noindex, nofollow">',
                            'viewport meta')
    return page


def newline_of(path: Path) -> str:
    """The file's own line ending, so rewriting it does not change every line."""
    return '\r\n' if b'\r\n' in path.read_bytes() else '\n'


def install_index(hero_html: str) -> None:
    """Back up index.html into scene-src/backup/, then write it with the scene hero installed
    (nothing is written or backed up when the page would not change)."""
    page = build_page(hero_html, preview=False)
    if page == SRC_PAGE.read_text(encoding='utf-8'):
        log.info('%s already up to date', SRC_PAGE.name)
        return
    newline = newline_of(SRC_PAGE)
    BACKUP_DIR.mkdir(exist_ok=True)
    backup = BACKUP_DIR / f'index-{datetime.now():%Y%m%d-%H%M%S}.html'
    shutil.copy2(SRC_PAGE, backup)
    SRC_PAGE.write_text(page, encoding='utf-8', newline=newline)
    log.info('wrote %s (previous version saved as %s)', SRC_PAGE.name, backup.relative_to(SITE).as_posix())


def main() -> int:
    media = {**export_posters(), **prepare_videos()}
    hero = render_hero(media, export_card_photos())
    if '--index' in sys.argv[1:]:
        install_index(hero)
    OUT_PAGE.write_text(build_page(hero, preview=True), encoding='utf-8')
    log.info('wrote %s', OUT_PAGE.name)
    return 0


if __name__ == '__main__':
    sys.exit(main())
