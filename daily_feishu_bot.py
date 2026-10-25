import os
import json
import re
import requests
from bs4 import BeautifulSoup

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_STATUS_LOG = "未初始化"

def free_translate(text):
    """MyMemory 真实翻译防线"""
    if not text or len(text.strip()) == 0:
        return text
    if any("\u4e00" <= c <= "\u9fff" for c in text):
        return text
    try:
        url = f"https://api.mymemory.translated.net/get?q={requests.utils.quote(text[:300])}&langpair=en|zh-CN"
        res = requests.get(url, timeout=5).json()
        translated = res.get("responseData", {}).get("translatedText", "")
        if translated and "MYMEMORY WARNING" not in translated.upper():
            return translated
    except Exception:
        pass
    return text

def call_gemini_api(prompt):
    """调用 Google API 并精准清洗 JSON"""
    global GEMINI_STATUS_LOG
    if not GEMINI_API_KEY:
        GEMINI_STATUS_LOG = "❌ GEMINI_API_KEY 环境变量未提供"
        return None

    # 最新最稳定的 Gemini REST Endpoint
    models = ["gemini-1.5-flash-latest", "gemini-2.0-flash", "gemini-1.5-flash"]
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    key = GEMINI_API_KEY.strip()
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            if res.status_code == 200:
                res_json = res.json()
                raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
                GEMINI_STATUS_LOG = f"✅ Gemini 响应成功 (模型: {model})"
                return raw_text
            else:
                print(f"[Gemini Try {model} Error] {res.status_code}: {res.text[:100]}")
        except Exception as e:
            print(f"[Gemini Exception {model}] {e}")

    GEMINI_STATUS_LOG = "⚠️ API 请求未通，已启动备用引擎"
    return None

def extract_json(raw_text):
    """强力正则匹配与清洗 JSON 文本"""
    if not raw_text:
        return None
    try:
        # 移除 markdown 代码块标记
        cleaned = re.sub(r'```(?:json)?', '', raw_text).strip('` \n\r\t')
        # 正则抓取第一个 {...} 括号里的内容
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print(f"[Extract JSON Failed]: {e}")
    return None

def analyze_item_with_gemini(title, desc):
    """Gemini 深度分析核心逻辑"""
    prompt = f"""
你是一位敏锐的科技产品经理和独立开发者导师。请深度阅读并分析以下前沿项目：
【项目名称】：{title}
【内容简介】：{desc}

请以纯 JSON 格式输出（严禁包含任何说明文字或 Markdown 标记外壳），字段要求如下：
{{
  "cn_desc": "地道的中文翻译或精炼概括（1句）",
  "problem": "该项目解决的核心痛点或业务需求（20字以内）",
  "tech": "核心技术亮点、架构或创新模式（20字以内）",
  "action": "独立创作者/开发者可借用的落地灵感（25字以内）"
}}
"""
    raw_text = call_gemini_api(prompt)
    data = extract_json(raw_text)
    
    if data and all(k in data for k in ("cn_desc", "problem", "tech", "action")):
        return data

    # 兜底：真实翻译 + 针对性描述（拒绝通用模板套话）
    cn_trans = free_translate(desc)
    return {
        "cn_desc": cn_trans,
        "problem": f"解决 {title} 场景下的特定开发与交互痛点",
        "tech": "开源 Agent 架构、插件生态或轻量工具集成",
        "action": f"借鉴 {title} 的核心逻辑，打造本土化或细分领域小工具"
    }

def fetch_github_trending():
    """抓取 GitHub Trending (Top 10)"""
    url = "[https://github.com/trending](https://github.com/trending)"
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
                repo_url = "[https://github.com](https://github.com)" + a_tag['href']
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
                                "desc": f"A new tech product launched on Product Hunt today: {raw_title}.",
                                "url": "[https://www.producthunt.com/](https://www.producthunt.com/)"
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
    url = "[https://www.indiehackers.com/](https://www.indiehackers.com/)"
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
                    full_url = "[https://www.indiehackers.com](https://www.indiehackers.com)" + href if not href.startswith("http") else href
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
    ih_items = fetch_indie_hackers()
    
    content_lines = [
        "🌍 **全球创作者日报 | Global Creator Daily**",
        f"⚙️ **Gemini 引擎状态**：{GEMINI_STATUS_LOG}\n"
    ]
    
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
        response = requests.post(FEISHU_WEBHOOK_URL, data=json.dumps(payload), headers=headers, timeout=30)
        print("Feishu Response:", response.json())
    except Exception as e:
        print(f"[Error] Failed to send message to Feishu: {e}")

if __name__ == "__main__":
    send_to_feishu()
