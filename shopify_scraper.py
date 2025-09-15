import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from bs4 import BeautifulSoup
import os
import re
import time
import random
from urllib.parse import urljoin, urlparse, unquote, parse_qs, urlencode
from pathlib import Path
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import warnings
import cssutils
import shutil

# 忽略SSL警告（仅在测试时使用）
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# 忽略cssutils的日志
cssutils.log.setLevel(logging.CRITICAL)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ShopifyScraper:
    def __init__(self, base_url, max_depth=3, max_workers=5, timeout=30, use_proxy=False):
        """
        初始化 Shopify 站点抓取器
        """
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.max_depth = max_depth
        self.max_workers = max_workers
        self.timeout = timeout
        self.use_proxy = use_proxy
        
        # 创建会话对象，复用连接
        self.session = requests.Session()
        self.session.verify = True
        
        # 配置重试策略
        if Retry is not None:
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS"],
                backoff_factor=1
            )
            adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=100, pool_maxsize=100)
        else:
            adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100)
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        self.session.headers.update(self.headers)
        
        # 代理设置
        self.proxies = None
        if use_proxy:
            self.proxies = {'http': 'http://your-proxy:port', 'https': 'http://your-proxy:port'}
        
        # URL管理
        self.visited_urls = set()
        self.failed_urls = set()
        self.downloaded_resources = set()
        self.url_to_local_path = {}
        
        # 文件队列
        self.css_files_to_process = set()
        self.js_files_downloaded = set()
        self.js_files_to_process = set()
        self.dynamic_imports_found = set()
        
        # Shopify URL模式
        self.shopify_patterns = [
            r'/pages/[\w-]+',
            r'/collections/[\w-]+',
            r'/products/[\w-]+',
            r'/blogs/[\w-]+',
            r'/articles/[\w-]+',
            r'/policies/[\w-]+',
            r'/search'
        ]
        
        # 资源文件扩展名
        self.resource_extensions = {
            'css': ['.css'],
            'js': ['.js', '.mjs', '.jsx', '.ts', '.tsx', '.cjs'],
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico', '.avif'],
            'fonts': ['.woff', '.woff2', '.ttf', '.eot', '.otf']
        }
        
        # 创建基础目录
        self.base_dir = Path('dump')
        self.assets_dir = self.base_dir / 'assets'
        self.create_directories()
        
        # 保存抓取状态
        self.scrape_stats = {
            'pages_scraped': 0,
            'resources_downloaded': 0,
            'css_processed': 0,
            'js_downloaded': 0,
            'js_parsed': 0,
            'dynamic_imports': 0,
            'module_preloads': 0,
            'failed_pages': 0,
            'failed_resources': 0
        }
        
        self.special_file_mappings = {}
    
    def create_directories(self):
        self.base_dir.mkdir(exist_ok=True)
        self.assets_dir.mkdir(exist_ok=True)
        for subdir in ['css', 'js', 'images', 'fonts']:
            (self.assets_dir / subdir).mkdir(exist_ok=True)
        (self.base_dir / 'fonts').mkdir(exist_ok=True)
    
    def normalize_protocol_relative_url(self, url):
        if url.startswith('//'):
            parsed_base = urlparse(self.base_url)
            return f"{parsed_base.scheme}:{url}"
        return url
    
    def is_valid_url(self, url):
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != self.domain:
            return False
        exclude_patterns = [
            r'/cart', r'/checkout', r'/account', r'/admin',
            r'\.xml$', r'\.json$', r'\#', r'mailto:', r'tel:', r'javascript:',
            r'\?_data=routes'
        ]
        for pattern in exclude_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        return True
    
    def should_download_resource(self, url):
        if url.startswith('data:') or url.startswith('javascript:'):
            return False
        parsed = urlparse(url)
        if not parsed.netloc or parsed.netloc == self.domain:
            return True
        cdn_domains = [
            'cdn.shopify.com','cdn.jsdelivr.net','cdnjs.cloudflare.com',
            'unpkg.com','ajax.googleapis.com','maxcdn.bootstrapcdn.com',
            'fonts.googleapis.com','fonts.gstatic.com'
        ]
        for cdn in cdn_domains:
            if cdn in parsed.netloc:
                return True
        url_lower = url.lower()
        if any(url_lower.endswith(ext) for ext in ['.js', '.mjs', '.cjs', '.css']):
            return True
        return False
    
    def get_resource_type(self, url):
        url_lower = url.lower()
        url_without_query = url_lower.split('?')[0]
        for res_type, extensions in self.resource_extensions.items():
            for ext in extensions:
                if url_without_query.endswith(ext):
                    return res_type
        if any(k in url_lower for k in ['/js/', '/javascript/', '/scripts/']): return 'js'
        if any(k in url_lower for k in ['/css/', '/styles/', '/stylesheets/']): return 'css'
        if any(k in url_lower for k in ['/font', '/webfont']): return 'fonts'
        if any(k in url_lower for k in ['/img/', '/images/', '/pics/', '/pictures/']): return 'images'
        return None
    
    def normalize_url(self, url):
        url = self.normalize_protocol_relative_url(url)
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}{p.path}{'?' + p.query if p.query else ''}"
    
    def clean_url(self, url):
        url = self.normalize_protocol_relative_url(url)
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}{p.path}{'?' + p.query if p.query else ''}".rstrip('/')
    
    def get_local_path(self, url, is_page=True):
        url = self.normalize_protocol_relative_url(url)
        if url in self.url_to_local_path:
            return Path(self.url_to_local_path[url])
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if is_page:
            if not path:
                local_path = self.base_dir / 'index.html'
            else:
                clean_path = path.split('?')[0].rstrip('/')
                if clean_path.endswith('.html'):
                    local_path = self.base_dir / clean_path
                else:
                    local_path = self.base_dir / clean_path / 'index.html'
            if parsed.query:
                query_hash = hashlib.md5(parsed.query.encode()).hexdigest()[:8]
                parent = local_path.parent
                name = local_path.stem
                local_path = parent / f"{name}_{query_hash}.html"
        else:
            path = path.split('?')[0]
            if 'fonts.css' in path:
                if '/css/fonts.css' in url or path.endswith('css/fonts.css'):
                    local_path = self.base_dir / 'assets' / 'css' / 'fonts.css'
                else:
                    local_path = self.base_dir / 'fonts' / 'fonts.css'
            elif path:
                local_path = self.base_dir / path
            else:
                resource_type = self.get_resource_type(url)
                filename = hashlib.md5(url.encode()).hexdigest()[:10]
                ext_map = {'js': '.js','css': '.css','images': '.png','fonts': '.woff2'}
                ext = ext_map.get(resource_type, '.unknown')
                filename = filename + ext
                if resource_type:
                    local_path = self.assets_dir / resource_type / filename
                else:
                    local_path = self.assets_dir / filename
        self.url_to_local_path[url] = str(local_path)
        return local_path
    
    def save_content(self, content, file_path, is_binary=False):
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if is_binary:
                with open(file_path, 'wb') as f: f.write(content)
            else:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(content)
            logger.info(f"保存成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存失败 {file_path}: {e}")
            return False
    
    def extract_css_resources(self, css_content, css_url):
        resources = set()
        url_pattern = re.compile(r'url\(["\']?([^"\')\s]+)["\']?\)', re.IGNORECASE)
        for m in url_pattern.finditer(css_content):
            resource_url = m.group(1)
            if not resource_url.startswith('data:'):
                resource_url = self.normalize_protocol_relative_url(resource_url)
                absolute_url = urljoin(css_url, resource_url)
                resources.add(absolute_url)
        import_pattern = re.compile(r'@import\s+(?:url\(["\']?|["\'])([^"\')\s]+)["\']?\)?', re.IGNORECASE)
        for m in import_pattern.finditer(css_content):
            import_url = m.group(1)
            if not import_url.startswith('data:'):
                import_url = self.normalize_protocol_relative_url(import_url)
                absolute_url = urljoin(css_url, import_url)
                resources.add(absolute_url)
                self.css_files_to_process.add(absolute_url)
        return resources
    
    def extract_js_imports(self, js_content, js_url):
        imports = set()
        patterns = [
            re.compile(r'import\s*\(\s*["\']([^"\']+)["\']', re.IGNORECASE),
            re.compile(r'(?:import|from)\s+["\']([^"\']+)["\']', re.IGNORECASE),
            re.compile(r'require\s*\(\s*["\']([^"\']+)["\']', re.IGNORECASE),
        ]
        for pat in patterns:
            for m in pat.finditer(js_content):
                pth = m.group(1)
                if pth.startswith('http://') or pth.startswith('https://'):
                    imports.add(pth)
                elif not pth.startswith('data:') and not pth.startswith('#'):
                    if pth.startswith('./') or pth.startswith('../'):
                        imports.add(urljoin(js_url, pth))
                    elif pth.startswith('/'):
                        b = urlparse(self.base_url)
                        imports.add(f"{b.scheme}://{b.netloc}{pth}")
        if imports:
            self.scrape_stats['dynamic_imports'] += len(imports)
            logger.info(f"从JS文件 {js_url} 中发现 {len(imports)} 个导入")
        return imports
    
    def process_js_file(self, js_url, js_content):
        logger.info(f"解析JS文件中的导入: {js_url}")
        imports = self.extract_js_imports(js_content, js_url)
        for u in imports:
            if u not in self.downloaded_resources:
                self.dynamic_imports_found.add(u)
        self.scrape_stats['js_parsed'] += 1
        return imports
    
    def process_css_file(self, css_url, css_content):
        logger.info(f"处理CSS文件: {css_url}")
        resources = self.extract_css_resources(css_content, css_url)
        for r in resources:
            if r not in self.downloaded_resources:
                self.download_resource(r)
        css_local_path = self.get_local_path(css_url, is_page=False)
        def repl(m):
            u = m.group(1)
            if u.startswith('data:'): return m.group(0)
            u = self.normalize_protocol_relative_url(u)
            absolute = urljoin(css_url, u)
            local = self.get_local_path(absolute, is_page=False)
            try:
                rel = os.path.relpath(local, css_local_path.parent).replace('\\','/')
                return f'url("{rel}")'
            except Exception as e:
                logger.error(f"计算CSS相对路径失败: {e}")
                return m.group(0)
        url_pat = re.compile(r'url\(["\']?([^"\')\s]+)["\']?\)', re.IGNORECASE)
        processed = url_pat.sub(repl, css_content)
        self.scrape_stats['css_processed'] += 1
        return processed
    
    def download_resource(self, url):
        url = self.normalize_protocol_relative_url(url)
        if url in self.downloaded_resources: return
        if not self.should_download_resource(url):
            logger.debug(f"跳过资源: {url}"); return
        self.downloaded_resources.add(url)
        try:
            if not url.startswith('http'): url = urljoin(self.base_url, url)
            clean_url = self.clean_url(url)
            resp = self.session.get(clean_url, timeout=self.timeout, proxies=self.proxies, allow_redirects=True)
            resp.raise_for_status()
            ctype = resp.headers.get('content-type','').lower()
            is_css = clean_url.lower().endswith('.css') or 'text/css' in ctype
            is_js  = (any(clean_url.lower().endswith(ext) for ext in ['.js','.mjs','.cjs']) or 'javascript' in ctype)
            local = self.get_local_path(clean_url, is_page=False)
            if is_css:
                processed_css = self.process_css_file(clean_url, resp.text)
                if self.save_content(processed_css, local, is_binary=False):
                    self.scrape_stats['resources_downloaded'] += 1
                    logger.info(f"下载并处理CSS: {clean_url} -> {local}")
            elif is_js:
                if self.save_content(resp.content, local, is_binary=True):
                    self.scrape_stats['resources_downloaded'] += 1
                    self.scrape_stats['js_downloaded'] += 1
                    self.js_files_downloaded.add(clean_url)
                    self.js_files_to_process.add((clean_url, resp.text))
                    logger.info(f"成功下载JS文件: {clean_url} -> {local}")
            else:
                if self.save_content(resp.content, local, is_binary=True):
                    self.scrape_stats['resources_downloaded'] += 1
                    logger.info(f"下载资源: {clean_url} -> {local}")
        except Exception as e:
            self.scrape_stats['failed_resources'] += 1
            logger.error(f"资源下载失败 {url}: {e}")
    
    def extract_resources(self, soup, page_url):
        resources = set()
        # CSS
        for link in soup.find_all('link'):
            href = link.get('href')
            if href:
                href = self.normalize_protocol_relative_url(href)
                rel = link.get('rel', [])
                if isinstance(rel, str): rel = [rel]
                if 'stylesheet' in rel or ('preload' in rel and link.get('as') == 'style'):
                    resources.add(href)
                    if href.lower().endswith('.css'):
                        absolute_url = urljoin(page_url, href)
                        self.css_files_to_process.add(absolute_url)
                if 'modulepreload' in rel or 'moduleprefetch' in rel:
                    self.scrape_stats['module_preloads'] += 1
                    logger.info(f"发现modulepreload（将被移除）: {href}")
        # JS
        for script in soup.find_all('script'):
            src = script.get('src')
            if src:
                src = self.normalize_protocol_relative_url(src)
                resources.add(src)
        # IMG
        for img in soup.find_all('img'):
            for attr in ['src','data-src']:
                val = img.get(attr)
                if val:
                    val = self.normalize_protocol_relative_url(val)
                    resources.add(val)
            srcset = img.get('srcset')
            if srcset:
                for item in srcset.split(','):
                    u = item.strip().split(' ')[0]
                    if u:
                        u = self.normalize_protocol_relative_url(u)
                        resources.add(u)
        # style内的资源
        for elem in soup.find_all(style=True):
            style = elem.get('style','')
            urls = re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', style)
            for u in urls:
                u = self.normalize_protocol_relative_url(u)
                resources.add(u)
        return resources
    
    def extract_page_links(self, soup, current_url):
        links = set()
        for a in soup.find_all('a', href=True):
            href = a.get('href')
            if href:
                if '?_data=' in href:
                    href = href.split('?_data=')[0]
                href = self.normalize_protocol_relative_url(href)
                absolute = urljoin(current_url, href)
                norm = self.normalize_url(absolute)
                if self.is_valid_url(norm):
                    links.add(norm)
        return links
    
    def get_relative_path(self, from_path, to_path):
        try:
            from_path = Path(from_path)
            to_path = Path(to_path)
            if from_path.is_file() or (not from_path.exists() and from_path.suffix):
                from_path = from_path.parent
            relative = os.path.relpath(to_path, from_path).replace('\\','/')
            if relative == '../index.html': return '../'
            elif relative.endswith('/index.html'): return relative[:-10] + '/'
        # 修复：移除末尾的双斜杠
            relative = relative.rstrip('/')
            if relative and not relative.endswith('.html'):
                relative += '/'
            return relative
        except Exception as e:
            logger.error(f"计算相对路径失败: {e}")
            return '/' + str(to_path).replace('\\','/')
    
    def disable_client_side_routing(self, soup):
        # 移除 modulepreload
        for link in soup.find_all('link'):
            rel = link.get('rel', [])
            if isinstance(rel, str): rel = [rel]
            if 'modulepreload' in rel or 'moduleprefetch' in rel:
                link.decompose()
                logger.info("移除modulepreload/moduleprefetch链接")
        # 移除或修改 type=module
        for script in soup.find_all('script', {'type':'module'}):
            src = script.get('src','')
            if 'entry.client' in src or 'root' in src or '@remix-run' in src:
                script.decompose()
                logger.info(f"移除Remix入口脚本: {src}")
            else:
                del script['type']
        # 注入禁用脚本
        disable_script = soup.new_tag('script')
        disable_script.string = """
        (function(){
            if (window.__remixContext) delete window.__remixContext;
            if (window.__remixManifest) delete window.__remixManifest;
            if (window.__remixRouteModules) delete window.__remixRouteModules;
            const ofetch = window.fetch;
            window.fetch = function(...args){
                const u = typeof args[0]==='string'?args[0]:args[0].url;
                if(u && u.includes('_data=')){ return Promise.reject(new Error('Remix routing disabled')); }
                return ofetch.apply(this,args);
            };
            const oopen = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(m,u){
                if(u && u.includes('_data=')) throw new Error('Remix routing disabled');
                return oopen.apply(this,arguments);
            };
            document.addEventListener('click',function(e){
                const link = e.target.closest('a');
                if(link && link.href && !link.href.startsWith('javascript:') && !link.href.startsWith('#') && !link.target){
                    if(link.href.includes('?_data=')){
                        e.preventDefault();
                        window.location.href = link.href.split('?_data=')[0];
                    }
                }
            },true);
            const ops = history.pushState, ors = history.replaceState;
            history.pushState = function(s,t,u){ if(u && u.includes('_data=')) u = u.split('?_data=')[0]; if(u && u!==window.location.href){ window.location.href=u; return; } return ops.apply(this,arguments); };
            history.replaceState = function(s,t,u){ if(u && u.includes('_data=')) u = u.split('?_data=')[0]; return ors.apply(this,arguments); };
            console.log('SPA disabled');
        })();
        """
        if soup.head: soup.head.insert(0, disable_script)
        else:
            head = soup.new_tag('head'); head.append(disable_script); soup.html.insert(0, head)
        return soup
    
    def process_html(self, html_content, page_url):
        soup = BeautifulSoup(html_content, 'html.parser')
        current_page_path = self.get_local_path(page_url)
        
        # 1) 处理页面链接 (<a href>)：使用相对路径
        for a in soup.find_all('a', href=True):
            href = a.get('href')
            if href and not href.startswith(('#','mailto:','tel:','javascript:')):
                if '?_data=' in href:
                    href = href.split('?_data=')[0]
                    a['href'] = href
                href = self.normalize_protocol_relative_url(href)
                absolute_url = urljoin(page_url, href)
                normalized_url = self.normalize_url(absolute_url)
                if self.is_valid_url(normalized_url):
                    local_path = self.get_local_path(normalized_url)
                    rel = self.get_relative_path(current_page_path, local_path)
                    # 修复：清理双斜杠
                    rel = re.sub(r'/+', '/', rel)  # 将多个斜杠替换为单个斜杠
                    a['href'] = rel
        
        # 一个工具：把资源本地路径转换为根相对路径
        def to_root_relative(local_path: Path) -> str:
            root_rel = "/" + os.path.relpath(local_path, self.base_dir).replace("\\","/")
            return root_rel
        
        # 2) CSS <link>：根相对路径
        for link in soup.find_all('link'):
            href = link.get('href')
            if href:
                href = self.normalize_protocol_relative_url(href)
                if not href.startswith('http'):
                    href = urljoin(page_url, href)
                if self.should_download_resource(href):
                    local_path = self.get_local_path(href, is_page=False)
                    link['href'] = to_root_relative(local_path)
        
        # 3) JS <script src>：根相对路径
        for script in soup.find_all('script', {'src': True}):
            src = script.get('src')
            if src:
                src = self.normalize_protocol_relative_url(src)
                if not src.startswith('http'):
                    src = urljoin(page_url, src)
                if self.should_download_resource(src):
                    local_path = self.get_local_path(src, is_page=False)
                    script['src'] = to_root_relative(local_path)
        
        # 4) 图片 <img>：根相对路径（含 data-src）
        for img in soup.find_all('img'):
            for attr in ['src', 'data-src']:
                value = img.get(attr)
                if value and not value.startswith('data:'):
                    value = self.normalize_protocol_relative_url(value)
                    if not value.startswith('http'):
                        value = urljoin(page_url, value)
                    if self.should_download_resource(value):
                        local_path = self.get_local_path(value, is_page=False)
                        img[attr] = to_root_relative(local_path)
        
        return soup.prettify()
    
    def process_js_queue(self):
        logger.info(f"处理JS文件队列，共 {len(self.js_files_to_process)} 个文件")
        processed = set()
        max_iterations = 3
        iteration = 0
        while self.js_files_to_process and iteration < max_iterations:
            iteration += 1
            current_batch = list(self.js_files_to_process)
            self.js_files_to_process.clear()
            logger.info(f"第 {iteration} 轮JS解析，处理 {len(current_batch)} 个文件")
            for item in current_batch:
                if isinstance(item, tuple):
                    js_url, js_content = item
                else:
                    js_url = item; js_content = None
                if js_url in processed: continue
                processed.add(js_url)
                if js_content is None:
                    local_path = self.get_local_path(js_url, is_page=False)
                    if local_path.exists():
                        try:
                            with open(local_path, 'r', encoding='utf-8') as f:
                                js_content = f.read()
                        except Exception as e:
                            logger.error(f"读取JS文件失败 {local_path}: {e}")
                            continue
                    else:
                        if js_url not in self.downloaded_resources:
                            self.download_resource(js_url)
                        continue
                if js_content:
                    imports = self.process_js_file(js_url, js_content)
                    for import_url in imports:
                        if import_url not in self.downloaded_resources:
                            self.download_resource(import_url)
                            if any(import_url.lower().endswith(ext) for ext in ['.js','.mjs','.cjs']):
                                self.js_files_to_process.add((import_url, None))
        logger.info(f"下载 {len(self.dynamic_imports_found)} 个动态导入资源")
        for url in self.dynamic_imports_found:
            if url not in self.downloaded_resources:
                self.download_resource(url)
    
    def scrape_page(self, url, depth=0):
        if depth > self.max_depth: return []
        normalized_url = self.normalize_url(url)
        if normalized_url in self.visited_urls or normalized_url in self.failed_urls:
            return []
        self.visited_urls.add(normalized_url)
        logger.info(f"抓取页面 [深度:{depth}]: {normalized_url}")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt
                    logger.info(f"第 {attempt + 1} 次重试，等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                response = self.session.get(
                    normalized_url, timeout=self.timeout,
                    proxies=self.proxies, allow_redirects=True
                )
                response.raise_for_status()
                if not response.content: raise Exception("空响应内容")
                soup = BeautifulSoup(response.text, 'html.parser')
                resources = self.extract_resources(soup, normalized_url)
                logger.info(f"页面 {normalized_url} 找到 {len(resources)} 个资源")
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = [executor.submit(self.download_resource, res) for res in resources]
                    for fut in as_completed(futures):
                        try: fut.result()
                        except Exception as e: logger.error(f"资源下载错误: {e}")
                while self.css_files_to_process:
                    css_url = self.css_files_to_process.pop()
                    if css_url not in self.downloaded_resources:
                        self.download_resource(css_url)
                self.process_js_queue()
                page_links = self.extract_page_links(soup, normalized_url)
                processed_html = self.process_html(response.text, normalized_url)
                local_path = self.get_local_path(normalized_url)
                if self.save_content(processed_html, local_path, is_binary=False):
                    self.scrape_stats['pages_scraped'] += 1
                return list(page_links)
            except Exception as e:
                logger.error(f"页面抓取失败 {normalized_url}: {e}")
                if attempt == max_retries - 1:
                    self.failed_urls.add(normalized_url)
                    self.scrape_stats['failed_pages'] += 1
        return []
    
    def scrape_site(self):
        logger.info(f"开始抓取网站: {self.base_url}")
        logger.info(f"最大深度: {self.max_depth}")
        current_level = [self.base_url]
        for depth in range(self.max_depth + 1):
            if not current_level: break
            logger.info(f"\n--- 抓取第 {depth} 层，共 {len(current_level)} 个页面 ---")
            next_level = []
            for i, url in enumerate(current_level):
                if i > 0:
                    delay = 1 + random.uniform(0.5, 2)
                    logger.info(f"等待 {delay:.1f} 秒后继续...")
                    time.sleep(delay)
                new_links = self.scrape_page(url, depth)
                next_level.extend(new_links)
                if (i + 1) % 10 == 0:
                    logger.info("已抓取10个页面，暂停5秒...")
                    time.sleep(5)
            current_level = list(set(next_level) - self.visited_urls)
            prioritized, others = [], []
            for u in current_level:
                (prioritized if any(re.search(p, u) for p in self.shopify_patterns) else others).append(u)
            current_level = prioritized + others
            MAX_PAGES_PER_LEVEL = 50
            if len(current_level) > MAX_PAGES_PER_LEVEL:
                logger.info(f"发现 {len(current_level)} 个链接，限制为前 {MAX_PAGES_PER_LEVEL} 个")
                current_level = current_level[:MAX_PAGES_PER_LEVEL]
        logger.info("\n执行后处理...")
        self.process_js_queue()
        self.save_stats()
        logger.info("\n抓取完成！")
        self.print_stats()
    
    def save_stats(self):
        stats_file = self.base_dir / 'scrape_stats.json'
        url_mappings = {}
        for url, path in self.url_to_local_path.items():
            rel_path = os.path.relpath(path, self.base_dir)
            url_mappings[url] = rel_path.replace('\\', '/')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump({
                'base_url': self.base_url,
                'max_depth': self.max_depth,
                'stats': self.scrape_stats,
                'visited_urls': list(self.visited_urls),
                'failed_urls': list(self.failed_urls),
                'downloaded_resources': list(self.downloaded_resources),
                'js_files_downloaded': list(self.js_files_downloaded),
                'dynamic_imports_found': list(self.dynamic_imports_found),
                'url_mappings': url_mappings
            }, f, indent=2, ensure_ascii=False)
    
    def print_stats(self):
        print("\n" + "="*50)
        print("抓取统计:")
        print(f"  页面成功: {self.scrape_stats['pages_scraped']}")
        print(f"  页面失败: {self.scrape_stats['failed_pages']}")
        print(f"  资源下载: {self.scrape_stats['resources_downloaded']}")
        print(f"  JS文件下载: {self.scrape_stats['js_downloaded']}")
        print(f"  JS文件解析: {self.scrape_stats['js_parsed']}")
        print(f"  动态导入发现: {self.scrape_stats['dynamic_imports']}")
        print(f"  Module Preload (已移除): {self.scrape_stats['module_preloads']}")
        print(f"  CSS处理: {self.scrape_stats['css_processed']}")
        print(f"  资源失败: {self.scrape_stats['failed_resources']}")
        print(f"  总访问URL: {len(self.visited_urls)}")
        print(f"  总下载资源: {len(self.downloaded_resources)}")
        print("="*50)
        print("\n本地网站入口: dump/index.html")
        print("使用方法:")
        print("  1. cd dump")
        print("  2. python -m http.server 8000")
        print("  3. 在浏览器访问 http://localhost:8000")

def main():
    TARGET_URL = "https://www.homecreator.com.au"
    MAX_DEPTH = 3
    MAX_WORKERS = 3
    TIMEOUT = 30
    USE_PROXY = False
    
    scraper = ShopifyScraper(
        base_url=TARGET_URL,
        max_depth=MAX_DEPTH,
        max_workers=MAX_WORKERS,
        timeout=TIMEOUT,
        use_proxy=USE_PROXY
    )
    try:
        scraper.scrape_site()
    except KeyboardInterrupt:
        logger.info("\n用户中断抓取")
        scraper.print_stats()
    except Exception as e:
        logger.error(f"抓取出错: {e}")
        import traceback; traceback.print_exc()
        scraper.print_stats()

if __name__ == "__main__":
    main()
