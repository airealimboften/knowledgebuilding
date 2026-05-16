# -*- coding: utf-8 -*-
"""HTML 生成器 - 负责生成寓言页面和更新目录首页"""

import os
import json
from datetime import datetime
import config


# ============================================================
# 领域颜色 CSS
# ============================================================
def _field_color_css(field):
    """获取领域对应的颜色"""
    color = config.FIELD_COLORS.get(field, "#667eea")
    return color


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
    """
    生成单篇寓言的完整 HTML 文件。

    参数:
        story_number: 故事编号 (int)
        concept_name: 概念名称
        field: 所属领域
        fable_content: LLM 生成的寓言 HTML 片段
        reply_title: 上一篇的标题（用于回复）
        reply_comment: 用户的留言内容
        reply_text: AI 的回复内容
        related_links: 关联篇目列表 [{"number": 5, "name": "xxx", "file": "005_xxx.html"}, ...]
        date_str: 日期字符串
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    num_str = f"{story_number:03d}"
    field_color = _field_color_css(field)

    # 构建回复区块
    reply_section = ""
    if reply_title and reply_comment and reply_text:
        reply_section = f"""
    <section class="reply-to-previous fade-in-up">
        <h3>📮 回复上篇讨论</h3>
        <blockquote>您在《{reply_title}》中问道：{reply_comment}</blockquote>
        <div class="reply-content">{reply_text}</div>
    </section>"""

    # 构建关联篇目
    related_section = ""
    if related_links:
        items = "\n".join(
            f'            <li><a href="{r["file"]}">第{r["number"]:03d}篇：{r["name"]}</a></li>'
            for r in related_links
        )
        related_section = f"""
    <section class="related-concepts fade-in-up">
        <h3>🔗 关联篇目</h3>
        <ul>
{items}
        </ul>
    </section>"""

    # 导航链接
    prev_link = ""
    if story_number > 1:
        prev_link = f'<a href="javascript:history.back()">← 上一篇</a>'
    else:
        prev_link = '<span></span>'

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
    </style>
</head>
<body>
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
    <section class="discussion fade-in-up" id="discussion-{num_str}">
        <h3>💬 讨论区</h3>
        <div class="user-comment" id="comment-{num_str}">
            <!-- 在此处输入您的留言 -->
        </div>
        <p class="hint">提示：直接编辑此 HTML 文件，在上方 div 标签内输入您的想法，保存即可。下一篇寓言生成时会读取并回复。</p>
    </section>

    <footer class="page-footer">
        <p>每日寓言 · 概念之旅 | 以寓言之光，照亮知识的幽径</p>
    </footer>
</div>
</body>
</html>"""

    return html


def save_story(story_number, concept_name, html_content):
    """保存故事 HTML 到 stories 目录"""
    os.makedirs(config.STORIES_DIR, exist_ok=True)
    # 文件名中去除特殊字符
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
    """
    重新生成 index.html 目录首页。
    """
    used = concepts_data.get("used_concepts", [])
    total = state_data.get("total_generated", 0)

    # 统计领域分布
    field_count = {}
    for field, concepts in concepts_data["fields"].items():
        count = len([c for c in concepts if c in used])
        if count > 0:
            field_count[field] = count

    fields_covered = len(field_count)

    # 构建目录条目
    toc_entries = _build_toc_entries()

    # 构建检查点
    checkpoints_html = _build_checkpoints(state_data)

    # 统计区
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
</head>
<body>
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
    </main>

    <footer class="page-footer">
        <p>每日自动生成 · 概念池覆盖 {len(concepts_data['fields'])} 个学科领域</p>
    </footer>
</div>
</body>
</html>"""

    with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(html)


def _build_toc_entries():
    """扫描 stories 目录，构建目录条目 HTML"""
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

            # 读取文件以获取领域和日期
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
    """从故事 HTML 中提取领域和日期"""
    field = "未知"
    date = ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read(2000)  # 只读取头部

        # 提取领域
        import re
        field_match = re.search(r'class="field-tag[^"]*">([^<]+)</span>', content)
        if field_match:
            field = field_match.group(1).strip()

        # 提取日期
        date_match = re.search(r'datetime="(\d{4}-\d{2}-\d{2})"', content)
        if date_match:
            date = date_match.group(1)
    except Exception:
        pass

    return field, date


def _build_checkpoints(state_data):
    """构建检查点 HTML"""
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
