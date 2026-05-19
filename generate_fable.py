# -*- coding: utf-8 -*-
"""
每日寓言生成系统 — 主控脚本
============================
15:00 生成每日 DAILY_COUNT 篇寓言。
20:00 检查 "再来一篇" 请求，最多再生成 MAX_EXTRA_PER_DAY 篇。

用法:
    python generate_fable.py            # 每日主生成
    python generate_fable.py --extra    # 处理"再来一篇"请求
"""

import os
import sys
import json
import logging
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime

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


# ============================================================
# DeepSeek API
# ============================================================
def call_deepseek(prompt):
    """调用 DeepSeek API（OpenAI 兼容接口）"""
    from openai import OpenAI
    client = OpenAI(
        api_key=config.DEEPSEEK_API_KEY,
        base_url=config.DEEPSEEK_BASE_URL,
    )
    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {
                "role": "system",
                "content": "你是一位博学的寓言大师，擅长用精炼的寓言故事解说复杂的专业概念。你的输出是 HTML 片段。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.85,
        max_tokens=2048,
    )
    return response.choices[0].message.content


def call_llm(prompt):
    try:
        logger.info("尝试调用 DeepSeek API...")
        result = call_deepseek(prompt)
        logger.info("DeepSeek 调用成功")
        return result
    except Exception as e:
        logger.error(f"DeepSeek 调用失败: {e}")
        raise RuntimeError("API 调用失败")


