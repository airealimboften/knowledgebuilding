# -*- coding: utf-8 -*-
"""HTML 生成器 - 负责生成寓言页面和更新目录首页（含密码门 + Giscus 评论）"""

import os
import json
import re
from datetime import datetime
import config


# ============================================================
# 密码门 JS（内嵌到每个页面）
# ============================================================
def _password_gate_overlay():
    """HTML overlay div (placed at top of body)"""
    return """
<div id="auth-overlay">
    <div class="auth-box">
        <div class="auth-icon">&#128274;</div>
        <h2>&#27599;&#26085;&#23493;&#35328; &middot; &#27010;&#24565;&#20043;&#26097;</h2>
        <p class="auth-subtitle">&#35831;&#36755;&#20837;&#35775;&#38382;&#23494;&#30721;</p>
        <input type="password" id="auth-input" placeholder="&#23494;&#30721;" />
        <button id="auth-btn">&#36827;&#20837;</button>
        <p id="auth-error">&#23494;&#30721;&#38169;&#35823;&#65292;&#35831;&#37325;&#35797;</p>
    </div>
</div>"""


def _password_gate_js():
    """Password gate JS — placed at END of body so all DOM elements exist"""
    return f"""
<script>
document.addEventListener('DOMContentLoaded', function() {{
    const H = '{config.ACCESS_PASSWORD_HASH}';
    const K = 'fable_auth';
    const overlay = document.getElementById('auth-overlay');
    const content = document.getElementById('page-content');

    function simpleHash(str) {{
        let hash = 0;
        for (let i = 0; i < str.length; i++) {{
            hash = ((hash << 5) - hash) + str.charCodeAt(i);
            hash |= 0;
        }}
        return hash.toString();
    }}

    function unlock() {{
        overlay.style.display = 'none';
        content.style.display = '';
    }}

    function reject() {{
        document.getElementById('auth-error').style.display = 'block';
        document.getElementById('auth-input').value = '';
        document.getElementById('auth-input').focus();
    }}

    // Already authenticated?
    if (localStorage.getItem(K) === H) {{
        unlock();
        return;
    }}

    // Hide content until password is entered
    content.style.display = 'none';

    function check() {{
        const v = document.getElementById('auth-input').value.trim();
        if (simpleHash(v) === H) {{
            localStorage.setItem(K, H);
            unlock();
        }} else {{
            reject();
        }}
    }}

    document.getElementById('auth-btn').addEventListener('click', check);
    document.getElementById('auth-input').addEventListener('keypress', function(e) {{
        if (e.key === 'Enter') check();
    }});
}});
</script>"""


def _password_gate_css():
    """密码门的 CSS 样式"""
    return """
#auth-overlay {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: var(--bg-primary, #0a0a12);
    display: flex; align-items: center; justify-content: center;
    z-index: 9999;
}
.auth-box {
    text-align: center; padding: 48px 40px;
    background: var(--bg-card, rgba(255,255,255,0.03));
    border: 1px solid var(--border-glass, rgba(255,255,255,0.08));
    border-radius: 24px; backdrop-filter: blur(20px);
    max-width: 380px; width: 90%;
}
.auth-icon { font-size: 3rem; margin-bottom: 16px; }
.auth-box h2 {
    font-family: var(--font-serif); font-size: 1.4rem;
    background: var(--accent-gradient, linear-gradient(135deg,#667eea,#764ba2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 8px;
}
.auth-subtitle { color: var(--text-muted, #5a5a6a); font-size: 0.9rem; margin-bottom: 24px; }
#auth-input {
    width: 100%; padding: 12px 16px; border: 1px solid var(--border-glass, rgba(255,255,255,0.08));
    border-radius: 12px; background: rgba(255,255,255,0.05);
    color: var(--text-primary, #e8e6e3); font-size: 1rem;
    outline: none; margin-bottom: 16px; text-align: center;
}
#auth-input:focus { border-color: var(--accent-color, #667eea); }
#auth-btn {
    width: 100%; padding: 12px; border: none; border-radius: 12px;
    background: var(--accent-gradient, linear-gradient(135deg,#667eea,#764ba2));
    color: white; font-size: 1rem; font-weight: 600; cursor: pointer;
    transition: opacity 0.3s;
}
#auth-btn:hover { opacity: 0.85; }
#auth-error { color: #ff7675; font-size: 0.85rem; margin-top: 12px; display: none; }
"""


