
// ─── Slider ───────────────────────────────────────────────────────────────────
const slider   = document.querySelector('.hero-slider');
const slides   = document.querySelectorAll('.hero-slide');
const prevBtn  = document.querySelector('.prev-btn');
const nextBtn  = document.querySelector('.next-btn');
const dots     = document.querySelectorAll('.dot');

let currentIndex = 0;

function updateSlider() {
    if (slider) slider.style.transform = `translateX(-${currentIndex * 33.333}%)`;
    dots.forEach((dot, i) => dot.classList.toggle('active', i === currentIndex));
}

if (prevBtn) prevBtn.addEventListener('click', () => {
    currentIndex = currentIndex > 0 ? currentIndex - 1 : slides.length - 1;
    updateSlider();
});

if (nextBtn) nextBtn.addEventListener('click', () => {
    currentIndex = currentIndex < slides.length - 1 ? currentIndex + 1 : 0;
    updateSlider();
});

dots.forEach((dot, i) => dot.addEventListener('click', () => {
    currentIndex = i;
    updateSlider();
}));

setInterval(() => {
    currentIndex = currentIndex < slides.length - 1 ? currentIndex + 1 : 0;
    updateSlider();
}, 5000);


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


    // ─── Scroll reveal ────────────────────────────────────────────────────────
    const revealEls = document.querySelectorAll('.reveal');

    if (revealEls.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });

        revealEls.forEach(el => observer.observe(el));
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

    timelineBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const year = this.getAttribute('data-year');
            timelineBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            historySections.forEach(s => s.classList.remove('active'));
            const target = document.querySelector(`.history-section[data-year="${year}"]`);
            if (target) target.classList.add('active');
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