# ============================================================
# 状态管理
# ============================================================
def load_state():
    with open(config.STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(config.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)


def reset_daily_counters(state):
    """如果是新的一天，重置每日计数器"""
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_generated_date") != today:
        state["today_count"] = 0
        state["today_extra_count"] = 0
    return today


# ============================================================
# Prompt 构建
# ============================================================
def build_fable_prompt(concept_name, field, reply_context=None):
    reply_part = ""
    if reply_context:
        title, comment = reply_context
        reply_part = f"""
---
在你开始写寓言之前，请先回复上一篇的读者讨论：
上一篇标题：《{title}》
读者留言：{comment}

请生成一段简洁、有深度的回复（3-5句话），用 <div class="ai-reply"><h4>回复</h4><p>你的回复</p></div> 包裹。
---
"""

    return f"""{reply_part}
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


def build_reply_prompt(title, comment):
    return f"""
读者在阅读《{title}》后留言：
{comment}

请用中文生成一段简洁、有深度的回复（3-5句话）。
回复应当与概念相关，引导读者深入思考。
直接输出回复文本，不要有任何前缀。
"""


# ============================================================
# 单篇生成（核心）
# ============================================================
def generate_one_fable(state, concepts_data, today, check_discussion=False):
    """
    生成一篇寓言。返回 True 成功，False 失败。
    check_discussion: 仅第一篇时检查上篇讨论。
    """
    # 选择概念
    field, concept_name = concept_manager.select_random_concept(concepts_data)
    if concept_name is None:
        logger.warning("所有概念已用完！请扩充概念池。")
        return False

    story_number = state["total_generated"] + 1
    logger.info(f"--- 第 {story_number} 篇: [{field}] {concept_name} ---")

    # 讨论回复（仅第一篇）
    reply_context = None
    reply_text = None
    prev_title = prev_comment = None
    if check_discussion:
        prev_title, prev_comment = discussion_reader.read_previous_discussion(story_number)
        if prev_title and prev_comment:
            logger.info(f"发现上篇讨论: {prev_comment[:50]}...")
            reply_context = (prev_title, prev_comment)
            try:
                reply_text = call_llm(build_reply_prompt(prev_title, prev_comment))
            except Exception:
                reply_text = None

    # 生成寓言
    try:
        fable_content = call_llm(build_fable_prompt(concept_name, field, reply_context))
        fable_content = fable_content.strip()
        for prefix in ["```html", "```"]:
            if fable_content.startswith(prefix):
                fable_content = fable_content[len(prefix):]
        if fable_content.endswith("```"):
            fable_content = fable_content[:-3]
        fable_content = fable_content.strip()
        logger.info(f"内容生成完毕 ({len(fable_content)} 字符)")
    except Exception as e:
        logger.error(f"寓言生成失败: {e}")
        return False

    # 关联篇目
    related_links = []
    for r_name in concept_manager.get_related_concepts(concepts_data, concept_name):
        r_num = concept_manager.find_story_number_for_concept(r_name)
        if r_num:
            safe = r_name.replace("/", "-").replace("\\", "-").replace(" ", "_")
            related_links.append({"number": r_num, "name": r_name, "file": f"{r_num:03d}_{safe}.html"})

    # 保存 HTML
    story_html = html_builder.generate_story_html(
        story_number=story_number,
        concept_name=concept_name,
        field=field,
        fable_content=fable_content,
        reply_title=prev_title,
        reply_comment=prev_comment,
        reply_text=reply_text,
        related_links=related_links or None,
        date_str=today,
    )
    filename = html_builder.save_story(story_number, concept_name, story_html)
    logger.info(f"已保存: {filename}")

    # 更新状态
    concept_manager.mark_concept_used(concepts_data, concept_name, story_number)
    state["current_number"] = story_number
    state["total_generated"] = story_number
    state["last_generated_date"] = today
    state["last_concept"] = concept_name
    state["today_count"] = state.get("today_count", 0) + 1

    # 检查点
    if story_number % config.CHECKPOINT_INTERVAL == 0:
        logger.info(f"到达第 {story_number} 篇检查点！系统暂停。")
        state["is_paused"] = True
        state["checkpoints"].append({
            "at": story_number,
            "confirmed": False,
            "confirmed_date": None,
        })

    save_state(state)
    return True


# ============================================================
# 主流程：每日批量生成
# ============================================================
def main():
    logger.info("=" * 60)
    logger.info("每日寓言生成系统启动（批量模式）")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    os.makedirs(config.STORIES_DIR, exist_ok=True)
    os.makedirs(config.ASSETS_DIR, exist_ok=True)
    git_pull()

    state = load_state()
    today = reset_daily_counters(state)
    logger.info(f"状态: 总计{state['total_generated']}篇, 今日已生成{state.get('today_count',0)}篇, 暂停={state['is_paused']}")

    if state["is_paused"]:
        logger.info("系统已暂停，跳过生成。")
        return

    already = state.get("today_count", 0)
    remaining = config.DAILY_COUNT - already
    if remaining <= 0:
        logger.info(f"今日 {config.DAILY_COUNT} 篇已全部生成，跳过。")
        return

    concepts_data = concept_manager.load_concepts()
    generated = 0

    for i in range(remaining):
        if state["is_paused"]:
            logger.info("检查点暂停，停止后续生成。")
            break
        check_disc = (i == 0 and already == 0)  # 仅今日第一篇检查讨论
        ok = generate_one_fable(state, concepts_data, today, check_discussion=check_disc)
        if ok:
            generated += 1
            time.sleep(2)  # API 间隔，避免限流
        else:
            logger.warning(f"第 {i+1} 篇生成失败，跳过。")
            time.sleep(5)

    # 更新目录 & 推送
    html_builder.update_index_html(state, concepts_data)
    logger.info("目录首页已更新")
    git_push(state["total_generated"], f"batch_{generated}_fables")
    logger.info(f"[OK] 今日共生成 {generated} 篇寓言")
    logger.info("=" * 60)


# ============================================================
# 额外生成：处理 "再来一篇" 请求
# ============================================================
def extra_main():
    logger.info("=" * 60)
    logger.info("检查「再来一篇」请求")
    logger.info("=" * 60)

    os.makedirs(config.STORIES_DIR, exist_ok=True)
    git_pull()

    state = load_state()
    today = reset_daily_counters(state)

    if state["is_paused"]:
        logger.info("系统已暂停，跳过。")
        return

    extra_done = state.get("today_extra_count", 0)
    if extra_done >= config.MAX_EXTRA_PER_DAY:
        logger.info(f"今日已额外生成 {extra_done} 篇，达到上限。")
        return

    # 读取 GitHub Issues 中的 ONE_MORE 请求
    requests_count = count_extra_requests(state)
    if requests_count <= 0:
        logger.info("无「再来一篇」请求。")
        return

    to_generate = min(requests_count, config.MAX_EXTRA_PER_DAY - extra_done)
    logger.info(f"发现 {requests_count} 个请求，将生成 {to_generate} 篇额外寓言。")

    concepts_data = concept_manager.load_concepts()
    generated = 0

    for i in range(to_generate):
        if state["is_paused"]:
            break
        ok = generate_one_fable(state, concepts_data, today)
        if ok:
            state["today_extra_count"] = state.get("today_extra_count", 0) + 1
            save_state(state)
            generated += 1
            time.sleep(2)

    if generated > 0:
        html_builder.update_index_html(state, concepts_data)
        git_push(state["total_generated"], f"extra_{generated}_fables")
        logger.info(f"[OK] 额外生成 {generated} 篇")


def count_extra_requests(state):
    """从 GitHub Issues 读取未处理的 ONE_MORE 请求数"""
    processed = set(state.get("processed_issue_ids", []))
    try:
        url = f"https://api.github.com/repos/{config.GITHUB_OWNER}/{config.GITHUB_REPO}/issues?state=open&per_page=20"
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            issues = json.loads(resp.read().decode("utf-8"))

        new_requests = 0
        new_ids = []
        for issue in issues:
            if issue.get("title", "").strip().upper() == "ONE_MORE":
                iid = issue["id"]
                if iid not in processed:
                    new_requests += 1
                    new_ids.append(iid)

        # 标记为已处理
        if new_ids:
            if "processed_issue_ids" not in state:
                state["processed_issue_ids"] = []
            state["processed_issue_ids"].extend(new_ids)
            save_state(state)

        return new_requests
    except Exception as e:
        logger.warning(f"读取 GitHub Issues 失败: {e}")
        return 0


# ============================================================
# Git 操作
# ============================================================
GIT_EXE = os.path.join(config.BASE_DIR, "git", "cmd", "git.exe")


def _run_git(*args):
    import subprocess
    if not os.path.exists(GIT_EXE):
        return None
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


def git_pull():
    if not os.path.exists(GIT_EXE):
        return
    try:
        result = _run_git("pull", "origin", "main")
        if result and result.returncode == 0:
            logger.info("已从 GitHub 拉取最新内容")
    except Exception as e:
        logger.error(f"Git pull 异常: {e}")


def git_push(story_number, label):
    if not os.path.exists(GIT_EXE):
        return
    try:
        _run_git("add", "-A")
        _run_git("commit", "-m", f"auto: {label} (up to #{story_number:03d})")
        result = _run_git("push", "origin", "main")
        if result and result.returncode == 0:
            logger.info("GitHub Pages 推送成功")
    except Exception as e:
        logger.error(f"Git 推送异常: {e}")


# ============================================================
# CLI 入口
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="每日寓言生成系统")
    parser.add_argument("--extra", action="store_true", help="处理「再来一篇」请求")
    args = parser.parse_args()

    try:
        if args.extra:
            extra_main()
        else:
            main()
    except Exception as e:
        logger.error(f"致命错误: {e}", exc_info=True)
        sys.exit(1)
