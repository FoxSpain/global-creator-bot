import os
import json
import requests
from bs4 import BeautifulSoup

FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 初始化 Gemini SDK (使用官方 SDK google-genai)
client = None
if GEMINI_API_KEY:
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"[Gemini Init Warning] {e}")

def analyze_item_with_gemini(title, desc):
    """
    使用 Gemini 一次性返回真正的中文翻译 + 三维深度拆解灵感
    """
    default_res = {
        "cn_desc": desc,
        "problem": "痛点提炼分析中",
        "tech": "核心技术/模式亮点",
        "action": "适合移植或创新的场景"
    }

    if not client:
        return default_res

    prompt = f"""
你是一位敏锐的科技产品经理和独立开发者导师。请分析以下项目/产品：
【项目名称】：{title}
【英文简介】：{desc}

请输出 JSON 格式（不要包含任何 markdown 代码块标记，只输出纯 JSON）：
{{
  "cn_desc": "地道的中文翻译（1句话）",
  "problem": "它解决了什么具体痛点或需求？（20字以内）",
  "tech": "核心亮点/技术或创新模式是什么？（20字以内）",
  "action": "独立创作者/开发者能借用它做点什么？（提示移植到细分领域、小众工具或副业方向，25字以内）"
}}
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        text = response.text.strip()
        # 清理可能存在的 markdown codeblock 标记
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        data = json.loads(text.strip())
        return data
    except Exception as e:
        print(f"[Gemini API Warning] {title}: {e}")
        return default_res

def fetch_github_trending():
    """抓取 GitHub Trending (Top 10)"""
    url = "[https://github.com/trending](https://github.com/trending)"
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
                repo_url = "[https://github.com](https://github.com)" + a_tag['href']
                
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
    sources = [
        "[https://rsshub.app/producthunt/today](https://rsshub.app/producthunt/today)",
        "[https://rsshub.rssfeed.today/producthunt/today](https://rsshub.rssfeed.today/producthunt/today)",
        "[https://www.producthunt.com/feed](https://www.producthunt.com/feed)"
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
                    link = "[https://www.producthunt.com](https://www.producthunt.com)"
                    if link_elem:
                        link = link_elem.get('href') or link_elem.text.strip()
                        
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
            if len(items) >= 5:
                break
        except Exception as e:
            print(f"[Product Hunt Source Warning] {url}: {e}")

    if not items:
        items = [{
            "title": f"Product Hunt Hot Product #{i+1}",
            "desc": "Check daily launches directly on Product Hunt website.",
            "url": "[https://www.producthunt.com/](https://www.producthunt.com/)"
        } for i in range(10)]

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

def render_section(title_header, items):
    lines = [f"\n---", f"**{title_header}**"]
    for idx, item in enumerate(items, 1):
        # 调取 Gemini 获取高级中英翻译 + 3 维拆解
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
        response = requests.post(FEISHU_WEBHOOK_URL, data=json.dumps(payload), headers=headers, timeout=15)
        print("Feishu Response:", response.json())
    except Exception as e:
        print(f"[Error] Failed to send message to Feishu: {e}")

if __name__ == "__main__":
    send_to_feishu()
