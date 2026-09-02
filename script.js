
// ─── Slider ───────────────────────────────────────────────────────────────────
// Infinite loop via leading/trailing clones, so wrapping (last → first,
// first → last) always continues sliding in the same direction instead of
// snapping backward.
const slider  = document.querySelector('.hero-slider');
const slides  = document.querySelectorAll('.hero-slide');
const prevBtn = document.querySelector('.prev-btn');
const nextBtn = document.querySelector('.next-btn');
const dots    = document.querySelectorAll('.dot');

if (slider && slides.length > 1) {
    const total = slides.length;

    const firstClone = slides[0].cloneNode(true);
    const lastClone   = slides[total - 1].cloneNode(true);
    [firstClone, lastClone].forEach(clone => {
        clone.setAttribute('aria-hidden', 'true');
        clone.setAttribute('inert', '');
    });
    slider.appendChild(firstClone);
    slider.insertBefore(lastClone, slides[0]);

    const trackLength = total + 2;
    let position  = 1;   // DOM position within the track (0 = leading clone)
    let realIndex = 0;   // logical slide index (0..total-1), drives the dots
    let animating = false;

    function render(instant) {
        slider.style.transition = instant ? 'none' : '';
        slider.style.transform = `translateX(-${position * (100 / trackLength)}%)`;
        dots.forEach((dot, i) => dot.classList.toggle('active', i === realIndex));
    }

    render(true);

    // Timeout-based completion (not transitionend) so the carousel can never
    // get stuck: transitionend won't fire if the transform doesn't actually
    // change visually (e.g. a hidden/zero-width tab), which would otherwise
    // leave `animating` stuck true and permanently block further clicks.
    function finishTransition() {
        animating = false;
        if (position === trackLength - 1) {
            position = 1;
            render(true);
        } else if (position === 0) {
            position = trackLength - 2;
            render(true);
        }
    }

    function step(delta) {
        if (animating) return;
        animating = true;
        position  += delta;
        realIndex = (realIndex + delta + total) % total;
        render(false);
        setTimeout(finishTransition, 520);
    }

    function goToSlide(i) {
        if (animating || i === realIndex) return;
        animating = true;
        position  = i + 1;
        realIndex = i;
        render(false);
        setTimeout(finishTransition, 520);
    }

    if (prevBtn) prevBtn.addEventListener('click', () => step(-1));
    if (nextBtn) nextBtn.addEventListener('click', () => step(1));
    dots.forEach((dot, i) => dot.addEventListener('click', () => goToSlide(i)));

    setInterval(() => step(1), 5000);

    // ─── Touch swipe ────────────────────────────────────────────────────────
    let touchStartX = 0;
    slider.addEventListener('touchstart', e => { touchStartX = e.changedTouches[0].clientX; }, { passive: true });
    slider.addEventListener('touchend', e => {
        const delta = touchStartX - e.changedTouches[0].clientX;
        if (Math.abs(delta) < 40) return;
        step(delta > 0 ? 1 : -1);
    }, { passive: true });
}


