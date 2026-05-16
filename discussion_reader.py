# -*- coding: utf-8 -*-
"""讨论区读取模块 - 从 GitHub Discussions (Giscus) 读取用户留言"""

import json
import urllib.request
import urllib.error
import logging

logger = logging.getLogger(__name__)


def read_previous_discussion(story_number):
    """
    读取上一篇寓言的 Giscus 讨论留言。

    通过 GitHub REST API 搜索 Discussions，找到上一篇的讨论，
    读取授权用户的最新留言。

    按照需求，仅读取：
    1. 上一篇寓言的标题（概念名称）
    2. 用户的留言内容（如果有）

    返回: (title, comment) 或 (None, None)
    """
    import config

    if story_number <= 1:
        return None, None

    prev_number = story_number - 1

    try:
        # 获取 Discussions 列表
        discussions = _fetch_discussions(config.GITHUB_OWNER, config.GITHUB_REPO)
        if not discussions:
            logger.info("未找到任何 Discussions")
            return _fallback_read_html(prev_number)

        # 查找上一篇的 Discussion（Giscus 用 data-term 映射）
        target_prefix = f"{prev_number:03d} "
        target_discussion = None

        for disc in discussions:
            title = disc.get("title", "")
            if title.startswith(target_prefix):
                target_discussion = disc
                break

        if not target_discussion:
            logger.info(f"未找到第 {prev_number:03d} 篇的 Discussion")
            return _fallback_read_html(prev_number)

        # 提取概念名称
        disc_title = target_discussion["title"]
        concept_name = disc_title[4:].strip()  # 去掉 "001 " 前缀

        # 获取评论
        disc_number = target_discussion["number"]
        comments = _fetch_discussion_comments(
            config.GITHUB_OWNER, config.GITHUB_REPO, disc_number
        )

        if not comments:
            logger.info(f"Discussion #{disc_number} 无评论")
            return None, None

        # 过滤授权用户的评论，取最新一条
        authorized = set(config.AUTHORIZED_USERS)
        user_comment = None
        for comment in reversed(comments):  # 从最新开始
            author = comment.get("user", {}).get("login", "")
            if author in authorized:
                user_comment = comment.get("body", "").strip()
                break

        if user_comment:
            logger.info(f"读取到授权用户留言: {user_comment[:50]}...")
            return concept_name, user_comment
        else:
            logger.info("无授权用户留言")
            return None, None

    except Exception as e:
        logger.error(f"读取 GitHub Discussions 失败: {e}")
        return _fallback_read_html(prev_number)


def _fetch_discussions(owner, repo):
    """通过 GitHub REST API 获取 Discussions 列表"""
    url = f"https://api.github.com/repos/{owner}/{repo}/discussions?per_page=30&direction=desc"
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.info("Discussions 未启用或 API 不可用")
        else:
            logger.warning(f"GitHub API 错误: {e.code}")
        return []
    except Exception as e:
        logger.warning(f"获取 Discussions 失败: {e}")
        return []


def _fetch_discussion_comments(owner, repo, discussion_number):
    """获取特定 Discussion 的评论"""
    url = f"https://api.github.com/repos/{owner}/{repo}/discussions/{discussion_number}/comments?per_page=30"
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning(f"获取评论失败: {e}")
        return []


def _fallback_read_html(story_number):
    """
    降级方案：如果 GitHub API 不可用，回退到读取本地 HTML 文件。
    兼容旧的直接编辑 HTML 方式。
    """
    import os
    from html.parser import HTMLParser
    import config

    class _CommentParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self._in_comment = False
            self._in_title = False
            self._comment_text = []
            self._title_text = []
            self._depth = 0
            self._found_h1 = False

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            if tag == "div" and "user-comment" in attrs_dict.get("class", ""):
                self._in_comment = True
                self._depth = 1
            elif self._in_comment:
                self._depth += 1
            if tag == "h1" and not self._found_h1:
                self._in_title = True
                self._found_h1 = True

        def handle_endtag(self, tag):
            if self._in_comment and tag == "div":
                self._depth -= 1
                if self._depth <= 0:
                    self._in_comment = False
            if self._in_title and tag == "h1":
                self._in_title = False

        def handle_data(self, data):
            if self._in_comment:
                text = data.strip()
                if text:
                    self._comment_text.append(text)
            if self._in_title:
                text = data.strip()
                if text:
                    self._title_text.append(text)

        def get_comment(self):
            return " ".join(self._comment_text).strip()

        def get_title(self):
            return " ".join(self._title_text).strip()

    # 查找文件
    if not os.path.exists(config.STORIES_DIR):
        return None, None

    prefix = f"{story_number:03d}_"
    for filename in os.listdir(config.STORIES_DIR):
        if filename.startswith(prefix) and filename.endswith(".html"):
            filepath = os.path.join(config.STORIES_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    html_content = f.read()

                parser = _CommentParser()
                parser.feed(html_content)

                title = parser.get_title() or None
                comment = parser.get_comment() or None

                if comment:
                    placeholders = ["在此处输入您的留言", "请在这里留下您的想法"]
                    for ph in placeholders:
                        comment = comment.replace(ph, "")
                    comment = comment.strip() or None

                return title, comment
            except Exception:
                return None, None

    return None, None
