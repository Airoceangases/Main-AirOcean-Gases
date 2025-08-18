



// 自动检测导航栏高度并调整内容区域位置
function adjustContentPosition() {
    const header = document.querySelector('header');
    const main = document.querySelector('main');
    const heroCarousel = document.querySelector('.hero-carousel');
    
    if (header && main) {
        const headerHeight = header.offsetHeight;
        // 添加1px的缓冲，确保完美衔接
        main.style.paddingTop = (headerHeight + 1) + 'px';
    }
    
    if (header && heroCarousel) {
        const headerHeight = header.offsetHeight;
        heroCarousel.style.marginTop = headerHeight + 'px';
        heroCarousel.style.height = `calc(100vh - ${headerHeight}px)`;
    }
}

// 轮播图逻辑
const slider = document.querySelector('.hero-slider');
const slides = document.querySelectorAll('.hero-slide');
const prevBtn = document.querySelector('.prev-btn');
const nextBtn = document.querySelector('.next-btn');
const dots = document.querySelectorAll('.dot');

let currentIndex = 0;

// 检查元素是否存在
if (!slider) {
    console.error('轮播图容器未找到');
}
if (!prevBtn) {
    console.error('上一张按钮未找到');
}
if (!nextBtn) {
    console.error('下一张按钮未找到');
}
if (dots.length === 0) {
    console.error('指示点未找到');
}

// 更新轮播图位置
function updateSlider() {
    if (slider) {
        slider.style.transform = `translateX(-${currentIndex * 33.333}%)`;
    }
    dots.forEach((dot, index) => {
        dot.classList.toggle('active', index === currentIndex);
    });
}

// 上一张
if (prevBtn) {
    prevBtn.addEventListener('click', () => {
        currentIndex = (currentIndex > 0) ? currentIndex - 1 : slides.length - 1;
        updateSlider();
    });
}

// 下一张
if (nextBtn) {
    nextBtn.addEventListener('click', () => {
        currentIndex = (currentIndex < slides.length - 1) ? currentIndex + 1 : 0;
        updateSlider();
    });
}

// 导航点点击
dots.forEach((dot, index) => {
    dot.addEventListener('click', () => {
        currentIndex = index;
        updateSlider();
    });
});

// 自动播放
setInterval(() => {
    currentIndex = (currentIndex < slides.length - 1) ? currentIndex + 1 : 0;
    updateSlider();
}, 5000);

