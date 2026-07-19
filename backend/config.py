# VibeCoding 小红书爬虫平台配置文件
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

# 数据库配置
DATABASE_PATH = os.path.join(PROJECT_DIR, "data", "vibecoding.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# 爬虫配置
DEFAULT_KEYWORD = "vibecoding AI编程"
DEFAULT_COUNT = 50
CRAWL_INTERVAL_MIN = 1.0  # 最小请求间隔（秒）
CRAWL_INTERVAL_MAX = 3.0  # 最大请求间隔（秒）

# Flask 配置
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True

# 小红书 Cookie（可选，不填则使用模拟数据）
XHS_COOKIE = os.environ.get("XHS_COOKIE", "")

# 首次启动时自动生成示例数据
SEED_ON_START = False  # 关闭自动seed，用户自己爬取真实数据

# ==================== VibeCoding 内容分类体系 ====================

# 预设的 Vibecoding 搜索关键词
VIBECODING_KEYWORDS = [
    "vibecoding AI编程",
    "Cursor AI编程",
    "Bolt.new 开发",
    "v0 AI前端",
    "AI编程工具推荐",
    "0基础学编程 AI",
    "独立开发者 AI",
    "AI写代码神器",
    "Windsurf AI编程",
    "Lovable AI应用",
    "Claude Artifacts 编程",
    "Replit Agent 开发",
    "GitHub Copilot 教程",
    "AI全栈开发",
    "无代码开发 AI",
]

# AI 编程工具映射
VIBECODING_TOOLS = {
    "cursor": {"label": "Cursor", "icon": "🖥️", "color": "#7c3aed"},
    "windsurf": {"label": "Windsurf", "icon": "🌊", "color": "#3b82f6"},
    "bolt": {"label": "Bolt.new", "icon": "⚡", "color": "#f59e0b"},
    "v0": {"label": "v0", "icon": "▲", "color": "#06b6d4"},
    "lovable": {"label": "Lovable", "icon": "❤️", "color": "#ec4899"},
    "replit": {"label": "Replit Agent", "icon": "🔄", "color": "#8b5cf6"},
    "copilot": {"label": "GitHub Copilot", "icon": "🤖", "color": "#22c55e"},
    "claude": {"label": "Claude Artifacts", "icon": "🧠", "color": "#f97316"},
    "trae": {"label": "Trae (字节)", "icon": "🚀", "color": "#6366f1"},
    "tongyi": {"label": "通义灵码", "icon": "☁️", "color": "#0891b2"},
    "general": {"label": "综合/AI编程", "icon": "💡", "color": "#64748b"},
}

# 项目类型映射
PROJECT_TYPES = {
    "web_app": {"label": "网站应用", "icon": "🌐"},
    "mobile_app": {"label": "移动应用", "icon": "📱"},
    "chrome_ext": {"label": "浏览器插件", "icon": "🧩"},
    "game": {"label": "小游戏", "icon": "🎮"},
    "landing_page": {"label": "落地页/官网", "icon": "🏠"},
    "dashboard": {"label": "数据面板", "icon": "📊"},
    "tool": {"label": "效率工具", "icon": "🔧"},
    "api": {"label": "API服务", "icon": "🔌"},
    "saas": {"label": "SaaS产品", "icon": "☁️"},
    "automation": {"label": "自动化脚本", "icon": "🤖"},
    "component": {"label": "UI组件", "icon": "🎨"},
    "ai_app": {"label": "AI应用", "icon": "✨"},
    "viz": {"label": "数据可视化", "icon": "📈"},
    "other": {"label": "其他", "icon": "📦"},
}

# 难度映射
DIFFICULTY_LEVELS = {
    "beginner": {"label": "入门级", "color": "#22c55e", "desc": "0基础可做"},
    "intermediate": {"label": "进阶级", "color": "#f59e0b", "desc": "有一定基础"},
    "advanced": {"label": "高级", "color": "#ef4444", "desc": "复杂项目"},
}

# 内容分类映射
CONTENT_CATEGORIES = {
    "tutorial": {"label": "教程教学", "icon": "📖"},
    "showcase": {"label": "项目展示", "icon": "🎯"},
    "comparison": {"label": "工具对比", "icon": "⚖️"},
    "workflow": {"label": "工作流分享", "icon": "🔄"},
    "tips": {"label": "技巧心得", "icon": "💡"},
    "case_study": {"label": "实战案例", "icon": "🔥"},
    "review": {"label": "工具评测", "icon": "⭐"},
    "prompt": {"label": "提示词工程", "icon": "📝"},
}
