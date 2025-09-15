import os
import re
from pathlib import Path

def fix_dropdown_links(dump_dir):
    """修复下拉菜单中的链接"""
    dump_path = Path(dump_dir)
    
    # 首先检查实际存在的集合目录
    collections_dir = dump_path / 'collections'
    if collections_dir.exists():
        print("检查现有的集合目录:")
        for item in collections_dir.iterdir():
            if item.is_dir():
                print(f"  - {item.name}")
    
    # 修复所有HTML文件的下拉菜单链接
    html_files = dump_path.rglob('*.html')
    
    fixed_count = 0
    for html_file in html_files:
        if fix_dropdown_links_in_file(html_file):
            fixed_count += 1
    
    print(f"\n总共修复了 {fixed_count} 个文件的链接")

def fix_dropdown_links_in_file(file_path):
    """修复单个文件中的下拉菜单链接"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 查找现有的下拉菜单并更新链接
        if 'Custom made-to-order' in content and 'dropdown-content' in content:
            # 替换错误的链接为正确的链接
            link_replacements = {
                '/collections/sheer-curtains/': '/collections/sheer-curtains/',
                '/collections/plantation-shutters/': '/collections/plantation-shutters/',
                '/collections/bamboo-jute-woven-roman-blinds/': '/collections/bamboo-jute-woven-roman-blinds/',
                '/collections/roller-blinds/': '/collections/roller-blinds/'
            }
            
            # 应用链接替换
            for old_link, new_link in link_replacements.items():
                if old_link in content:
                    content = content.replace(old_link, new_link)
                    print(f"  替换链接: {old_link} -> {new_link}")
        
        # 如果找到下拉菜单，直接替换整个下拉内容以确保正确
        if 'nav-dropdown dropdown-content' in content:
            # 定义正确的下拉菜单HTML
            correct_dropdown = '''<div class="nav-dropdown dropdown-content">
                    <a href="/collections/plantation-shutters/">Plantation Shutters</a>
                    <a href="/collections/sheer-curtains/">S Fold Curtains</a>
                    <a href="/collections/bamboo-jute-woven-roman-blinds/">Bamboo & Jute Woven Roman Blinds</a>
                    <a href="/collections/roller-blinds/">Roller Blinds</a>
                </div>'''
            
            # 替换现有的下拉内容
            dropdown_pattern = r'<div class="nav-dropdown dropdown-content">.*?</div>'
            if re.search(dropdown_pattern, content, re.DOTALL):
                content = re.sub(dropdown_pattern, correct_dropdown, content, flags=re.DOTALL)
                print(f"  更新整个下拉菜单内容")
        
        # 如果内容有变化，写入文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"修复链接: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"修复链接失败 {file_path}: {e}")
        return False

def update_main_css_dropdown():
    """更新主CSS文件中的下拉菜单定义"""
    dump_path = Path('/home/fuxian/zouyufei/1500/dump')
    
    # 更新fix.py文件中的下拉菜单HTML
    fix_py_path = Path('/home/fuxian/zouyufei/1500/fix.py')
    if fix_py_path.exists():
        try:
            with open(fix_py_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换下拉菜单HTML中的链接
            old_dropdown = '''<div class="nav-dropdown dropdown-content">
                    <a href="/collections/plantation-shutters/">Plantation Shutters</a>
                    <a href="/collections/sheer-curtains/">S Fold Curtains</a>
                    <a href="/collections/bamboo-jute-woven-roman-blinds/">Bamboo & Jute Woven Roman Blinds</a>
                    <a href="/collections/roller-blinds/">Roller Blinds</a>
                </div>'''
            
            new_dropdown = '''<div class="nav-dropdown dropdown-content">
                    <a href="/collections/plantation-shutters/">Plantation Shutters</a>
                    <a href="/collections/sheer-curtains/">S Fold Curtains</a>
                    <a href="/collections/bamboo-jute-woven-roman-blinds/">Bamboo & Jute Woven Roman Blinds</a>
                    <a href="/collections/roller-blinds/">Roller Blinds</a>
                </div>'''
            
            if '/collections/sheer-curtains/' in content:
                content = content.replace('/collections/sheer-curtains/', '/collections/sheer-curtains/')
                content = content.replace('/collections/roller-blinds/', '/collections/roller-blinds/')
                
                with open(fix_py_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"更新了 {fix_py_path} 中的链接")
            
        except Exception as e:
            print(f"更新fix.py失败: {e}")

if __name__ == '__main__':
    print("修复下拉菜单链接...")
    
    # 更新fix.py文件
    update_main_css_dropdown()
    
    # 修复所有HTML文件
    fix_dropdown_links('/home/fuxian/zouyufei/1500/dump')
    
    print("\n链接修复完成！现在:")
    print("- S Fold Curtains -> /collections/sheer-curtains/")
    print("- Roller Blinds -> /collections/roller-blinds/")
    print("- 其他链接保持不变")