// 自动检测导航栏高度并调整内容区域位置
function adjustContentPosition() {
    const header = document.querySelector('header');
    const heroCarousel = document.querySelector('.hero-carousel');
    
    if (header && heroCarousel) {
        const headerHeight = header.offsetHeight;
        heroCarousel.style.marginTop = headerHeight + 'px';
        heroCarousel.style.height = `calc(100vh - ${headerHeight}px)`;
    }
}

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    // 自动检测导航栏高度并调整内容区域位置
    adjustContentPosition();
    
    // 监听窗口大小变化，重新调整位置
    window.addEventListener('resize', adjustContentPosition);
    
    // 确保在图片加载完成后也重新调整位置
    window.addEventListener('load', adjustContentPosition);
    
    // 延迟执行一次调整，确保所有元素都已渲染
    setTimeout(adjustContentPosition, 100);
    
    // 导航栏滚动跟随功能 - 与styles.css保持一致
    const header = document.querySelector('header');
    
    if (header) {
        // 确保页面加载时导航栏立即显示
        header.style.opacity = '1';
        header.style.visibility = 'visible';
        header.style.transform = 'translateY(0)';
        
        // 滚动监听 - 简化版本，与styles.css保持一致
        window.addEventListener('scroll', function() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            
            // 当滚动超过50px时，添加scrolled类
            if (scrollTop > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        });
    }
    
    // 时间轴交互功能
    const timelineBtns = document.querySelectorAll('.timeline-btn');
    const historySections = document.querySelectorAll('.history-section');
    
    timelineBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const year = this.getAttribute('data-year');
            
            // 移除所有按钮的active类
            timelineBtns.forEach(b => b.classList.remove('active'));
            
            // 为当前按钮添加active类
            this.classList.add('active');
            
            // 隐藏所有历史部分
            historySections.forEach(section => {
                section.classList.remove('active');
            });
            
            // 显示对应的历史部分
            const targetSection = document.querySelector(`.history-section[data-year="${year}"]`);
            if (targetSection) {
                targetSection.classList.add('active');
            }
        });
    });

    // 应用案例：根据 data-bg-index 设置背景图
    // 约定命名：images/applications_page_{编号}.jpg
    // 例如 data-bg-index="12" → images/applications_page_12.jpg
    const appCards = document.querySelectorAll('.app-card[data-bg-index]');
    appCards.forEach(card => {
        const idx = card.getAttribute('data-bg-index');
        if (idx) {
            card.style.backgroundImage = `url('applications_page_${idx}.jpg')`;
        }
    });

    // 应用案例：搜索过滤 + 动画重排
    // 使用 FLIP 动画思路：First(记录初始) → Layout(改变顺序与显隐) → Invert(计算位移) → Play(过渡回0)
    // 搜索后：匹配项置顶并过渡到新位置；不匹配项淡出并隐藏（不占位）
    const searchInput = document.querySelector('#applicationsSearch');
    if (searchInput) {
        const normalize = s => (s || '').toLowerCase().trim();
        const grid = document.querySelector('.applications-grid');
        const cards = Array.from(document.querySelectorAll('.app-card'));

        // 对匹配集合执行 FLIP 动画；beforeMutate 中完成 DOM 变更（隐藏/重排）
        function flipAnimateMatched(matchedNodes, beforeMutate) {
            // 记录匹配项初始位置
            const firstRects = new Map();
            matchedNodes.forEach(node => firstRects.set(node, node.getBoundingClientRect()));

            // 执行布局变更（隐藏不匹配、重排匹配）
            beforeMutate();

            // 为匹配项应用 FLIP 动画
            matchedNodes.forEach(node => {
                const last = node.getBoundingClientRect();
                const first = firstRects.get(node);
                const dx = first.left - last.left;
                const dy = first.top - last.top;
                node.style.transition = 'none';
                node.style.transform = `translate(${dx}px, ${dy}px)`;
                node.style.opacity = '1';
                // 强制 reflow
                node.getBoundingClientRect();
                node.style.transition = 'transform 450ms ease, opacity 400ms ease';
                node.style.transform = 'translate(0, 0)';
            });
        }

        searchInput.addEventListener('input', () => {
            const q = normalize(searchInput.value);

            // 分组
            const matched = cards.filter(card => {
                const titleEl = card.querySelector('.app-title');
                const title = normalize(titleEl ? titleEl.textContent : '');
                return !q || title.includes(q);
            });
            const unmatched = cards.filter(card => !matched.includes(card));

            // 为匹配项做 FLIP，隐藏不匹配；匹配项 append 到容器末尾以实现“置顶”顺序
            flipAnimateMatched(matched, () => {
                // 隐藏不匹配
                unmatched.forEach(node => {
                    node.style.transition = 'none';
                    node.style.opacity = '0';
                    node.style.display = 'none';
                });
                // 显示匹配并重排至顶部
                matched.forEach(node => {
                    node.style.display = '';
                    grid.appendChild(node);
                });
            });
        });
    }

    // 产品页面：搜索过滤 + 动画重排
    // 说明：
    // - 支持页面结构中存在一个或多个 .product-grid
    // - 每个产品卡片使用 .product-card；匹配依据优先取 .product-abbreviation 与 .product-fullname 文本
    // - 搜索框元素 id 统一为 #productsSearch
    const productsSearchInput = document.querySelector('#productsSearch');
    if (productsSearchInput) {
        const normalize = s => (s || '').toLowerCase().trim();
        const grids = Array.from(document.querySelectorAll('.product-grid'));

        // 针对单个网格执行过滤与重排
        function applySearchToGrid(grid, query) {
            const cards = Array.from(grid.querySelectorAll('.product-card'));
            const matched = [];
            const unmatched = [];

            // 预记录匹配项初始 rect（FLIP First）
            const firstRects = new Map();
            cards.forEach(card => {
                const abbr = card.querySelector('.product-abbreviation');
                const name = card.querySelector('.product-fullname');
                const text = normalize((abbr?.textContent || '') + ' ' + (name?.textContent || ''));
                const isMatch = !query || text.includes(query);
                (isMatch ? matched : unmatched).push(card);
                if (isMatch) firstRects.set(card, card.getBoundingClientRect());
            });

            // 布局变更（Layout）：隐藏不匹配、显示匹配并置顶
            unmatched.forEach(node => {
                node.style.transition = 'none';
                node.style.opacity = '0';
                node.style.display = 'none';
            });
            matched.forEach(node => {
                node.style.display = '';
                grid.appendChild(node);
            });

            // FLIP Invert + Play：对匹配项做位移过渡
            matched.forEach(node => {
                const last = node.getBoundingClientRect();
                const first = firstRects.get(node) || last;
                const dx = first.left - last.left;
                const dy = first.top - last.top;
                node.style.transition = 'none';
                node.style.transform = `translate(${dx}px, ${dy}px)`;
                node.getBoundingClientRect();
                node.style.transition = 'transform 450ms ease';
                node.style.transform = 'translate(0, 0)';
                node.style.opacity = '1';
            });
        }

        // 绑定输入事件（多网格逐一处理）
        productsSearchInput.addEventListener('input', () => {
            const q = normalize(productsSearchInput.value);
            grids.forEach(grid => applySearchToGrid(grid, q));
        });
    }
});