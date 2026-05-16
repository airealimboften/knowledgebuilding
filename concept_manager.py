# -*- coding: utf-8 -*-
"""概念库管理模块 - 负责概念的随机选取、去重和动态扩展"""

import json
import random
import os
from datetime import datetime
import config


def load_concepts():
    """加载概念池"""
    with open(config.CONCEPTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_concepts(data):
    """保存概念池"""
    with open(config.CONCEPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all_available_concepts(data):
    """获取所有未使用的概念，返回 [(field, concept), ...]"""
    used = set(data.get("used_concepts", []))
    available = []
    for field, concepts in data["fields"].items():
        for c in concepts:
            if c not in used:
                available.append((field, c))
    return available


def select_random_concept(data):
    """
    随机选择一个未使用的概念。
    策略：先随机选领域，再从该领域中随机选概念。
    如果该领域概念已用完，换一个领域。
    """
    used = set(data.get("used_concepts", []))
    
    # 筛选还有可用概念的领域
    available_fields = {}
    for field, concepts in data["fields"].items():
        remaining = [c for c in concepts if c not in used]
        if remaining:
            available_fields[field] = remaining
    
    if not available_fields:
        return None, None  # 所有概念已用完
    
    # 随机选领域
    field = random.choice(list(available_fields.keys()))
    # 随机选概念
    concept = random.choice(available_fields[field])
    
    return field, concept


def mark_concept_used(data, concept, story_number):
    """标记概念已使用"""
    if "used_concepts" not in data:
        data["used_concepts"] = []
    data["used_concepts"].append(concept)
    save_concepts(data)


def get_related_concepts(data, concept):
    """
    获取与当前概念相关的概念列表。
    返回已生成的关联概念（用于生成超链接）。
    """
    related_map = data.get("related_map", {})
    used = set(data.get("used_concepts", []))
    
    related = related_map.get(concept, [])
    # 只返回已经生成过的关联概念
    existing_related = [r for r in related if r in used]
    
    return existing_related


def find_story_number_for_concept(concept):
    """查找某个概念对应的故事编号"""
    state = load_state()
    # 扫描stories目录查找文件名
    stories_dir = config.STORIES_DIR
    if not os.path.exists(stories_dir):
        return None
    
    for filename in os.listdir(stories_dir):
        if filename.endswith(".html") and concept in filename:
            # 提取编号，如 "001_纳什均衡.html" -> 1
            try:
                num = int(filename.split("_")[0])
                return num
            except (ValueError, IndexError):
                continue
    return None


def load_state():
    """加载状态"""
    with open(config.STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_concept_stats(data):
    """获取概念统计信息"""
    used = set(data.get("used_concepts", []))
    total = sum(len(v) for v in data["fields"].values())
    
    field_stats = {}
    for field, concepts in data["fields"].items():
        total_in_field = len(concepts)
        used_in_field = len([c for c in concepts if c in used])
        field_stats[field] = {
            "total": total_in_field,
            "used": used_in_field,
            "remaining": total_in_field - used_in_field
        }
    
    return {
        "total_concepts": total,
        "used_concepts": len(used),
        "remaining_concepts": total - len(used),
        "fields": field_stats
    }
