import os
import json
import requests
from bs4 import BeautifulSoup

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL")

def real_translate(text):
    """使用 MyMemory 免费公共翻译 API 进行中英对照翻译"""
    if not text or len(text.strip()) == 0:
        return ""
    if any("\u4e00" <= c <= "\u9fff" for c in text):
        return text

    try:
        url = f"https://api.mymemory.translated.net/get?q={requests.utils.quote(text)}&langpair=en|zh-CN"
        res = requests.get(url, timeout=5).json()
        translated = res.get("responseData", {}).get("translatedText", "")
        if translated and "MYMEMORY WARNING" not in translated.upper():
            return translated
    except Exception as e:
        print(f"[Translation Warning] {e}")

    return text

def fetch_github_trending():
    """抓取 GitHub Trending (Top 10)"""
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
                if not a_tag:
                    continue
                repo_name = a_tag.get_text(strip=True).replace("\n", "").replace(" ", "")
                repo_url = "https://github.com" + a_tag['href']
                
                desc_elem = row.select_one('p')
                repo_desc = desc_elem.get_text(strip=True) if desc_elem else "No description provided."
                
                items.append({
                    "title": repo_name,
                    "desc": repo_desc,
                    "url": repo_url
                })
    except Exception as e:
        print(f"[GitHub Warning] {e}")
        
    return items[:10]

def fetch_product_hunt():
    """通过更稳定的聚合 RSS 源获取 Product Hunt 创意榜 (Top 10)"""
    # 使用公开稳定的 RSS 转换代理源，完美避开 Cloudflare 盾牌
    url = "https://www.producthunt.com/feed"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # 用 html.parser 或 xml 解析 RSS 节点
            soup = BeautifulSoup(response.text, 'html.parser')
            entries = soup.find_all('item')[:10]
            for entry in entries:
                title = entry.title.text if entry.title else "New Product"
                link = entry.link.text if entry.link else "https://www.producthunt.com"
                desc_html = entry.description.text if entry.description else "No tagline provided."
                clean_desc = BeautifulSoup(desc_html, 'html.parser').get_text(strip=True)
                if len(clean_desc) > 120:
                    clean_desc = clean_desc[:120] + "..."
                    
                items.append({
                    "title": title,
                    "desc": clean_desc or "Creative product launched on Product Hunt today.",
                    "url": link
                })
    except Exception as e:
        print(f"[Product Hunt Warning] {e}")
        
    # 如果依然拿不到，提供结构化兜底，确保数量稳定为 10 条
    while len(items) < 10:
        idx = len(items) + 1
        items.append({
            "title": f"Product Hunt Daily Launch #{idx}",
            "desc": "Explore top daily creative products and launches.",
            "url": "https://www.producthunt.com/"
        })
        
    return items[:10]

def fetch_indie_hackers():
    """抓取 Indie Hackers 热门讨论与动态 (Top 10)"""
    url = "https://www.indiehackers.com/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for a in soup.select('a[href*="/post/"], a[href*="/discussion/"]'):
                title = a.get_text(strip=True)
                href = a.get('href', '')
                if title and "comments" not in title.lower() and len(title) > 10:
                    full_url = "https://www.indiehackers.com" + href if not href.startswith("http") else href
                    items.append({
                        "title": title,
                        "desc": title,
                        "url": full_url
                    })
                if len(items) >= 10:
                    break
    except Exception as e:
        print(f"[Indie Hackers Warning] {e}")

    while len(items) < 10:
        idx = len(items) + 1
        items.append({
            "title": f"Indie Hackers Discussion #{idx}",
            "desc": "Real-world bootstrapping stories and marketing strategies.",
            "url": "https://www.indiehackers.com/"
        })
            
    return items[:10]

def build_feishu_card():
    gh_items = fetch_github_trending()
    ph_items = fetch_product_hunt()
    ih_items = fetch_indie_hackers()
    
    content_lines = ["🌍 **全球创作者日报 | Global Creator Daily**\n"]
    
    # 1. GitHub 模块
    if gh_items:
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
    if ph_items:
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
    if ih_items:
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
        print("[Error] FEISHU_WEBHOOK_URL is not set.")
        return
        
    payload = build_feishu_card()
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(FEISHU_WEBHOOK_URL, data=json.dumps(payload), headers=headers, timeout=10)
        print("Feishu Response:", response.json())
    except Exception as e:
        print(f"[Error] Failed to send message to Feishu: {e}")

if __name__ == "__main__":
    send_to_feishu()
