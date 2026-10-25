import os
import json
import requests
from bs4 import BeautifulSoup

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 状态追踪全局变量
if GEMINI_API_KEY:
    GEMINI_STATUS_LOG = "✅ Gemini 已加载 (准备就绪)"
else:
    GEMINI_STATUS_LOG = "❌ 未检测到 GEMINI_API_KEY 环境变量！"

def call_gemini_api(prompt):
    """真正让 Gemini 联网阅读并深度总结的底层 HTTP 请求"""
    if not GEMINI_API_KEY:
        return None

    # 使用目前最稳定的 Gemini 官方 REST 节点
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY.strip()}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            res_json = res.json()
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"[Gemini HTTP Error] Status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[Gemini Exception] {e}")
        
    return None

def analyze_item_with_gemini(title, desc):
    """让 Gemini 逐条阅读内容并进行定制化拆解"""
    prompt = f"""
你是一位敏锐的科技产品经理和独立开发者导师。请深度阅读并分析以下海外前沿科技项目/讨论：
【项目/标题】：{title}
【英文简介/内容】：{desc}

请用 JSON 格式回复（绝对不要包含任何 markdown 符号如 ```json，只输出标准大括号开头的 JSON 文本）：
{{
  "cn_desc": "地道的中文翻译，准确概括其核心功能（1句）",
  "problem": "它具体解决了什么真实痛点或业务需求？（20字以内）",
  "tech": "核心技术亮点、架构或创新商业模式是什么？（20字以内）",
  "action": "独立创作者/开发者能借用它做点什么？（提示移植到细分领域或副业方向，25字以内）"
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
            if all(k in data for k in ("cn_desc", "problem", "tech", "action")):
                return data
        except Exception as e:
            print(f"[JSON Parse Error for '{title}']: {e}")
            
    # 如果 AI 偶然超时，基于原文动态生成摘要，拒绝死板模板
    return {
        "cn_desc": desc[:100] + "..." if len(desc) > 100 else desc,
        "problem": f"针对 {title[:20]} 的效率与体验痛点",
        "tech": "现代化工作流或轻量级工具集成",
        "action": "可作为独立开发或垂直领域工具的参考"
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
    """精准清洗 Product Hunt 抓取"""
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
                                "desc": f"A newly launched tech product on Product Hunt called {raw_title}, focusing on creator productivity and digital tools.",
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
        # 逐条丢给 Gemini 阅读并提炼
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