# ============================================================
# Giscus 评论组件
# ============================================================
def _giscus_widget(story_term):
    """生成 Giscus 评论组件的 HTML"""
    if not config.GISCUS_CATEGORY_ID:
        # 如果 category_id 未配置，使用占位提示
        return f"""
    <section class="discussion fade-in-up">
        <h3>💬 讨论区</h3>
        <p class="hint">Giscus 评论系统待配置。请在 config.py 中填入 GISCUS_CATEGORY_ID。</p>
    </section>"""

    return f"""
    <section class="discussion fade-in-up">
        <h3>💬 讨论区</h3>
        <script src="https://giscus.app/client.js"
            data-repo="{config.GITHUB_OWNER}/{config.GITHUB_REPO}"
            data-repo-id="{config.GITHUB_REPO_ID}"
            data-category="{config.GISCUS_CATEGORY}"
            data-category-id="{config.GISCUS_CATEGORY_ID}"
            data-mapping="specific"
            data-term="{story_term}"
            data-strict="0"
            data-reactions-enabled="1"
            data-emit-metadata="0"
            data-input-position="top"
            data-theme="noborder_dark"
            data-lang="zh-CN"
            crossorigin="anonymous"
            async>
        </script>
    </section>"""


# ============================================================
# 领域颜色
# ============================================================
def _field_color_css(field):
    return config.FIELD_COLORS.get(field, "#667eea")


# ============================================================
# 单篇寓言 HTML 生成
# ============================================================
def generate_story_html(
    story_number,
    concept_name,
    field,
    fable_content,
    reply_title=None,
    reply_comment=None,
    reply_text=None,
    related_links=None,
    date_str=None,
):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    num_str = f"{story_number:03d}"
    field_color = _field_color_css(field)
    story_term = f"{num_str} {concept_name}"

    # 回复区块
    reply_section = ""
    if reply_title and reply_comment and reply_text:
        reply_section = f"""
        <section class="reply-to-previous fade-in-up">
            <h3>📮 回复上篇讨论</h3>
            <blockquote>您在《{reply_title}》中问道：{reply_comment}</blockquote>
            <div class="reply-content">{reply_text}</div>
        </section>"""

    # 关联篇目
    related_section = ""
    if related_links:
        items = "\n".join(
            f'                <li><a href="{r["file"]}">第{r["number"]:03d}篇：{r["name"]}</a></li>'
            for r in related_links
        )
        related_section = f"""
        <section class="related-concepts fade-in-up">
            <h3>🔗 关联篇目</h3>
            <ul>
{items}
            </ul>
        </section>"""

    # 导航
    prev_link = '<a href="javascript:history.back()">← 上一篇</a>' if story_number > 1 else '<span></span>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>第{num_str}篇 · {concept_name} — 每日寓言</title>
    <meta name="description" content="以寓言方式解说「{concept_name}」({field}) 的核心概念">
    <link rel="stylesheet" href="../styles.css">
    <style>
        .fable-header .field-tag {{
            background: {field_color}20;
            color: {field_color};
            border-color: {field_color}40;
        }}
        .fable-header .story-number {{
            background: {field_color}15;
            color: {field_color};
        }}
{_password_gate_css()}
    </style>
</head>
<body>
{_password_gate_overlay()}
<div id="page-content">
<div class="fable-page">
    <nav class="fable-nav">
        {prev_link}
        <a href="../index.html">📖 返回目录</a>
    </nav>

    <header class="fable-header fade-in-up">
        <span class="story-number">第 {num_str} 篇</span>
        <h1>{concept_name}</h1>
        <div class="meta">
            <span class="field-tag">{field}</span>
            <time datetime="{date_str}">{date_str}</time>
        </div>
    </header>
{reply_section}
    <section class="fable-body fade-in-up">
{fable_content}
    </section>
{related_section}
{_giscus_widget(story_term)}

    <footer class="page-footer">
        <p>每日寓言 · 概念之旅 | 以寓言之光，照亮知识的幽径</p>
    </footer>
</div>
</div>
{_password_gate_js()}
</body>
</html>"""

    return html


def save_story(story_number, concept_name, html_content):
    """保存故事 HTML 到 stories 目录"""
    os.makedirs(config.STORIES_DIR, exist_ok=True)
    safe_name = concept_name.replace("/", "-").replace("\\", "-").replace(" ", "_")
    filename = f"{story_number:03d}_{safe_name}.html"
    filepath = os.path.join(config.STORIES_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return filename


# ============================================================
# 目录首页 HTML 生成/更新
# ============================================================
def update_index_html(state_data, concepts_data):
    used = concepts_data.get("used_concepts", [])
    total = state_data.get("total_generated", 0)

    field_count = {}
    for field, concepts in concepts_data["fields"].items():
        count = len([c for c in concepts if c in used])
        if count > 0:
            field_count[field] = count

    fields_covered = len(field_count)
    toc_entries = _build_toc_entries()
    checkpoints_html = _build_checkpoints(state_data)

    stats_html = f"""
            <div class="stats">
                <div class="stat-item">
                    <span class="stat-number">{total}</span>
                    <span class="stat-label">已生成篇数</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{fields_covered}</span>
                    <span class="stat-label">覆盖领域</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{sum(len(v) for v in concepts_data['fields'].values()) - len(used)}</span>
                    <span class="stat-label">待探索概念</span>
                </div>
            </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>每日寓言 · 概念之旅</title>
    <meta name="description" content="以寓言之光照亮知识的幽径——每日一篇，用故事解说科学、经济、人文等领域的核心概念">
    <link rel="stylesheet" href="styles.css">
    <style>
{_password_gate_css()}
    </style>
