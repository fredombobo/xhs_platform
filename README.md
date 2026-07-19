# ⚡ VibeCoding 灵感发现平台

小红书热门 AI 编程 (VibeCoding) 项目与创意发现工具。

## 功能

- 🔍 **关键词搜索**：搜索小红书上的 VibeCoding / AI 编程相关热门内容
- 🌐 **真实浏览器爬取**：基于 Playwright 的浏览器自动化，获取真实小红书数据
- 🤖 **模拟数据模式**：无需登录即可体验，自动生成 VibeCoding 主题内容
- 🏷️ **多维度筛选**：按 AI 工具 (Cursor/Bolt/v0...)、难度、项目类型、内容分类筛选
- 🔥 **热门排行**：基于互动速度的热度排序
- 📊 **数据统计**：工具分布、难度分布可视化

## 快速开始

### 安装

```bash
pip install flask flask-cors requests sqlalchemy playwright
python -m playwright install chromium
```

### 启动

```bash
cd backend
python app.py
```

访问 **http://localhost:5000**

### 真实数据爬取

1. 点击左侧 **「🔐 登录小红书」** → 弹出浏览器窗口 → 扫码登录
2. 登录成功后，点击 **「🌐 真实浏览器爬取」** → 自动搜索并提取数据

> 登录状态保存在 `data/browser_profile/`，一次登录长期有效

### 模拟数据模式

无需登录，直接输入关键词点击 **「🚀 模拟爬取」** 即可生成体验数据。

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Flask + SQLAlchemy + SQLite |
| 真实爬虫 | Playwright (Chromium persistent context) |
| 模拟数据 | 关键词感知生成引擎 (hash种子) |
| 前端 | Vanilla JS SPA (零框架依赖) |
| 分类体系 | 12工具 × 14项目类型 × 3难度 × 8内容分类 |

## 项目结构

```
xhs_platform/
├── backend/
│   ├── app.py              # Flask API (10个端点)
│   ├── crawler.py           # 模拟数据引擎
│   ├── real_crawler.py      # Playwright 真实浏览器爬虫
│   ├── models.py            # SQLAlchemy 数据模型
│   └── config.py            # 配置 & 分类体系
├── frontend/
│   ├── index.html           # 页面结构
│   ├── app.js               # 前端全部逻辑
│   └── style.css            # 样式 (响应式)
└── data/                    # 运行时数据
    ├── vibecoding.db        # SQLite 数据库
    └── browser_profile/     # Playwright 登录状态
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/contents` | 内容列表 (支持 tool/difficulty/category 筛选) |
| POST | `/api/crawl` | 模拟爬取 |
| POST | `/api/crawl/real` | 真实浏览器爬取 |
| GET | `/api/stats` | 统计概览 (含分类分布) |
| GET | `/api/vibecoding/tools` | 工具列表 |
| GET | `/api/vibecoding/categories` | 分类选项 |
| GET | `/api/vibecoding/trending` | 热门排行 |
| POST | `/api/vibecoding/seed` | 手动生成示例数据 |
| POST | `/api/login-browser` | 打开登录浏览器 |
| GET | `/api/login-status` | 登录状态检查 |

## License

MIT
