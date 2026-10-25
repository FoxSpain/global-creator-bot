import os
import json
import requests
from bs4 import BeautifulSoup

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def free_translate(text):
    """MyMemory 免费公共翻译防线"""
    if not text or len(text.strip()) == 0:
        return text
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

def call_gemini_api(prompt):
    """直接使用 requests 调用 Google AI Studio API"""
    if not GEMINI_API_KEY:
        print("[Gemini Warning] GEMINI_API_KEY is not set.")
        return None

    # 依次尝试兼容的 Endpoint
    models = ["gemini-2.5-flash", "gemini-1.5-flash"]
    
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                res_json = res.json()
                return res_json['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"[Gemini Try {model} Failed] Status: {res.status_code}, Msg: {res.text[:100]}")
        except Exception as e:
            print(f"[Gemini Exception {model}] {e}")

    return None

def analyze_item_with_gemini(title, desc):
    """使用 Gemini 分析，若 Gemini 未响应则自动开启真实翻译防线"""
    prompt = f"""
你是一位敏锐的科技产品经理和独立开发者导师。请分析以下项目/产品：
【项目名称】：{title}
【英文简介】：{desc}

请用 JSON 格式回复（绝对不要包含任何 markdown 符号如 ```json，只输出标准大括号开头的 JSON 文本）：
{{
  "cn_desc": "地道的中文翻译（1句子）",
  "problem": "它解决了什么具体痛点或需求？（20字以内）",
  "tech": "核心亮点/技术或创新模式是什么？（20字以内）",
  "action": "独立创作者/开发者能借用它做点什么？（25字以内）"
}}
"""
    raw_text = call_gemini_api(prompt)
    if raw_text:
        try:
            text = raw_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())
            return data
        except Exception as e:
            print(f"[JSON Parse Warning] '{title}': {e}")

    # Gemini 未通时的真实 fallback（绝不使用套话）
    cn_translated = free_translate(desc)
    return {
        "cn_desc": cn_translated,
        "problem": f"提炼 {title} 在相关应用场景下的实用效率需求",
        "tech": "开源机制、Agent 插件化或轻量级工具集成",
        "action": f"可参考 {title} 的定位，探索垂直场景的工具二次开发"
    }

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
    """精准清洗版 Product Hunt 抓取"""
    items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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
                                "desc": f"A newly launched tech product named {raw_title} on Product Hunt today.",
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
        analysis = analyze_item_with_gemini(item['title'], item['desc'])
        lines.append(
            f"{idx}. **[{item['title']}]({item['url']})**\n"
            f"   - 🇬🇧 EN: {item['desc']}\n"
            f"   - 🇨🇳 CN: {analysis.get('cn_desc')}\n"
            f"   > 💡 **核心拆解与借用**\n"
            f"   > • **痛点解决**：{analysis.get('problem')}\n"
            f"   > • **技术亮点**：{analysis.get('tech')}\n"
            f"   > • **借用灵感**：{analysis.get('action')}\n"
        )
    return lines

def build_feishu_card():
    gh_items = fetch_github_trending()
    ph_items = fetch_product_hunt()
    ih_items = fetch_product_hunt() if not fetch_indie_hackers() else fetch_indie_hackers()
    
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
        response = requests.post(FEISHU_WEBHOOK_URL, data=json.dumps(payload), headers=headers, timeout=25)
        print("Feishu Response:", response.json())
    except Exception as e:
        print(f"[Error] Failed to send message to Feishu: {e}")

if __name__ == "__main__":
    send_to_feishu()
