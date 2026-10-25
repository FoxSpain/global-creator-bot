import os
import json
import requests
from bs4 import BeautifulSoup

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def translate_with_gemini_or_fallback(text):
    """优先使用 Gemini 进行地道中文翻译，异常时自动降级到 MyMemory"""
    if not text or len(text.strip()) == 0:
        return text
    
    # 如果本身包含较多中文，直接返回
    if sum(1 for c in text if "\u4e00" <= c <= "\u9fff") > len(text) * 0.3:
        return text

    # 1. 尝试使用 Gemini API 翻译
    if GEMINI_API_KEY:
        key = GEMINI_API_KEY.strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        headers = {"Content-Type": "application/json"}
        prompt = f"请将以下科技/开源项目的英文简介地道、精准地翻译为中文（只输出中文翻译结果，不要包含任何多余解释）：\n{text}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=8)
            if res.status_code == 200:
                res_json = res.json()
                translated = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
                if translated:
                    return translated
        except Exception as e:
            print(f"[Gemini Translate Warning]: {e}")

    # 2. 备用免费 API 翻译防线
    try:
        url = f"https://api.mymemory.translated.net/get?q={requests.utils.quote(text[:300])}&langpair=en|zh-CN"
        res = requests.get(url, timeout=5).json()
        translated = res.get("responseData", {}).get("translatedText", "")
        if translated and "MYMEMORY WARNING" not in translated.upper():
            return translated
    except Exception as e:
        print(f"[Fallback Translate Warning]: {e}")

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
            for row in soup.select('article.Box-row')[:10]:
                a_tag = row.select_one('h2 a')
                if not a_tag:
                    continue
                repo_name = a_tag.get_text(strip=True).replace("\n", "").replace(" ", "")
                repo_url = "https://github.com" + a_tag['href']
                desc_elem = row.select_one('p')
                repo_desc = desc_elem.get_text(strip=True) if desc_elem else "No description provided."
                items.append({"title": repo_name, "desc": repo_desc, "url": repo_url})
    except Exception as e:
        print(f"[GitHub Warning] {e}")
    return items[:10]

def fetch_product_hunt():
    """抓取 Product Hunt 每日产品 (Top 10)"""
    items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    url = "https://r.jina.ai/https://www.producthunt.com/"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            lines = response.text.split('\n')
            for line in lines:
                if "[" in line and "](" in line and "http" in line and "Image" not in line and "Promoted" not in line:
                    try:
                        start = line.index('[') + 1
                        end = line.index(']')
                        raw_title = line[start:end].strip()
                        if "." in raw_title[:3]:
                            raw_title = raw_title.split(".", 1)[-1].strip()
                            
                        if len(raw_title) > 2 and raw_title not in [i['title'] for i in items]:
                            items.append({
                                "title": raw_title,
                                "desc": f"Today's featured product launch on Product Hunt: {raw_title}.",
                                "url": "https://www.producthunt.com/"
                            })
                    except Exception:
                        continue
                if len(items) >= 10:
                    break
    except Exception as e:
        print(f"[PH Source Error]: {e}")

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
                    items.append({"title": title, "desc": title, "url": full_url})
                if len(items) >= 10:
                    break
    except Exception as e:
        print(f"[Indie Hackers Warning] {e}")
    return items[:10]

def render_section(title_header, items):
    lines = [f"\n---", f"**{title_header}**"]
    for idx, item in enumerate(items, 1):
        cn_desc = translate_with_gemini_or_fallback(item['desc'])
        lines.append(
            f"{idx}. **[{item['title']}]({item['url']})**\n"
            f"   - 🇬🇧 EN: {item['desc']}\n"
            f"   - 🇨🇳 CN: {cn_desc}"
        )
    return lines

def build_feishu_card():
    gh_items = fetch_github_trending()
    ph_items = fetch_product_hunt()
    ih_items = fetch_indie_hackers()
    
    content_lines = ["🌍 **全球创作者日报 | Global Creator Daily**\n"]
    
    if gh_items:
        content_lines.extend(render_section("🔥 GitHub 开源风向标 (Top 10)", gh_items))
    if ph_items:
        content_lines.extend(render_section("🚀 Product Hunt 创意产品 (Top 10)", ph_items))
    if ih_items:
        content_lines.extend(render_section("💡 Indie Hackers 独立开发与变现 (Top 10)", ih_items))
        
    card_content = "\n".join(content_lines)
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "💡 每日全球开源与商业创意灵感"},
                "template": "blue"
            },
            "elements": [{"tag": "markdown", "content": card_content}]
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
        response = requests.post(FEISHU_WEBHOOK_URL, data=json.dumps(payload), headers=headers, timeout=20)
        print("Feishu Response:", response.json())
    except Exception as e:
        print(f"[Error] Failed to send message to Feishu: {e}")

if __name__ == "__main__":
    send_to_feishu()
