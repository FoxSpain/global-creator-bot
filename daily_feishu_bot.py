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
    """多通道抓取 Product Hunt 每日产品 ( Top 10 )"""
    items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # 通道 1：使用 RSSHub 公开节点 (对 GitHub Actions 最友好的镜像源)
    sources = [
        "https://rsshub.app/producthunt/today",
        "https://rsshub.rssfeed.today/producthunt/today",
        "https://www.producthunt.com/feed"
    ]
    
    for url in sources:
        try:
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                entries = soup.find_all(['item', 'entry'])
                for entry in entries:
                    title_elem = entry.find('title')
                    link_elem = entry.find('link')
                    desc_elem = entry.find(['description', 'summary', 'content'])
                    
                    title = title_elem.text.strip() if title_elem else ""
                    
                    # 提取链接
                    link = "https://www.producthunt.com"
                    if link_elem:
                        link = link_elem.get('href') or link_elem.text.strip()
                        
                    # 提取 Tagline/描述
                    desc = "New creative product on Product Hunt."
                    if desc_elem:
                        clean_text = BeautifulSoup(desc_elem.text, 'html.parser').get_text(strip=True)
                        if clean_text:
                            desc = clean_text[:120] + "..." if len(clean_text) > 120 else clean_text
                            
                    if title and title not in [i['title'] for i in items]:
                        items.append({
                            "title": title,
                            "desc": desc,
                            "url": link
                        })
                    if len(items) >= 10:
                        break
            if len(items) >= 5: # 拿到了有效数据就退出轮询
                break
        except Exception as e:
            print(f"[Product Hunt Source Warning] {url}: {e}")

    # 如果抓取依旧受阻，进行保底处理
    if not items:
        print("[Product Hunt Error] All sources failed, using fallback.")
        items = [{
            "title": f"Product Hunt Hot Product #{i+1}",
            "desc": "Check daily launches directly on Product Hunt website.",
            "url": "https://www.producthunt.com/"
        } for i in range(10)]

    return items[:10]

def fetch_indie_hackers():
    """抓取 Indie Hackers 热门讨论 (Top 10)"""
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
