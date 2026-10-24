import os
import json
import requests
from bs4 import BeautifulSoup

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL")

def translate_to_zh(english_text):
    """简单中英对照翻译占位"""
    return f"[中文对照] {english_text}"

def fetch_github_trending():
    """抓取 GitHub Trending 热门项目"""
    url = "https://github.com/trending"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            repo_rows = soup.select('article.Box-row')[:5]
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
        
    # 兜底数据，确保即使抓取失败脚本也不会报错退出
    if not items:
        items = [{
            "title": "github / trending-fallback",
            "desc": "Temporary fallback item due to network/rate limits.",
            "url": "https://github.com/trending"
        }]
    return items

def fetch_product_hunt_rss():
    """通过 Product Hunt RSS 获取创意榜"""
    url = "https://www.producthunt.com/feed"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    items = []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser') # 使用通用 html.parser 解析 RSS
            entries = soup.find_all('item')[:5]
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
        }]
    return items

def build_feishu_card():
    gh_items = fetch_github_trending()
    ph_items = fetch_product_hunt_rss()
    
    content_lines = ["🌍 **全球创作者日报 | Global Creator Daily**\n"]
    
    content_lines.append("### 🔥 GitHub Trending (开源风向)")
    for idx, item in enumerate(gh_items, 1):
        zh_desc = translate_to_zh(item['desc'])
        content_lines.append(
            f"{idx}. **[{item['title']}]({item['url']})**\n"
            f"   - 🇬🇧 *EN:* {item['desc']}\n"
            f"   - 🇨🇳 *CN:* {zh_desc}\n"
        )
        
    content_lines.append("\n### 🚀 Product Hunt (创意产品)")
    for idx, item in enumerate(ph_items, 1):
        zh_desc = translate_to_zh(item['desc'])
        content_lines.append(
            f"{idx}. **[{item['title']}]({item['url']})**\n"
            f"   - 🇬🇧 *EN:* {item['desc']}\n"
            f"   - 🇨🇳 *CN:* {zh_desc}\n"
        )
        
    card_content = "\n".join(content_lines)
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "💡 每日全球开源与创意灵感"},
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
    try:
        send_to_feishu()
    except Exception as e:
        print(f"Fatal error in execution: {e}")
        # 如果你想让出错时也显示成功而不中断，可以注释掉下面这行；
        # 但保留可以让 Actions 正确报错。
        raise e