// ─── Header scroll shadow ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const header = document.querySelector('header');

    if (header) {
        window.addEventListener('scroll', function () {
            header.classList.toggle('scrolled', window.pageYOffset > 50);
        });
    }


    // ─── Hamburger menu ───────────────────────────────────────────────────────
    const hamburger = document.querySelector('.hamburger');
    const navMenu   = document.querySelector('.nav-menu');

    if (hamburger && navMenu) {
        hamburger.addEventListener('click', () => {
            const isOpen = navMenu.classList.toggle('open');
            hamburger.classList.toggle('open', isOpen);
            hamburger.setAttribute('aria-expanded', isOpen);
        });

        navMenu.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('open');
                hamburger.classList.remove('open');
                hamburger.setAttribute('aria-expanded', 'false');
            });
        });

        document.addEventListener('click', e => {
            if (!header.contains(e.target)) {
                navMenu.classList.remove('open');
                hamburger.classList.remove('open');
                hamburger.setAttribute('aria-expanded', 'false');
            }
        });
    }


    // ─── Hide header on nav link click (prevents flash on new page) ──────────
    if (header) {
        header.querySelectorAll('a[href]').forEach(link => {
            link.addEventListener('click', function (e) {
                const href = this.getAttribute('href');
                if (href && !href.startsWith('#') && !href.startsWith('javascript')) {
                    header.style.opacity = '0';
                }
            });
        });
    }



    // ─── Back to top ──────────────────────────────────────────────────────────
    const backToTop = document.getElementById('back-to-top');

    if (backToTop) {
        window.addEventListener('scroll', () => {
            backToTop.classList.toggle('visible', window.pageYOffset > 400);
        });

        backToTop.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }


    // ─── Timeline (about page) ────────────────────────────────────────────────
    const timelineBtns    = document.querySelectorAll('.timeline-btn');
    const historySections = document.querySelectorAll('.history-section');
    let   histAnimating   = false;

    timelineBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            if (histAnimating) return;
            const year    = this.getAttribute('data-year');
            const current = document.querySelector('.history-section.active');
            const target  = document.querySelector(`.history-section[data-year="${year}"]`);

            if (!target || target === current) return;

            timelineBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            if (typeof gsap === 'undefined') {
                current.classList.remove('active');
                target.classList.add('active');
                return;
            }

            histAnimating = true;

            gsap.to(current, {
                opacity: 0, y: 10,
                duration: 0.22, ease: 'power2.in',
                onComplete() {
                    gsap.set(current, { clearProps: 'all' });
                    current.classList.remove('active');
                    target.classList.add('active');

                    const els = [
                        ...target.querySelectorAll('.ab-history-year, .ab-history-title, .ab-history-desc'),
                        ...target.querySelectorAll('.ab-history-img'),
                    ];
                    gsap.fromTo(els,
                        { opacity: 0, y: 20 },
                        {
                            opacity: 1, y: 0,
                            duration: 0.5, ease: 'power3.out',
                            stagger: 0.08,
                            onComplete() { histAnimating = false; }
                        }
                    );
                }
            });
        });
    });


    // ─── Gas element card scroll-to-center ───────────────────────────────────
    document.querySelectorAll('.ph-el[href]').forEach(card => {
        card.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').slice(1);
            const target = document.getElementById(targetId);
            if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    });


    // ─── Application cards background ────────────────────────────────────────
    document.querySelectorAll('.app-card[data-bg-index]').forEach(card => {
        const idx = card.getAttribute('data-bg-index');
        if (idx) card.style.backgroundImage = `url('applications_page_${idx}.jpg')`;
    });


    // ─── Applications search (FLIP) ───────────────────────────────────────────
    const searchInput = document.querySelector('#applicationsSearch');
    if (searchInput) {
        const normalize = s => (s || '').toLowerCase().trim();
        const grid  = document.querySelector('.applications-grid');
        const cards = Array.from(document.querySelectorAll('.app-card'));

        function flipAnimate(matched, beforeMutate) {
            const rects = new Map();
            matched.forEach(n => rects.set(n, n.getBoundingClientRect()));
            beforeMutate();
            matched.forEach(n => {
                const last  = n.getBoundingClientRect();
                const first = rects.get(n);
                const dx = first.left - last.left;
                const dy = first.top  - last.top;
                n.style.transition = 'none';
                n.style.transform  = `translate(${dx}px,${dy}px)`;
                n.style.opacity    = '1';
                n.getBoundingClientRect();
                n.style.transition = 'transform 450ms ease, opacity 400ms ease';
                n.style.transform  = 'translate(0,0)';
            });
        }

        searchInput.addEventListener('input', () => {
            const q       = normalize(searchInput.value);
            const matched = cards.filter(c => {
                const title = normalize(c.querySelector('.app-title')?.textContent);
                return !q || title.includes(q);
            });
            const unmatched = cards.filter(c => !matched.includes(c));

            flipAnimate(matched, () => {
                unmatched.forEach(n => { n.style.transition='none'; n.style.opacity='0'; n.style.display='none'; });
                matched.forEach(n   => { n.style.display=''; grid.appendChild(n); });
            });
        });
    }


    // ─── Products search (FLIP) ───────────────────────────────────────────────
    const productsSearch = document.querySelector('#productsSearch');
    if (productsSearch) {
        const normalize = s => (s || '').toLowerCase().trim();
        const grids = Array.from(document.querySelectorAll('.product-grid'));

        function applySearchToGrid(grid, query) {
            const cards     = Array.from(grid.querySelectorAll('.product-card'));
            const matched   = [];
            const unmatched = [];
            const rects     = new Map();

            cards.forEach(card => {
                const abbr  = card.querySelector('.product-abbreviation');
                const name  = card.querySelector('.product-fullname');
                const text  = normalize((abbr?.textContent||'') + ' ' + (name?.textContent||''));
                const match = !query || text.includes(query);
                (match ? matched : unmatched).push(card);
                if (match) rects.set(card, card.getBoundingClientRect());
            });

            unmatched.forEach(n => { n.style.transition='none'; n.style.opacity='0'; n.style.display='none'; });
            matched.forEach(n   => { n.style.display=''; grid.appendChild(n); });

            matched.forEach(n => {
                const last  = n.getBoundingClientRect();
                const first = rects.get(n) || last;
                const dx = first.left - last.left;
                const dy = first.top  - last.top;
                n.style.transition = 'none';
                n.style.transform  = `translate(${dx}px,${dy}px)`;
                n.getBoundingClientRect();
                n.style.transition = 'transform 450ms ease';
                n.style.transform  = 'translate(0,0)';
                n.style.opacity    = '1';
            });
        }

        productsSearch.addEventListener('input', () => {
            const q = normalize(productsSearch.value);
            grids.forEach(g => applySearchToGrid(g, q));
        });
    }
});
