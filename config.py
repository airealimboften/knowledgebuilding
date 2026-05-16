# -*- coding: utf-8 -*-
"""每日寓言生成系统 - 配置文件"""

import os

# ============================================================
# 路径配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORIES_DIR = os.path.join(BASE_DIR, "stories")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# ============================================================
# API 配置
# ============================================================
# 主选：DeepSeek API
DEEPSEEK_API_KEY = "sk-00bbdababe7340a2b86dfa954335294b"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# ============================================================
# 访问控制
# ============================================================
# 页面访问密码（默认 "fable2026"，修改后需重新生成页面）
ACCESS_PASSWORD_HASH = "5dbf791e63b35eed8770399b1b509538107b6052c98f5484207d145fc5cf47a8"

# 授权的 GitHub 用户名（只有这些账号的留言会被读取和回复）
AUTHORIZED_USERS = ["airealimboften"]

# ============================================================
# GitHub 仓库信息（Giscus 评论 + API 读取）
# ============================================================
GITHUB_OWNER = "airealimboften"
GITHUB_REPO = "knowledgebuilding"
GITHUB_REPO_ID = "R_kgDOSe7aUA"
# Discussions 分类 ID（启用 Discussions 后填入）
GISCUS_CATEGORY = "General"
GISCUS_CATEGORY_ID = ""  # 待填入

# ============================================================
# 生成设置
# ============================================================
CHECKPOINT_INTERVAL = 100       # 每100篇暂停一次
FABLE_TARGET_LENGTH = 800       # 寓言目标字数
REQUEST_TIMEOUT = 60            # API请求超时（秒）
MAX_RETRIES = 3                 # API重试次数

# ============================================================
# 文件路径
# ============================================================
CONCEPTS_FILE = os.path.join(BASE_DIR, "concepts.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
INDEX_FILE = os.path.join(BASE_DIR, "index.html")
STYLES_FILE = os.path.join(BASE_DIR, "styles.css")
LOG_FILE = os.path.join(BASE_DIR, "generate.log")

# ============================================================
# 领域颜色映射（用于视觉区分）
# ============================================================
FIELD_COLORS = {
    "物理学": "#6c5ce7",
    "化学": "#00b894",
    "生物学": "#00cec9",
    "数学": "#fd79a8",
    "经济学": "#ffeaa7",
    "心理学": "#e17055",
    "社会学": "#dfe6e9",
    "哲学": "#a29bfe",
    "计算机科学": "#55efc4",
    "政治学": "#fab1a0",
    "人类学": "#fdcb6e",
    "语言学": "#74b9ff",
    "法学": "#b2bec3",
    "医学": "#ff7675",
    "地理学": "#81ecec",
    "历史学": "#ffeaa7",
    "艺术理论": "#e84393",
    "管理学": "#0984e3",
    "统计学": "#636e72",
    "生态学": "#00b894",
}
