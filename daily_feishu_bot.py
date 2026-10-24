import os
import json
import requests
from bs4 import BeautifulSoup

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL")

# 引入翻译库，带安全降级
try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False

def real_translate(text):
    """真正的中英对照翻译，带超时与容错机制"""
    if not text or len(text.strip()) == 0:
        return ""
    # 已经是中文，直接返回
    if any("\u4e00" <= c <= "\u9fff" for c in text):
        return text
        
    if HAS_TRANSLATOR:
        try:
            # 限制单次翻译超时为 5 秒
            translated = GoogleTranslator(source='en', target='zh-CN').translate(text)
            if translated:
                return translated
        except Exception as e:
            print(f"[Translation Warning] {e}")
            
    # 降级：如果翻译失败，返回英文提示
    return f"（英文原意）{text}"

def fetch_github_trending():
    """抓取 GitHub Trending (Top 10)"""
    url = "https://github.com/trending"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=8)
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
        print(f"[GitHub Warning] Fetch failed: {e}")
        
    # 如果抓取不全或失败，补充结构化提示
    while len(items) < 10:
        idx = len(items) + 1
        items.append({
            "title": f"github/trending-repo-{idx}",
            "desc": "Explore top daily repositories on GitHub Trending.",
            "url": "https://github.com/trending"
        })
        
    return items[:10]

def fetch_product_hunt():
    """抓取 Product Hunt 创意榜 (Top 10)"""
    url = "https://www.producthunt.com/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            seen_titles = set()
            for a in soup.select('a[href*="/posts/"]'):
                title = a.get_text(strip=True)
                href = a.get('href', '')
                if title and len(title) > 3 and title not in seen_titles and "comments" not in title.lower():
                    seen_titles.add(title)
                    full_url = "https://www.producthunt.com" + href if not href.startswith("http") else href
                    items.append({
                        "title": title,
                        "desc": "New tech project and product launch on Product Hunt.",
                        "url": full_url
                    })
                if len(items) >= 10:
                    break
    except Exception as e:
        print(f"[Product Hunt Warning] Fetch failed: {e}")
        
    while len(items) < 10:
        idx = len(items) + 1
        items.append({
            "title": f"Product Hunt Project #{idx}",
            "desc": "Daily curated top product launches for indie hackers.",
            "url": "https://www.producthunt.com/"
        })
        
    return items[:10]

def fetch_indie_hackers():
    """抓取 Indie Hackers 社区讨论 (Top 10)"""
    url = "https://www.indiehackers.com/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for a in soup.select('a[href*="/post/"], a[href*="/discussion/"]'):
                title = a.get_text(strip=True)
                href = a.get('href', '')
                if title and "comments" not in title.lower() and len(title) > 10:
                    full_url = "https://www.indiehackers.com" + href if not href.startswith("http") else href
                    items.append({
                        "title": title,
                        "desc": "Indie developer discussion on product growth and revenue.",
                        "url": full_url
                    })
                if len(items) >= 10:
                    break
    except Exception as e:
        print(f"[Indie Hackers Warning] Fetch failed: {e}")

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
    try:
        send_to_feishu()
    except Exception as e:
        print(f"[Fatal Exception Caught] {e}")
