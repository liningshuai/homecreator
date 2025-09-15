class GalleryManager {
    constructor(containerId, images) {
        this.container = document.getElementById(containerId);
        this.images = images;
        this.currentIndex = 0;
        this.init();
    }
    
    init() {
        if (!this.container || !this.images.length) return;
        
        this.createGalleryGrid();
        this.createLightbox();
    }
    
    createGalleryGrid() {
        const gridHtml = `
            <div class="gallery-grid grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
                ${this.images.map((img, index) => `
                    <div class="gallery-item cursor-pointer hover:opacity-80 transition-opacity" 
                         data-index="${index}">
                        <img src="${img.thumb}" 
                             alt="${img.title}" 
                             class="w-full h-48 object-cover rounded-lg shadow-md">
                        <p class="text-center mt-2 text-sm text-gray-600">${img.title}</p>
                    </div>
                `).join('')}
            </div>
        `;
        
        this.container.innerHTML = gridHtml;
        
        // 添加点击事件
        this.container.querySelectorAll('.gallery-item').forEach((item, index) => {
            item.addEventListener('click', () => this.openLightbox(index));
        });
    }
    
    createLightbox() {
        const lightboxHtml = `
            <div id="gallery-lightbox" class="fixed inset-0 bg-black bg-opacity-90 z-50 hidden">
                <div class="flex items-center justify-center h-full p-4">
                    <div class="relative max-w-4xl max-h-full">
                        <img id="lightbox-image" src="" alt="" class="max-w-full max-h-full object-contain">
                        <button id="lightbox-prev" class="absolute left-4 top-1/2 transform -translate-y-1/2 text-white text-2xl bg-black bg-opacity-50 rounded-full w-12 h-12 flex items-center justify-center hover:bg-opacity-75">‹</button>
                        <button id="lightbox-next" class="absolute right-4 top-1/2 transform -translate-y-1/2 text-white text-2xl bg-black bg-opacity-50 rounded-full w-12 h-12 flex items-center justify-center hover:bg-opacity-75">›</button>
                        <button id="lightbox-close" class="absolute top-4 right-4 text-white text-2xl bg-black bg-opacity-50 rounded-full w-10 h-10 flex items-center justify-center hover:bg-opacity-75">×</button>
                        <div id="lightbox-title" class="absolute bottom-4 left-4 right-4 text-white text-center bg-black bg-opacity-50 p-2 rounded"></div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', lightboxHtml);
        
        // 绑定lightbox事件
        this.bindLightboxEvents();
    }
    
    bindLightboxEvents() {
        const lightbox = document.getElementById('gallery-lightbox');
        const closeBtn = document.getElementById('lightbox-close');
        const prevBtn = document.getElementById('lightbox-prev');
        const nextBtn = document.getElementById('lightbox-next');
        
        closeBtn.addEventListener('click', () => this.closeLightbox());
        prevBtn.addEventListener('click', () => this.prevImage());
        nextBtn.addEventListener('click', () => this.nextImage());
        
        // 点击背景关闭
        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) this.closeLightbox();
        });
        
        // 键盘控制
        document.addEventListener('keydown', (e) => {
            if (!lightbox.classList.contains('hidden')) {
                switch(e.key) {
                    case 'Escape': this.closeLightbox(); break;
                    case 'ArrowLeft': this.prevImage(); break;
                    case 'ArrowRight': this.nextImage(); break;
                }
            }
        });
    }
    
    openLightbox(index) {
        this.currentIndex = index;
        this.updateLightboxImage();
        document.getElementById('gallery-lightbox').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
    
    closeLightbox() {
        document.getElementById('gallery-lightbox').classList.add('hidden');
        document.body.style.overflow = '';
    }
    
    prevImage() {
        this.currentIndex = (this.currentIndex - 1 + this.images.length) % this.images.length;
        this.updateLightboxImage();
    }
    
    nextImage() {
        this.currentIndex = (this.currentIndex + 1) % this.images.length;
        this.updateLightboxImage();
    }
    
    updateLightboxImage() {
        const img = document.getElementById('lightbox-image');
        const title = document.getElementById('lightbox-title');
        const current = this.images[this.currentIndex];
        
        img.src = current.full;
        img.alt = current.title;
        title.textContent = current.title;
    }
}