/* ── Hero scene: hover cards on hotspots, industry tags, desktop/phone loop switching ──
   Mouse: hovering a blue point opens its card; leaving closes it after a short grace
   period so the pointer can travel onto the card. Touch/keyboard: tap or focus opens,
   tap outside / Esc / the close button closes. */
(function () {
    const hero = document.getElementById('hsHero');
    if (!hero) return;

    const header      = document.querySelector('header');
    const viewport    = document.getElementById('hsViewport');
    const stage       = hero.querySelector('.hs-stage');
    const film        = hero.querySelector('video.hs-img');   // the looping scene
    const spots       = Array.from(hero.querySelectorAll('.hs-spot'));
    const compact     = window.matchMedia('(max-width: 760px)');
    const reduced     = window.matchMedia('(prefers-reduced-motion: reduce)');
    const EDGE_GAP    = 8;     // px kept between an open card and the viewport edge
    const CLOSE_DELAY = 220;   // ms to move the pointer from a dot onto its card
    const flip = { l: 'r', r: 'l', t: 'b', b: 't' };
    let openSpot   = null;
    let closeTimer = 0;
    let refocusing = false;    // true while focus is handed back to a dot after closing

    const spotX = spot => parseFloat(spot.style.getPropertyValue('--x')) || 50;
    const spotY = spot => parseFloat(spot.style.getPropertyValue('--y')) || 50;

    /* Card photos load on the first interaction with the map, not with the page. */
    let photosRequested = false;
    function loadPhotos() {
        if (photosRequested) return;
        photosRequested = true;
        hero.querySelectorAll('.hs-card-media[data-src]').forEach(photo => {
            photo.src = photo.dataset.src;
            photo.removeAttribute('data-src');
        });
    }

    /* Area of `rect` hidden outside the (cropped) viewport. */
    function hiddenArea(rect, bounds) {
        const visibleW = Math.max(0, Math.min(rect.right, bounds.right - EDGE_GAP) - Math.max(rect.left, bounds.left + EDGE_GAP));
        const visibleH = Math.max(0, Math.min(rect.bottom, bounds.bottom - EDGE_GAP) - Math.max(rect.top, bounds.top + EDGE_GAP));
        return rect.width * rect.height - visibleW * visibleH;
    }

    /* Open the card away from the nearest frame edges, then try the other placements
       (flipped sides, then vertically centred on the dot) until one is fully visible. */
    function fitCard(spot) {
        const side = spotX(spot) > 60 ? 'l' : 'r';
        const vert = spotY(spot) < 45 ? 'b' : 't';
        spot.dataset.side = side;
        spot.dataset.vert = vert;
        if (compact.matches) return;

        const card    = spot.querySelector('.hs-card');
        const vp      = viewport.getBoundingClientRect();
        // The transparent fixed header floats over the top of the scene: keep cards below it.
        const headerBottom = header ? header.getBoundingClientRect().bottom : vp.top;
        const bounds  = { left: vp.left, right: vp.right, top: Math.max(vp.top, headerBottom), bottom: vp.bottom };
        const options = [[side, vert], [side, flip[vert]], [flip[side], vert],
                         [flip[side], flip[vert]], [side, 'm'], [flip[side], 'm']];
        let best = null;
        for (const [s, v] of options) {
            spot.dataset.side = s;
            spot.dataset.vert = v;
            const hidden = hiddenArea(card.getBoundingClientRect(), bounds);
            if (hidden === 0) return;
            if (!best || hidden < best.hidden) best = { s, v, hidden };
        }
        spot.dataset.side = best.s;
        spot.dataset.vert = best.v;
    }

    /* Industry tags sit right of their dot; a tag flips left when it would cover another
       dot or an earlier tag, or run past the edge of the map. */
    const tagged     = spots.filter(spot => spot.querySelector('.hs-tag'));
    const DOT_RADIUS = 15;     // half the dot's hit area
    const overlaps = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

    function placeTags() {
        const map  = stage.getBoundingClientRect();
        const shown = spots.filter(spot => spot.offsetParent !== null);   // phones hide Hongyuan's
        const dots = shown.map(spot => {
            const p = spot.getBoundingClientRect();          // zero-size anchor at the hotspot
            return { spot, rect: { left: p.left - DOT_RADIUS, right: p.left + DOT_RADIUS,
                                   top: p.top - DOT_RADIUS, bottom: p.top + DOT_RADIUS } };
        });
        const placed  = [];
        const blocked = (spot, rect) =>
            rect.left < map.left + EDGE_GAP || rect.right > map.right - EDGE_GAP
            || dots.some(d => d.spot !== spot && overlaps(rect, d.rect))
            || placed.some(r => overlaps(rect, r));
        tagged.forEach(spot => {
            const tag = spot.querySelector('.hs-tag');
            spot.dataset.tag = 'r';
            if (blocked(spot, tag.getBoundingClientRect())) {
                spot.dataset.tag = 'l';
                if (blocked(spot, tag.getBoundingClientRect())) spot.dataset.tag = 'r';
            }
            placed.push(tag.getBoundingClientRect());
        });
    }

    let tagFrame = 0;
    function schedulePlaceTags() {
        cancelAnimationFrame(tagFrame);
        tagFrame = requestAnimationFrame(placeTags);
    }

    function cancelClose() { clearTimeout(closeTimer); }
    function scheduleClose() {
        cancelClose();
        closeTimer = setTimeout(() => closeSpot(), CLOSE_DELAY);
    }

    function closeSpot({ returnFocus = false } = {}) {
        cancelClose();
        if (!openSpot) return;
        const dot = openSpot.querySelector('.hs-dot');
        openSpot.classList.remove('is-open');
        dot.setAttribute('aria-expanded', 'false');
        openSpot = null;
        if (returnFocus) {
            refocusing = true;
            dot.focus();
            refocusing = false;
        }
    }

    function openSpotCard(spot) {
        cancelClose();
        if (openSpot === spot) return;
        closeSpot();
        loadPhotos();
        openSpot = spot;
        spot.classList.add('is-open');
        spot.querySelector('.hs-dot').setAttribute('aria-expanded', 'true');
        fitCard(spot);
    }

    spots.forEach((spot, i) => {
        const dot = spot.querySelector('.hs-dot');
        spot.style.setProperty('--i', i);
        spot.addEventListener('pointerenter', event => {
            if (event.pointerType === 'mouse') openSpotCard(spot);
        });
        spot.addEventListener('pointerleave', event => {
            if (event.pointerType === 'mouse' && openSpot === spot) scheduleClose();
        });
        spot.addEventListener('focusin', () => { if (!refocusing) openSpotCard(spot); });
        spot.addEventListener('focusout', event => {
            if (openSpot === spot && !spot.contains(event.relatedTarget)) closeSpot();
        });
        dot.addEventListener('click', event => {
            event.stopPropagation();
            openSpotCard(spot);
        });
        spot.querySelector('.hs-card').addEventListener('click', event => event.stopPropagation());
        spot.querySelector('.hs-card-close').addEventListener('click', () => closeSpot({ returnFocus: true }));
        const tag = spot.querySelector('.hs-tag');
        if (tag) {
            tag.addEventListener('click', event => {     // a tap on the name opens the card too
                event.stopPropagation();
                openSpotCard(spot);
            });
        }
    });

    viewport.addEventListener('pointerenter', loadPhotos, { once: true });
    document.addEventListener('click', () => closeSpot());
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') closeSpot({ returnFocus: true });
    });

    /* The loop plays only while the hero is on screen and the visitor allows motion;
       otherwise the poster (the loop's first frame) stays up. */
    let onScreen = true;
    function syncPlayback() {
        if (!film) return;
        if (onScreen && !reduced.matches) {
            // A refused autoplay (e.g. data-saver) is fine: the poster simply stays visible.
            film.play().catch(() => {});
        } else {
            film.pause();
        }
    }
    if (film && 'IntersectionObserver' in window) {
        new IntersectionObserver(([entry]) => { onScreen = entry.isIntersecting; syncPlayback(); }).observe(hero);
    }
    reduced.addEventListener('change', syncPlayback);

    requestAnimationFrame(() => {        // the poster paints immediately; dots fade in over it
        placeTags();
        hero.classList.add('is-ready');
        syncPlayback();
    });

    window.addEventListener('resize', schedulePlaceTags);
    if (document.fonts) document.fonts.ready.then(schedulePlaceTags);   // icon font changes tag widths
    /* Crossing the phone breakpoint swaps between the desktop and the portrait loop: <source media>
       is only evaluated when the video loads, so reload it (the <picture> poster swaps by itself). */
    compact.addEventListener('change', () => {
        closeSpot();
        if (film) {
            film.load();
            syncPlayback();
        }
        schedulePlaceTags();
    });
})();
