// 轮播数据：现在使用运行时的 origin 来构建本地链接与图片地址（在本地 dev server 上如 http://0.0.0.0:8000 会生效）
(function(){
    const ORIGIN = (window.location && window.location.origin) ? window.location.origin : 'http://0.0.0.0:8000';

    // 数据顺序： Roller / Curtains / Shutters / Bamboo
    const carouselData = [
        {
            title: "HOME CREATOR",
            subtitle: "Rethinking Roller Blinds",
            link: ORIGIN + "/collections/custom-blockout-roller-blinds/",
            // 使用相对到 origin 的图片路径（确保这些资源能从本地 server 提供）
            backgroundImage: `url('${ORIGIN}/s/files/1/0677/9650/0800/files/white.jpg')`
        },
        {
            title: "HOME CREATOR",
            subtitle: "Beautiful Curtains",
            link: ORIGIN + "/collections/sheer-curtains/",
            backgroundImage: `url('${ORIGIN}/s/files/1/0677/9650/0800/files/curtains_banner.jpg')`
        },
        {
            title: "HOME CREATOR",
            subtitle: "Elegant Plantation Shutters",
            link: ORIGIN + "/collections/plantation-shutters/",
            backgroundImage: `url('${ORIGIN}/s/files/1/0677/9650/0800/files/shutters_banner.jpg')`
        },
        {
            title: "HOME CREATOR",
            subtitle: "Classical Bamboo & Jute Woven Blinds",
            link: ORIGIN + "/collections/bamboo-jute-woven-roman-blinds/",
            backgroundImage: `url('${ORIGIN}/s/files/1/0677/9650/0800/files/BW-2.jpg')`
        }
    ];

    // Broadcast helper
    function emitCarouselChanged(index) {
        const detail = { index, data: carouselData[index] || null };
        document.dispatchEvent(new CustomEvent('carousel:changed', { detail }));
    }

    function updateMobileContent(index) {
        const mobileContent = document.getElementById('mobile-carousel-content');
        const data = carouselData[index];
        if (mobileContent && data) {
            mobileContent.innerHTML = `
                <div>
                    <p class="mb-2 text-sm">${data.title}</p>
                    <h3 class="mb-4 text-2xl">${data.subtitle}</h3>
                    <a class="btn" href="${data.link}">Shop Now</a>
                </div>
            `;
        }
    }

    // SimpleCarousel 与 MainCarousel 类保持实现，唯一不同是现在使用上面的 carouselData
    class SimpleCarousel {
        constructor(element, options = {}) {
            this.element = element;
            this.slides = Array.from(element.querySelectorAll('.splide__slide'));
            this.currentIndex = 0;
            this.options = {
                autoplay: options.autoplay !== false,
                interval: options.interval || 4500,
                ...options
            };
            this.init();
        }

        init() {
            if (this.slides.length <= 1) return;
            this.createDots();
            this.createArrows();
            if (this.options.autoplay) this.startAutoplay();
            this.showSlide(0);
            this.element.classList.add('is-initialized');
        }

        createDots() {
            const dotsContainer = document.createElement('div');
            dotsContainer.className = 'splide__pagination';
            this.slides.forEach((_, index) => {
                const dot = document.createElement('button');
                dot.className = 'splide__pagination__page';
                dot.addEventListener('click', () => this.goToSlide(index));
                dotsContainer.appendChild(dot);
            });
            this.element.appendChild(dotsContainer);
            this.dots = dotsContainer.querySelectorAll('.splide__pagination__page');
        }

        createArrows() {
            const arrowsContainer = document.createElement('div');
            arrowsContainer.className = 'splide__arrows';
            const prev = document.createElement('button');
            prev.className = 'splide__arrow splide__arrow--prev';
            prev.innerHTML = '&#8592;';
            prev.addEventListener('click', () => this.prevSlide());
            const next = document.createElement('button');
            next.className = 'splide__arrow splide__arrow--next';
            next.innerHTML = '&#8594;';
            next.addEventListener('click', () => this.nextSlide());
            arrowsContainer.appendChild(prev);
            arrowsContainer.appendChild(next);
            this.element.appendChild(arrowsContainer);
        }

        showSlide(index) {
            this.slides.forEach((slide, i) => {
                slide.style.display = i === index ? 'block' : 'none';
            });
            if (this.dots) {
                this.dots.forEach((dot, i) => dot.classList.toggle('is-active', i === index));
            }
            this.currentIndex = index;
            updateMobileContent(index);
            emitCarouselChanged(index);
        }

        nextSlide() {
            const idx = (this.currentIndex + 1) % this.slides.length;
            this.showSlide(idx);
        }
        prevSlide() {
            const idx = (this.currentIndex - 1 + this.slides.length) % this.slides.length;
            this.showSlide(idx);
        }
        goToSlide(index) {
            this.showSlide(index);
            this.restartAutoplay();
        }
        startAutoplay() {
            this.autoplayTimer = setInterval(() => this.nextSlide(), this.options.interval);
        }
        stopAutoplay() {
            if (this.autoplayTimer) { clearInterval(this.autoplayTimer); this.autoplayTimer = null; }
        }
        restartAutoplay() {
            this.stopAutoplay();
            if (this.options.autoplay) this.startAutoplay();
        }
    }

    class MainCarousel {
        constructor() {
            this.currentSlide = 0;
            this.autoplayTimer = null;
            this.carousel = document.querySelector('.carousel-container');
            this.slides = Array.from(document.querySelectorAll('.slide'));
            this.indicatorsContainer = document.querySelector('.carousel-indicators');
            this.init();
        }

        init() {
            if (!this.carousel || this.slides.length === 0) return;
            this.initCarousel();
            this.createIndicatorsIfNeeded();
            // 保证显示第一个
            this.showSlide(0);
            this.addNavigationListeners();
            this.startAutoplay();
            this.addHoverPause();
        }

        initCarousel() {
            this.slides.forEach((slide, index) => {
                const data = carouselData[index];
                if (data) {
                    slide.style.backgroundImage = data.backgroundImage || '';
                    const title = slide.querySelector('h1');
                    const eyebrow = slide.querySelector('.eyebrow');
                    const link = slide.querySelector('.shop-now-btn');
                    if (eyebrow) eyebrow.textContent = data.title || '';
                    if (title) title.textContent = data.subtitle || '';
                    if (link) link.href = data.link || '#';
                }
            });
        }

        createIndicatorsIfNeeded() {
            if (!this.indicatorsContainer) {
                return;
            }
            this.indicatorsContainer.innerHTML = '';
            this.slides.forEach((_, i) => {
                const btn = document.createElement('button');
                btn.className = 'carousel-indicator';
                btn.setAttribute('aria-label', `Go to slide ${i+1}`);
                btn.dataset.index = i;
                btn.addEventListener('click', (e) => {
                    const idx = Number(e.currentTarget.dataset.index);
                    this.goToSlide(idx);
                });
                this.indicatorsContainer.appendChild(btn);
            });
            this.indicators = Array.from(this.indicatorsContainer.querySelectorAll('.carousel-indicator'));
        }

        updateIndicators(index) {
            if (!this.indicators) return;
            this.indicators.forEach((btn, i) => btn.classList.toggle('active', i === index));
        }

        showSlide(index) {
            this.slides.forEach((slide, i) => {
                if (i === index) {
                    slide.classList.add('active');
                    slide.setAttribute('aria-hidden', 'false');
                } else {
                    slide.classList.remove('active');
                    slide.setAttribute('aria-hidden', 'true');
                }
            });
            this.currentSlide = index;
            this.updateIndicators(index);
            updateMobileContent(index);
            emitCarouselChanged(index);
        }

        nextSlide() {
            const nextIndex = (this.currentSlide + 1) % this.slides.length;
            this.showSlide(nextIndex);
        }

        prevSlide() {
            const prevIndex = (this.currentSlide - 1 + this.slides.length) % this.slides.length;
            this.showSlide(prevIndex);
        }

        goToSlide(index) {
            this.showSlide(index);
            this.restartAutoplay();
        }

        addNavigationListeners() {
            const nextBtn = document.querySelector('.carousel-next');
            const prevBtn = document.querySelector('.carousel-prev');

            if (nextBtn) nextBtn.addEventListener('click', () => { this.nextSlide(); this.restartAutoplay(); });
            if (prevBtn) prevBtn.addEventListener('click', () => { this.prevSlide(); this.restartAutoplay(); });

            document.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowLeft') { this.prevSlide(); this.restartAutoplay(); }
                if (e.key === 'ArrowRight') { this.nextSlide(); this.restartAutoplay(); }
            });
        }

        startAutoplay() {
            this.autoplayTimer = setInterval(() => this.nextSlide(), 5000);
        }

        stopAutoplay() {
            if (this.autoplayTimer) { clearInterval(this.autoplayTimer); this.autoplayTimer = null; }
        }

        restartAutoplay() {
            this.stopAutoplay();
            this.startAutoplay();
        }

        addHoverPause() {
            if (!this.carousel) return;
            this.carousel.addEventListener('mouseenter', () => this.stopAutoplay());
            this.carousel.addEventListener('mouseleave', () => this.startAutoplay());
        }
    }

    // 初始化
    document.addEventListener('DOMContentLoaded', function() {
        const splideElements = document.querySelectorAll('.splide:not(.is-initialized)');
        splideElements.forEach(element => {
            new SimpleCarousel(element, { autoplay: true, interval: 4500 });
        });

        // main carousel
        new MainCarousel();

        // 兼容外部 Splide（若存在）
        setTimeout(() => {
            const splideEl = document.querySelector('.splide');
            if (splideEl && splideEl.splide && typeof splideEl.splide.on === 'function') {
                splideEl.splide.on('moved', (newIndex) => {
                    emitCarouselChanged(newIndex);
                    updateMobileContent(newIndex);
                });
            }
        }, 500);
    });

})();