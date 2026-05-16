# -*- coding: utf-8 -*-
"""讨论区读取模块 - 解析HTML中用户留言"""

import os
import re
from html.parser import HTMLParser


class DiscussionParser(HTMLParser):
    """解析HTML中讨论区的用户留言"""
    
    def __init__(self):
        super().__init__()
        self._in_comment = False
        self._in_title = False
        self._comment_text = []
        self._title_text = []
        self._found_comment_div = False
        self._found_h1 = False
        self._depth = 0
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # 查找用户留言区 <div class="user-comment">
        if tag == "div" and "user-comment" in attrs_dict.get("class", ""):
            self._in_comment = True
            self._found_comment_div = True
            self._depth = 1
        elif self._in_comment:
            self._depth += 1
        
        # 查找标题 <h1>
        if tag == "h1" and not self._found_h1:
            self._in_title = True
            self._found_h1 = True
    
    def handle_endtag(self, tag):
        if self._in_comment:
            if tag == "div":
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


def read_previous_discussion(story_number):
    """
    读取上一篇寓言的标题和讨论区留言。
    
    按照需求，只读取：
    1. 上一篇寓言的标题（概念名称）
    2. 用户的留言内容（如果有）
    
    返回: (title, comment) 或 (None, None)
    """
    from config import STORIES_DIR
    
    if story_number <= 1:
        return None, None
    
    prev_number = story_number - 1
    prev_file = _find_story_file(prev_number)
    
    if not prev_file:
        return None, None
    
    try:
        with open(prev_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        parser = DiscussionParser()
        parser.feed(html_content)
        
        title = parser.get_title()
        comment = parser.get_comment()
        
        # 过滤掉HTML注释标记文本
        if comment:
            # 去除提示性文字
            placeholders = [
                "在此处输入您的留言",
                "请在这里留下您的想法",
                "===== 在下方留言 =====",
                "===== 留言结束 ====="
            ]
            for ph in placeholders:
                comment = comment.replace(ph, "")
            comment = comment.strip()
        
        return title if title else None, comment if comment else None
        
    except Exception as e:
        print(f"读取讨论区失败: {e}")
        return None, None


def _find_story_file(story_number):
    """根据编号查找故事文件"""
    from config import STORIES_DIR
    
    if not os.path.exists(STORIES_DIR):
        return None
    
    prefix = f"{story_number:03d}_"
    for filename in os.listdir(STORIES_DIR):
        if filename.startswith(prefix) and filename.endswith(".html"):
            return os.path.join(STORIES_DIR, filename)
    
    return None
