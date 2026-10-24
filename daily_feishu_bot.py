import os
import json
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator  # 使用免费稳定的翻译库

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL")

def real_translate(text):
    """
    使用 deep-translator 将英文翻译为中文，实现真正的中英对照
    如果已经是中文则直接返回
    """
    if not text or len(text.strip()) == 0:
        return ""
    # 如果包含中文字符，直接返回
    if any("\u4e00" <= c <= "\u9fff" for c in text):
        return text
        
    try:
        # 调用谷歌翻译（免费、无需 Key）
        translated = GoogleTranslator(source='en', target='zh-CN').translate(text)
        return translated if translated else text
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def fetch_github_trending():
    """精准抓取 GitHub Trending 热门项目 (前 10 个)"""
    url = "https://github.com/trending"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            repo_rows = soup.select('article.Box-row')[:10]
            for row in repo_rows:
                a_tag = row.select_one('h2 a')
                if a_tag:
                    repo_name = a_tag.get_text(strip=True).replace("\n", "").replace(" ", "")
                    repo_url = "https://github.com" + a_tag['href']
                else:
                    continue
                
                desc_elem = row.select_one('p')
                repo_desc = desc_elem.get_text(strip=True) if desc_elem else "No description provided."
                
                items.append({
                    "title": repo_name,
                    "desc": repo_desc,
                    "url": repo_url
                })
    except Exception as e:
        print(f"Error fetching GitHub Trending: {e}")
        
    return items

def fetch_product_hunt():
    """抓取 Product Hunt 首页创意产品（去重防重复）"""
    url = "https://www.producthunt.com/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 查找 PH 首页的产品链接及标语
            # 通过提取带有 product 链接的元素
            seen_titles = set()
            for a in soup.select('a[href*="/posts/"]'):
                title = a.get_text(strip=True)
                href = a.get('href', '')
                if title and len(title) > 2 and title not in seen_titles:
                    seen_titles.add(title)
                    full_url = "https://www.producthunt.com" + href if not href.startswith("http") else href
                    items.append({
                        "title": title,
                        "desc": "Top trending product launched on Product Hunt today.",
                        "url": full_url
                    })
                if len(items) >= 10:
                    break
    except Exception as e:
        print(f"Error fetching Product Hunt: {e}")
        
    # 如果抓取为空，提供标准备用
    if not items:
        items = [{
            "title": f"Product Hunt Trending Item #{i+1}",
            "desc": "Explore top launched products on Product Hunt.",
            "url": "https://www.producthunt.com/"
        } for i in range(10)]
        
    return items[:10]

def fetch_indie_hackers():
    """精准抓取 Indie Hackers 讨论，过滤掉评论数等噪声"""
    url = "https://www.indiehackers.com/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 过滤标题：排除纯数字或带有 comments 字样的噪声
            for a in soup.select('a[href*="/post/"], a[href*="/discussion/"], h3 a'):
                title = a.get_text(strip=True)
                href = a.get('href', '')
                if title and "comments" not in title.lower() and len(title) > 10:
                    full_url = "https://www.indiehackers.com" + href if not href.startswith("http") else href
                    items.append({
                        "title": title,
                        "desc": "Real-world bootstrapping stories, revenue numbers, and marketing strategies.",
                        "url": full_url
                    })
                if len(items) >= 10:
                    break
    except Exception as e:
        print(f"Error fetching Indie Hackers: {e}")

    if len(items) < 10:
        for i in range(10 - len(items)):
            items.append({
                "title": f"Indie Hackers Startup Discussion #{i+1}",
                "desc": "Real-world bootstrapping stories, revenue numbers, and marketing strategies.",
                "url": "https://www.indiehackers.com/"
            })
            
    return items[:10]

def build_feishu_card():
    gh_items = fetch_github_trending()
    ph_items = fetch_product_hunt()
    ih_items = fetch_indie_hackers()
    
    content_lines = ["🌍 **全球创作者日报 | Global Creator Daily**\n"]
    
    # 1. GitHub 模块
    content_lines.append("---")
    content_lines.append("**🔥 GitHub 开源风向标 (Top 10)**")
    for idx, item in enumerate(gh_items, 1):
        zh_desc = real_translate(item['desc'])
        content_lines.append(
            f"{idx}. **[{item['title']}]({item['url']})**\n"
            f"   - 🇬🇧 EN: {item['desc']}\n"
            f"   - 🇨🇳 CN: {zh_desc}\n"
        )
        
    # 2. Product Hunt 模块
    content_lines.append("\n---")
    content_lines.append("**🚀 Product Hunt 创意产品 (Top 10)**")
    for idx, item in enumerate(ph_items, 1):
        zh_desc = real_translate(item['desc'])
        content_lines.append(
            f"{idx}. **[{item['title']}]({item['url']})**\n"
            f"   - 🇬🇧 EN: {item['desc']}\n"
            f"   - 🇨🇳 CN: {zh_desc}\n"
        )

    # 3. Indie Hackers 模块
    content_lines.append("\n---")
    content_lines.append("**💡 Indie Hackers 独立开发与变现 (Top 10)**")
    for idx, item in enumerate(ih_items, 1):
        zh_desc = real_translate(item['desc'])
        content_lines.append(
            f"{idx}. **[{item['title']}]({item['url']})**\n"
            f"   - 🇬🇧 EN: {item['desc']}\n"
            f"   - 🇨🇳 CN: {zh_desc}\n"
        )
        
    card_content = "\n".join(content_lines)
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "💡 每日全球开源与商业创意灵感"},
                "template": "blue"
            },
            "elements": [{
                "tag": "markdown",
                "content": card_content
            }]
        }
    }
    return payload

def send_to_feishu():
    if not FEISHU_WEBHOOK_URL:
        print("Error: FEISHU_WEBHOOK_URL is not set.")
        return
        
    payload = build_feishu_card()
    headers = {'Content-Type': 'application/json'}
    response = requests.post(FEISHU_WEBHOOK_URL, data=json.dumps(payload), headers=headers)
    print("Feishu Response:", response.json())

if __name__ == "__main__":
    send_to_feishu()
