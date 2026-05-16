# -*- coding: utf-8 -*-
"""
每日寓言生成系统 — 主控脚本
============================
每天凌晨 3:00 由 Windows Task Scheduler 触发。
主选 Gemini API，网络失败时回退至 DeepSeek API。
"""

import os
import sys
import json
import logging
import time
from datetime import datetime

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import concept_manager
import discussion_reader
import html_builder

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def call_llm(prompt):
    """
    调用 LLM，目前仅使用 DeepSeek API。
    """
    try:
        logger.info("尝试调用 DeepSeek API...")
        result = call_deepseek(prompt)
        logger.info("DeepSeek 调用成功")
        return result
    except Exception as e:
        logger.error(f"DeepSeek 调用失败: {e}")
        raise RuntimeError(f"API 调用失败")


# ============================================================
# 状态管理
# ============================================================
def load_state():
    with open(config.STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(config.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)


# ============================================================
# Prompt 构建
# ============================================================
def build_fable_prompt(concept_name, field, reply_context=None):
    """构建寓言生成 Prompt"""
    reply_part = ""
    if reply_context:
        title, comment = reply_context
        reply_part = f"""
---
在你开始写寓言之前，请先回复上一篇的读者讨论：
上一篇标题：《{title}》
读者留言：{comment}

请生成一段简洁、有深度的回复（3-5句话），用 <div class="ai-reply"><h4>📝 回复</h4><p>你的回复</p></div> 包裹。
这段回复将出现在本篇寓言正文之前。
---
"""

    prompt = f"""{reply_part}
请为以下概念创作一篇中文寓言故事。输出纯 HTML 片段（不需要 DOCTYPE、head、body 等外层标签）。

概念：{concept_name}
领域：{field}

创作要求：
1. 寓言只保留核心部分，用最精炼的叙事说明概念本质
2. 角色和场景要生动形象，但不冗余
3. 寓言正文用 <h2>寓言</h2> 开头，包裹在若干 <p> 标签中
4. 寓言结尾用 <p class="moral">寓意点睛</p> 点明概念要义（1-2句话）
5. 在寓言之后，用 <div class="concept-explanation"><h2>概念解析</h2><p>...</p></div> 提供简明的正式解释（2-3句）
6. 如果有助于理解，可以在正文中嵌入：
   - 表格：用标准 <table> 标签（用于对比、分类）
   - SVG 图解：用内联 <svg> 标签（用于流程、关系图，注意配色用浅色线条和文字，背景透明）
   - 重点标注：<mark> 和 <strong>
7. 总字数控制在 500-800 字
8. 不要使用 markdown 格式，直接输出 HTML
9. 不要包含 ```html 代码块标记

直接输出 HTML 片段，不要有任何其他前缀或后缀说明。
"""
    return prompt


def build_reply_prompt(title, comment):
    """构建讨论回复 Prompt（独立调用时使用）"""
    return f"""
读者在阅读《{title}》后留言：
{comment}

请用中文生成一段简洁、有深度的回复（3-5句话）。
回复应当与概念相关，引导读者深入思考。
直接输出回复文本，不要有任何前缀。
"""


# ============================================================
# 主流程
# ============================================================
def main():
    logger.info("=" * 60)
    logger.info("每日寓言生成系统启动")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # 确保目录存在
    os.makedirs(config.STORIES_DIR, exist_ok=True)
    os.makedirs(config.ASSETS_DIR, exist_ok=True)

    # 1. 加载状态
    state = load_state()
    logger.info(f"当前状态: 已生成 {state['total_generated']} 篇, 暂停={state['is_paused']}")

    # 2. 检查是否暂停
    if state["is_paused"]:
        logger.info("⏸ 系统已暂停（等待确认继续），跳过生成。")
        logger.info("请将 state.json 中的 is_paused 改为 false 以继续。")
        return

    # 3. 检查今天是否已生成（防止重复）
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_generated_date") == today:
        logger.info(f"今天 ({today}) 已生成过，跳过。")
        return

    # 4. 加载概念库
    concepts_data = concept_manager.load_concepts()

    # 5. 选择概念
    field, concept_name = concept_manager.select_random_concept(concepts_data)
    if concept_name is None:
        logger.warning("所有概念已用完！请扩充概念池。")
        return

    story_number = state["total_generated"] + 1
    logger.info(f"选定概念: [{field}] {concept_name} (第 {story_number} 篇)")

    # 6. 读取上一篇讨论
    reply_context = None
    reply_text = None
    prev_title, prev_comment = discussion_reader.read_previous_discussion(story_number)
    if prev_title and prev_comment:
        logger.info(f"发现上篇讨论: 《{prev_title}》 => {prev_comment[:50]}...")
        reply_context = (prev_title, prev_comment)
        # 生成回复
        try:
            reply_prompt = build_reply_prompt(prev_title, prev_comment)
            reply_text = call_llm(reply_prompt)
            logger.info("讨论回复已生成")
        except Exception as e:
            logger.error(f"生成讨论回复失败: {e}")
            reply_text = None
    else:
        logger.info("上篇无讨论留言")

    # 7. 生成寓言
    try:
        prompt = build_fable_prompt(concept_name, field, reply_context)
        fable_content = call_llm(prompt)

        # 清理可能的 markdown 代码块标记
        fable_content = fable_content.strip()
        if fable_content.startswith("```html"):
            fable_content = fable_content[7:]
        if fable_content.startswith("```"):
            fable_content = fable_content[3:]
        if fable_content.endswith("```"):
            fable_content = fable_content[:-3]
        fable_content = fable_content.strip()

        logger.info(f"寓言内容已生成 ({len(fable_content)} 字符)")
    except Exception as e:
        logger.error(f"寓言生成失败: {e}")
        return

    # 8. 查找关联篇目
    related = concept_manager.get_related_concepts(concepts_data, concept_name)
    related_links = []
    for r_name in related:
        r_num = concept_manager.find_story_number_for_concept(r_name)
        if r_num:
            safe = r_name.replace("/", "-").replace("\\", "-").replace(" ", "_")
            related_links.append({
                "number": r_num,
                "name": r_name,
                "file": f"{r_num:03d}_{safe}.html",
            })

    # 9. 生成 HTML 并保存
    story_html = html_builder.generate_story_html(
        story_number=story_number,
        concept_name=concept_name,
        field=field,
        fable_content=fable_content,
        reply_title=prev_title,
        reply_comment=prev_comment,
        reply_text=reply_text,
        related_links=related_links if related_links else None,
        date_str=today,
    )
    filename = html_builder.save_story(story_number, concept_name, story_html)
    logger.info(f"故事已保存: {filename}")

    # 10. 标记概念已使用
    concept_manager.mark_concept_used(concepts_data, concept_name, story_number)

    # 11. 更新状态
    state["current_number"] = story_number
    state["total_generated"] = story_number
    state["last_generated_date"] = today
    state["last_concept"] = concept_name

    # 12. 检查是否到达检查点
    if story_number % config.CHECKPOINT_INTERVAL == 0:
        logger.info(f"🎯 到达第 {story_number} 篇检查点！系统暂停。")
        state["is_paused"] = True
        state["checkpoints"].append({
            "at": story_number,
            "confirmed": False,
            "confirmed_date": None,
        })

    save_state(state)

    # 13. 更新目录首页
    html_builder.update_index_html(state, concepts_data)
    logger.info("目录首页已更新")

    # 14. 推送到 GitHub Pages
    git_push(story_number, concept_name)

    logger.info(f"[OK] 第 {story_number} 篇 [{concept_name}] 生成完毕！")
    logger.info("=" * 60)


# ============================================================
# Git 自动推送
# ============================================================
GIT_EXE = os.path.join(config.BASE_DIR, "git", "cmd", "git.exe")


def git_push(story_number, concept_name):
    """生成后自动 commit + push 到 GitHub"""
    import subprocess

    if not os.path.exists(GIT_EXE):
        logger.warning(f"Portable Git 未找到: {GIT_EXE}，跳过推送。")
        return

    try:
        def run_git(*args):
            result = subprocess.run(
                [GIT_EXE] + list(args),
                cwd=config.BASE_DIR,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0 and result.stderr:
                logger.warning(f"git {args[0]}: {result.stderr.strip()}")
            return result

        run_git("add", "-A")
        run_git("commit", "-m", f"story {story_number:03d}: {concept_name}")
        result = run_git("push", "origin", "main")

        if result.returncode == 0:
            logger.info("GitHub Pages 推送成功")
        else:
            logger.warning(f"推送可能失败: {result.stderr.strip()}")

    except Exception as e:
        logger.error(f"Git 推送异常: {e}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"致命错误: {e}", exc_info=True)
        sys.exit(1)

