import os
import json
import requests
from bs4 import BeautifulSoup

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL")

def simple_translate(text):
    """
    轻量翻译函数：
    如果是纯中文，直接返回；如果是英文，转换为中文（此处可接入你喜欢的翻译API或保持简明翻译）
    """
    if not text:
        return ""
    # 如果文本包含中文字符，直接返回原样
    if any("\u4e00" <= c <= "\u9fff" for c in text):
        return text
    
    # 简单的常用映射或占位升级（实际生产中可调用 DeepL 或 OpenAI API）
    # 这里为了演示和零依赖，做一些基础的创作者常用词汇替换，或者返回友好的中文直译提示
    return f"【翻译】{text}"

def fetch_github_trending():
    """抓取 GitHub Trending 热门项目 (前 10 个)"""
    url = "https://github.com/trending"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            repo_rows = soup.select('article.Box-row')[:10] # 取前 10 个
            for row in repo_rows:
                a_tag = row.select_one('h2 a')
                if a_tag:
                    repo_name = a_tag.get_text(strip=True).replace("\n", "").replace(" ", "")
                    repo_url = "https://github.com" + a_tag['href']
                else:
                    repo_name = "Unknown Repo"
                    repo_url = "https://github.com"
                
                desc_elem = row.select_one('p')
                repo_desc = desc_elem.get_text(strip=True) if desc_elem else "No description provided."
                
                items.append({
                    "title": repo_name,
                    "desc": repo_desc,
                    "url": repo_url
                })
    except Exception as e:
        print(f"Warning: Error fetching GitHub Trending: {e}")
        
    if not items:
        items = [{
            "title": "github / trending-fallback",
            "desc": "Temporary fallback item due to network/rate limits.",
            "url": "https://github.com/trending"
        }] * 10
    return items

def fetch_product_hunt_rss():
    """通过 Product Hunt RSS 获取创意榜 (前 10 个)"""
    url = "https://www.producthunt.com/feed"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            entries = soup.find_all('item')[:10] # 取前 10 个
            for entry in entries:
                title = entry.title.text if entry.title else "New Product"
                link = entry.link.text if entry.link else "https://www.producthunt.com"
                desc = entry.description.text if entry.description else "No tagline provided."
                clean_desc = BeautifulSoup(desc, "html.parser").get_text(strip=True)
                
                items.append({
                    "title": title,
                    "desc": clean_desc,
                    "url": link
                })
    except Exception as e:
        print(f"Warning: Error fetching Product Hunt RSS: {e}")
        
    if not items:
        items = [{
            "title": "Product Hunt Daily Top",
            "desc": "Visit Product Hunt directly to explore today's launches.",
            "url": "https://www.producthunt.com/"
        }] * 10
    return items

def fetch_indie_hackers():
    """获取 Indie Hackers 热门讨论/访谈 (前 10 个)"""
    # 模拟或通过其公开 RSS/页面抓取
    url = "https://www.indiehackers.com/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 抓取首页讨论标题和链接
            links = soup.select('a.feed-item__title-link, a.discussion-title, h3 a')[:10]
            if not links:
                # 备用选择器
                links = soup.select('a[href*="/post/"], a[href*="/interview/"]')[:10]
                
            for a in links:
                title = a.get_text(strip=True)
                href = a.get('href', '')
                if href and not href.startswith('http'):
                    href = "https://www.indiehackers.com" + href
                if title and len(title) > 5:
                    items.append({
                        "title": title,
                        "desc": "Independent creator discussion & revenue insights.",
                        "url": href or "https://www.indiehackers.com/"
                    })
    except Exception as e:
        print(f"Warning: Error fetching Indie Hackers: {e}")

    # 如果抓取为空或受限，提供结构化兜底
    if len(items) < 10:
        fallback_count = 10 - len(items)
        for i in range(fallback_count):
            items.append({
                "title": f"Indie Hackers Community Insight #{i+1}",
                "desc": "Real-world bootstrapping stories, revenue numbers, and marketing strategies.",
                "url": "https://www.indiehackers.com/"
            })
            
    return items[:10]

def build_feishu_card():
    gh_items = fetch_github_trending()
    ph_items = fetch_product_hunt_rss()
    ih_items = fetch_indie_hackers()
    
    content_lines = ["🌍 **全球创作者日报 | Global Creator Daily**\n"]
    
    # 1. GitHub 模块（块状分隔）
    content_lines.append("---")
    content_lines.append("**🔥 GitHub 开源风向标 (Top 10)**")
    for idx, item in enumerate(gh_items, 1):
        zh_desc = simple_translate(item['desc'])
        content_lines.append(
            f"{idx}. **[{item['title']}]({item['url']})**\n"
            f"   - 🇬🇧 EN: {item['desc']}\n"
            f"   - 🇨🇳 CN: {zh_desc}\n"
        )
        
    # 2. Product Hunt 模块（块状分隔）
    content_lines.append("\n---")
    content_lines.append("**🚀 Product Hunt 创意产品 (Top 10)**")
    for idx, item in enumerate(ph_items, 1):
        zh_desc = simple_translate(item['desc'])
        content_lines.append(
            f"{idx}. **[{item['title']}]({item['url']})**\n"
            f"   - 🇬🇧 EN: {item['desc']}\n"
            f"   - 🇨🇳 CN: {zh_desc}\n"
        )

    # 3. Indie Hackers 模块（块状分隔）
    content_lines.append("\n---")
    content_lines.append("**💡 Indie Hackers 独立开发与变现 (Top 10)**")
    for idx, item in enumerate(ih_items, 1):
        zh_desc = simple_translate(item['desc'])
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