</head>
<body>
{_password_gate_overlay()}
<div id="page-content">
<div class="container">
    <header class="hero">
        <h1>每日寓言 · 概念之旅</h1>
        <p class="subtitle">以寓言之光，照亮知识的幽径</p>
{stats_html}
    </header>

    <main class="toc-section">
        <h2>📚 篇目索引</h2>
{checkpoints_html}
        <div class="toc-grid">
{toc_entries}
        </div>

        <div class="one-more-section">
            <a class="one-more-btn" href="https://github.com/{config.GITHUB_OWNER}/{config.GITHUB_REPO}/issues/new?title=ONE_MORE&body=%E5%86%8D%E6%9D%A5%E4%B8%80%E7%AF%87%EF%BC%81" target="_blank" rel="noopener">
                &#10024; 再来一篇
            </a>
            <p class="one-more-hint">&#x1F4A1; 每天最多追加 {config.MAX_EXTRA_PER_DAY} 篇 &middot; 点击后在 GitHub 提交请求，下一轮运行时自动生成</p>
        </div>
    </main>

    <footer class="page-footer">
        <p>每日自动生成 {config.DAILY_COUNT} 篇 · 概念池覆盖 {len(concepts_data['fields'])} 个学科领域</p>
    </footer>
</div>
</div>
{_password_gate_js()}
</body>
</html>"""

    with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(html)


def _build_toc_entries():
    if not os.path.exists(config.STORIES_DIR):
        return "            <p style='color: var(--text-muted); grid-column: 1/-1; text-align: center;'>尚未生成任何寓言，敬请期待第一篇...</p>"

    entries = []
    files = sorted(os.listdir(config.STORIES_DIR))

    for filename in files:
        if not filename.endswith(".html"):
            continue
        try:
            parts = filename.replace(".html", "").split("_", 1)
            num = int(parts[0])
            name = parts[1] if len(parts) > 1 else "未知"

            filepath = os.path.join(config.STORIES_DIR, filename)
            field, date = _extract_meta_from_story(filepath)

            field_color = _field_color_css(field)
            entry = f"""            <a class="toc-item" href="stories/{filename}">
                <span class="item-number">{num:03d}</span>
                <div class="item-info">
                    <div class="item-name">{name}</div>
                    <div class="item-meta">
                        <span class="field-tag" style="background: {field_color}15; color: {field_color}; border-color: {field_color}30;">{field}</span>
                        <span>{date}</span>
                    </div>
                </div>
            </a>"""
            entries.append(entry)
        except (ValueError, IndexError):
            continue

    if not entries:
        return "            <p style='color: var(--text-muted); grid-column: 1/-1; text-align: center;'>尚未生成任何寓言，敬请期待第一篇...</p>"

    return "\n".join(entries)


def _extract_meta_from_story(filepath):
    field = "未知"
    date = ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        field_match = re.search(r'class="field-tag[^"]*">([^<]+)</span>', content)
        if field_match:
            field = field_match.group(1).strip()

        date_match = re.search(r'datetime="(\d{4}-\d{2}-\d{2})"', content)
        if date_match:
            date = date_match.group(1)
    except Exception:
        pass
    return field, date


def _build_checkpoints(state_data):
    checkpoints = state_data.get("checkpoints", [])
    if not checkpoints:
        return ""

    html_parts = []
    for cp in checkpoints:
        at = cp["at"]
        confirmed = cp.get("confirmed", False)
        if confirmed:
            status = f'<p style="color: var(--success);">✅ 已确认继续（{cp.get("confirmed_date", "")}）</p>'
        else:
            status = f"""<p>是否继续生成接下来的 {config.CHECKPOINT_INTERVAL} 篇？</p>
            <div class="confirm-instruction">
                请将 state.json 中的 "is_paused" 改为 false 以继续生成
            </div>"""

        html_parts.append(f"""
        <div class="checkpoint" id="checkpoint-{at}">
            <h2>🎯 已完成第 1 — {at} 篇</h2>
            {status}
        </div>""")

    return "\n".join(html_parts)
