#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os
import json
import sys

def extract_correct_image_urls(html_content):
    """
    从HTML文件的remixContext中提取正确的图片URL
    
    Args:
        html_content: HTML文件内容
    
    Returns:
        图片URL列表，如果提取失败返回None
    """
    # 使用正则表达式找到remixContext部分
    remix_pattern = r'window\.__remixContext = ({.*?});'
    match = re.search(remix_pattern, html_content, re.DOTALL)
    
    if not match:
        print("错误：无法找到remixContext数据")
        return None
    
    try:
        # 解析JSON数据
        remix_data = json.loads(match.group(1))
        
        # 提取gallery中的图片URL
        gallery_nodes = remix_data['state']['loaderData']['routes/pages.$handle']['page']['gallery']['references']['nodes']
        
        # 提取所有图片URL
        image_urls = []
        for node in gallery_nodes:
            if 'image' in node and 'url' in node['image']:
                image_urls.append(node['image']['url'])
        
        return image_urls
        
    except (json.JSONDecodeError, KeyError) as e:
        print(f"解析错误: {e}")
        return None


def fix_gallery_html(file_path):
    """
    修复单个gallery HTML文件的图片显示问题
    
    Args:
        file_path: HTML文件的路径
    
    Returns:
        True表示修复成功，False表示失败
    """
    
    print(f"\n处理文件: {file_path}")
    print("-" * 50)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误：文件不存在 - {file_path}")
        return False
    
    # 读取HTML文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"读取文件失败: {e}")
        return False
    
    # 提取正确的图片URL
    image_urls = extract_correct_image_urls(html_content)
    
    if not image_urls:
        print("无法提取图片URL")
        return False
    
    print(f"找到 {len(image_urls)} 个图片URL")
    
    # 构建新的JavaScript代码
    images_js = json.dumps(image_urls, indent=2)
    new_images_line = f'const images = {images_js};'
    
    # 定义多个可能的错误模式
    patterns = [
        # 模式1: roller_blind_x.jpg
        r'const images = \["https://cdn\.shopify\.com/s/files/1/0677/9650/0800/files/roller_blind_[^"]+\.jpg"(?:,"https://cdn\.shopify\.com/s/files/1/0677/9650/0800/files/roller_blind_[^"]+\.jpg")*\];',
        # 模式2: curtain_x.jpg
        r'const images = \["https://cdn\.shopify\.com/s/files/1/0677/9650/0800/files/curtain_[^"]+\.jpg"(?:,"https://cdn\.shopify\.com/s/files/1/0677/9650/0800/files/curtain_[^"]+\.jpg")*\];',
        # 模式3: bamboo_blind_x.jpg
        r'const images = \["https://cdn\.shopify\.com/s/files/1/0677/9650/0800/files/bamboo_blind_[^"]+\.jpg"(?:,"https://cdn\.shopify\.com/s/files/1/0677/9650/0800/files/bamboo_blind_[^"]+\.jpg")*\];',
        # 通用模式（最后的备选方案）
        r'const images = \[[^\]]*\];'
    ]
    
    # 尝试每个模式进行替换
    replaced = False
    for pattern in patterns:
        if re.search(pattern, html_content):
            html_content = re.sub(pattern, new_images_line, html_content)
            print(f"成功使用模式替换图片URL数组")
            replaced = True
            break
    
    if not replaced:
        print("警告：无法找到要替换的images数组")
        return False
    
    # 创建备份
    backup_path = file_path + '.backup'
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            with open(file_path, 'r', encoding='utf-8') as orig:
                f.write(orig.read())
        print(f"备份已保存到: {backup_path}")
    except Exception as e:
        print(f"创建备份失败: {e}")
    
    # 写入修复后的内容
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"文件已成功修复: {file_path}")
    except Exception as e:
        print(f"写入文件失败: {e}")
        return False
    
    # 显示修复后的图片列表
    print("\n修复后的图片URL列表：")
    for i, url in enumerate(image_urls, 1):
        filename = url.split('/')[-1].split('?')[0]
        print(f"  {i}. {filename}")
    
    return True


def main():
    """主函数 - 批量修复所有gallery文件"""
    
    # 定义需要修复的所有文件路径
    gallery_files = [
        {
            'name': 'Roller Blinds Gallery',
            'path': '/home/fuxian/zouyufei/1500/dump/pages/roller-blinds-gallery/index.html'
        },
        {
            'name': 'Curtains Gallery', 
            'path': '/home/fuxian/zouyufei/1500/dump/pages/curtains-gallery/index.html'
        },
        {
            'name': 'Bamboo & Jute Woven Roman Blinds Gallery',
            'path': '/home/fuxian/zouyufei/1500/dump/pages/bamboo-jute-woven-roman-blinds-gallery/index.html'
        }
    ]
    
    print("=" * 60)
    print("Gallery图片修复工具")
    print("=" * 60)
    
    # 如果提供了命令行参数，使用参数指定的文件
    if len(sys.argv) > 1:
        custom_files = []
        for arg in sys.argv[1:]:
            custom_files.append({
                'name': os.path.basename(arg),
                'path': arg
            })
        gallery_files = custom_files
        print(f"使用命令行参数指定的 {len(gallery_files)} 个文件")
    else:
        print(f"准备修复 {len(gallery_files)} 个默认gallery文件")
    
    # 统计结果
    success_count = 0
    failed_files = []
    
    # 处理每个文件
    for gallery in gallery_files:
        print(f"\n{'=' * 60}")
        print(f"正在修复: {gallery['name']}")
        
        if fix_gallery_html(gallery['path']):
            success_count += 1
        else:
            failed_files.append(gallery['name'])
    
    # 显示总结
    print("\n" + "=" * 60)
    print("修复完成！")
    print("=" * 60)
    print(f"✅ 成功修复: {success_count}/{len(gallery_files)} 个文件")
    
    if failed_files:
        print(f"❌ 修复失败的文件:")
        for name in failed_files:
            print(f"   - {name}")
    
    if success_count > 0:
        print("\n请刷新浏览器查看效果")
        print("如需恢复原始文件，可使用 .backup 备份文件")


if __name__ == "__main__":
    main()