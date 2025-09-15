// 增强的平滑滚动实现
class SmoothScroll {
    constructor(options = {}) {
        this.options = {
            duration: 800,
            easing: 'easeInOutCubic',
            offset: 0,
            ...options
        };
        
        this.init();
    }
    
    init() {
        // 拦截所有内部链接点击
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href^="#"]');
            if (link) {
                e.preventDefault();
                const targetId = link.getAttribute('href').substring(1);
                this.scrollToElement(targetId);
            }
        });
        
        // 初始化视差滚动
        this.initParallax();
        
        // 初始化滚动动画
        this.initScrollAnimations();
    }
    
    // 平滑滚动到指定元素
    scrollToElement(targetId) {
        const targetElement = document.getElementById(targetId);
        if (!targetElement) return;
        
        const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - this.options.offset;
        this.smoothScrollTo(targetPosition);
    }
    
    // 平滑滚动到指定位置
    smoothScrollTo(targetPosition) {
        const startPosition = window.pageYOffset;
        const distance = targetPosition - startPosition;
        const startTime = performance.now();
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / this.options.duration, 1);
            
            const easeProgress = this.easing(progress);
            window.scrollTo(0, startPosition + (distance * easeProgress));
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }
    
    // 缓动函数
    easing(t) {
        switch (this.options.easing) {
            case 'easeInOutCubic':
                return t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1;
            case 'easeInOutQuart':
                return t < 0.5 ? 8 * t * t * t * t : 1 - 8 * (--t) * t * t * t;
            case 'easeInOutQuint':
                return t < 0.5 ? 16 * t * t * t * t * t : 1 + 16 * (--t) * t * t * t * t;
            default:
                return t;
        }
    }
    
    // 初始化视差滚动
    initParallax() {
        const parallaxElements = document.querySelectorAll('[data-parallax]');
        
        if (parallaxElements.length === 0) return;
        
        let ticking = false;
        
        const updateParallax = () => {
            const scrolled = window.pageYOffset;
            
            parallaxElements.forEach(element => {
                const speed = parseFloat(element.dataset.parallax) || 0.5;
                const yPos = -(scrolled * speed);
                element.style.transform = `translateY(${yPos}px)`;
            });
            
            ticking = false;
        };
        
        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(updateParallax);
                ticking = true;
            }
        });
    }
    
    // 初始化滚动动画
    initScrollAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -100px 0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in-on-scroll');
                }
            });
        }, observerOptions);
        
        // 观察所有可动画元素
        const animatableElements = document.querySelectorAll('.animate-on-scroll, .card, .gallery-item');
        animatableElements.forEach(el => observer.observe(el));
    }
}

// 初始化平滑滚动
document.addEventListener('DOMContentLoaded', () => {
    new SmoothScroll({
        duration: 1000,
        easing: 'easeInOutCubic',
        offset: 80
    });
});