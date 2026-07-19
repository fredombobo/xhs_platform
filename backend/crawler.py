"""VibeCoding 小红书内容爬虫模块"""
import random
import hashlib
import time
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 导入配置中的分类体系
from config import (
    VIBECODING_TOOLS,
    PROJECT_TYPES,
    DIFFICULTY_LEVELS,
    CONTENT_CATEGORIES,
)


class XiaohongshuCrawler:
    """
    小红书内容爬虫

    支持两种模式：
    1. 真实模式：配置 Cookie 后调用真实小红书 API
    2. 模拟模式：使用精心构造的 VibeCoding 模拟数据（无需登录，开箱即用）

    真实 API 说明：
    - 搜索接口: POST https://edith.xiaohongshu.com/api/sns/web/v1/search/notes
    - 需要 X-S, X-T 签名，Cookie 中需要 a1, web_session 等字段
    """

    BASE_URL = "https://edith.xiaohongshu.com"
    SEARCH_API = "/api/sns/web/v1/search/notes"

    def __init__(self, cookie: str = ""):
        self.cookie = cookie
        self._session = None
        self._use_real = bool(cookie and cookie.strip())

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(self._build_headers())
        return self._session

    def _build_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://www.xiaohongshu.com",
            "Referer": "https://www.xiaohongshu.com/",
            "Cookie": self.cookie,
            "X-B3-Traceid": hashlib.md5(str(time.time()).encode()).hexdigest()[:16],
        }

    def _generate_x_s(self, url: str, data: dict) -> str:
        """生成 X-S 签名（简化版）"""
        sorted_keys = sorted(data.keys())
        raw = url + "&".join(f"{k}={data[k]}" for k in sorted_keys if data[k] is not None)
        return hashlib.md5(raw.encode()).hexdigest()

    def search_notes(self, keyword: str, count: int = 50) -> List[Dict]:
        """搜索笔记入口"""
        if self._use_real:
            print(f"[真实模式] 搜索关键词: {keyword}")
            return self._real_search(keyword, count)
        else:
            print(f"[模拟模式] 搜索关键词: {keyword}，生成 {count} 条 VibeCoding 数据")
            return self._generate_vibecoding_mock_data(keyword, count)

    def _real_search(self, keyword: str, count: int) -> List[Dict]:
        """通过真实 API 爬取"""
        results = []
        cursor = ""
        max_pages = (count // 20) + 2

        for page in range(max_pages):
            if len(results) >= count:
                break

            payload = {
                "keyword": keyword,
                "page": str(page + 1),
                "page_size": min(20, count - len(results)),
                "search_id": hashlib.md5(
                    f"{time.time()}{random.random()}".encode()
                ).hexdigest(),
                "sort": "general",
                "note_type": 0,
                "cursor": cursor,
                "ext_flags": [],
                "image_formats": ["jpg", "webp", "avif"],
            }

            headers = self._build_headers()
            headers["X-S"] = self._generate_x_s(self.SEARCH_API, payload)
            headers["X-T"] = str(int(time.time() * 1000))
            headers["X-S-Common"] = hashlib.md5(
                f"{int(time.time())}{random.randint(0, 9999)}".encode()
            ).hexdigest()

            try:
                resp = requests.post(
                    f"{self.BASE_URL}{self.SEARCH_API}",
                    json=payload,
                    headers=headers,
                    timeout=15
                )

                if resp.status_code == 471:
                    print("触发验证码，请手动处理")
                    break
                if resp.status_code != 200:
                    print(f"API 返回状态码: {resp.status_code}")
                    break

                data = resp.json()
                if not data.get("success"):
                    print(f"API 错误: {data.get('msg', '未知错误')}")
                    break

                items = data.get("data", {}).get("items", [])
                if not items:
                    print("没有更多数据")
                    break

                for item in items:
                    note = item.get("note_card") or item
                    info = note.get("interact_info", {})
                    user = note.get("user", {})
                    cover_info = note.get("cover", {})

                    results.append({
                        "note_id": item.get("id", ""),
                        "title": note.get("display_title", ""),
                        "description": note.get("desc", ""),
                        "author_name": user.get("nickname", "") or user.get("name", ""),
                        "author_id": str(user.get("user_id", "")),
                        "cover_url": cover_info.get("url", "") or cover_info.get("url_default", ""),
                        "video_url": note.get("video", {}).get("media", {}).get("stream", {}).get("h264", [{}])[0].get("master_url", "") if note.get("video") else "",
                        "images": [
                            img.get("url_default", img.get("url", ""))
                            for img in note.get("image_list", [])
                        ],
                        "likes": int(info.get("liked_count", 0) or 0),
                        "collects": int(info.get("collected_count", 0) or 0),
                        "comments": int(info.get("comment_count", 0) or 0),
                        "shares": int(info.get("share_count", 0) or 0),
                        "tags": [
                            t.get("name", "")
                            for t in note.get("tag_list", [])
                        ],
                        # VibeCoding 字段（真实模式暂不分类）
                        "tool_name": None,
                        "project_type": None,
                        "difficulty_level": None,
                        "content_category": None,
                        "source_url": "",
                        "is_trending": False,
                        "ai_confidence": 0.0,
                        "publish_time": datetime.fromtimestamp(
                            note.get("time", time.time())
                        ).isoformat(),
                    })

                cursor = data.get("data", {}).get("cursor", "")
                if not cursor:
                    break

                time.sleep(random.uniform(1.0, 3.0))

            except requests.RequestException as e:
                print(f"请求异常: {e}")
                break
            except Exception as e:
                print(f"解析异常: {e}")
                break

        return results

    # ==================== VibeCoding 模拟数据 ====================

    # ---- 标题模板库 ----
    TITLE_TEMPLATES = [
        # Cursor + web_app
        {"title": "用Cursor 10分钟做了一个AI导航站，小白0基础也能做", "tool": "cursor", "project_type": "web_app", "difficulty": "beginner", "category": "showcase"},
        {"title": "Cursor写的个人博客上线了！附完整Prompt和部署教程", "tool": "cursor", "project_type": "web_app", "difficulty": "intermediate", "category": "tutorial"},
        {"title": "用Cursor搭建了一个在线工具箱，太好用了", "tool": "cursor", "project_type": "tool", "difficulty": "intermediate", "category": "showcase"},

        # Cursor + chrome_ext
        {"title": "用Cursor写了个Chrome插件，自动总结网页内容，太强了", "tool": "cursor", "project_type": "chrome_ext", "difficulty": "intermediate", "category": "showcase"},
        {"title": "Cursor写浏览器插件保姆级教程｜从0到上架", "tool": "cursor", "project_type": "chrome_ext", "difficulty": "beginner", "category": "tutorial"},

        # Bolt.new
        {"title": "Bolt.new真的太香了！10分钟做出一个完整的问卷调查系统", "tool": "bolt", "project_type": "web_app", "difficulty": "beginner", "category": "showcase"},
        {"title": "用Bolt.new做了个SaaS仪表盘，一句话描述需求就生成了", "tool": "bolt", "project_type": "dashboard", "difficulty": "beginner", "category": "showcase"},
        {"title": "Bolt.new vs Cursor vs v0 三款AI编程工具横评", "tool": "general", "project_type": "other", "difficulty": "intermediate", "category": "comparison"},
        {"title": "0基础用Bolt.new做了个记账App，感觉可以创业了", "tool": "bolt", "project_type": "tool", "difficulty": "beginner", "category": "showcase"},

        # v0
        {"title": "v0 5分钟生成了一个高级感官网，设计师看完沉默了", "tool": "v0", "project_type": "landing_page", "difficulty": "beginner", "category": "showcase"},
        {"title": "v0 + Cursor联动工作流分享，效率翻倍！", "tool": "v0", "project_type": "web_app", "difficulty": "intermediate", "category": "workflow"},
        {"title": "用v0生成UI组件库，前端开发速度起飞了", "tool": "v0", "project_type": "component", "difficulty": "intermediate", "category": "tips"},
        {"title": "v0最新功能实测！AI生成的前端代码质量到底怎么样", "tool": "v0", "project_type": "other", "difficulty": "intermediate", "category": "review"},

        # Windsurf
        {"title": "从Cursor叛变到Windsurf的真实体验｜一周使用报告", "tool": "windsurf", "project_type": "other", "difficulty": "intermediate", "category": "review"},
        {"title": "Windsurf生成的实时数据面板，颜值和功能都在线", "tool": "windsurf", "project_type": "dashboard", "difficulty": "intermediate", "category": "showcase"},
        {"title": "Windsurf + Supabase 全栈开发实战，一天上线一个项目", "tool": "windsurf", "project_type": "saas", "difficulty": "advanced", "category": "case_study"},

        # Lovable
        {"title": "用Lovable三天做出了一个SaaS MVP，已经收到第一批付费用户", "tool": "lovable", "project_type": "saas", "difficulty": "advanced", "category": "case_study"},
        {"title": "Lovable搭建AI聊天应用全过程，附完整操作录屏", "tool": "lovable", "project_type": "ai_app", "difficulty": "intermediate", "category": "tutorial"},

        # Replit
        {"title": "Replit Agent写了个Discord机器人，全程在浏览器完成", "tool": "replit", "project_type": "automation", "difficulty": "beginner", "category": "showcase"},
        {"title": "用Replit Agent零基础做了个API服务，部署只需点一下", "tool": "replit", "project_type": "api", "difficulty": "beginner", "category": "tutorial"},

        # GitHub Copilot
        {"title": "GitHub Copilot新Agent模式深度体验，编程效率直接翻10倍", "tool": "copilot", "project_type": "other", "difficulty": "intermediate", "category": "review"},
        {"title": "Copilot Agent自动重构了5000行代码，我直接震惊了", "tool": "copilot", "project_type": "automation", "difficulty": "advanced", "category": "tips"},
        {"title": "用Copilot写了一个自动化数据采集脚本，原来要3天的活10分钟搞定", "tool": "copilot", "project_type": "automation", "difficulty": "intermediate", "category": "case_study"},

        # Claude
        {"title": "Claude Artifacts写了个AI聊天应用，全在浏览器里完成", "tool": "claude", "project_type": "ai_app", "difficulty": "beginner", "category": "showcase"},
        {"title": "Claude Artifacts + MCP Server搭建个人知识库，搜索效率拉满", "tool": "claude", "project_type": "tool", "difficulty": "intermediate", "category": "tutorial"},

        # Trae
        {"title": "字节的Trae真的太卷了！免费还好用，Cursor平替实锤", "tool": "trae", "project_type": "other", "difficulty": "beginner", "category": "review"},
        {"title": "Trae国内直接能用！用它做了个天气预报小程序", "tool": "trae", "project_type": "mobile_app", "difficulty": "beginner", "category": "showcase"},

        # 通义灵码
        {"title": "通义灵码免费AI编程助手实测，阿里这波配享太庙", "tool": "tongyi", "project_type": "other", "difficulty": "beginner", "category": "review"},

        # General / Multi-tool
        {"title": "2025年AI编程工具大盘点，这8个工具让你效率翻倍", "tool": "general", "project_type": "other", "difficulty": "beginner", "category": "comparison"},
        {"title": "从0到1：我的AI全栈开发工作流大公开", "tool": "general", "project_type": "web_app", "difficulty": "intermediate", "category": "workflow"},
        {"title": "VibeCoding入门指南｜不会写代码也能做产品", "tool": "general", "project_type": "other", "difficulty": "beginner", "category": "tutorial"},
        {"title": "独立开发者必看！AI编程工具全流程实战分享", "tool": "general", "project_type": "saas", "difficulty": "intermediate", "category": "case_study"},
        {"title": "写给程序员的VibeCoding心法，从抵触到真香", "tool": "general", "project_type": "other", "difficulty": "intermediate", "category": "tips"},
        {"title": "用了3个月AI编程的真实感受，这10个技巧一定要知道", "tool": "general", "project_type": "other", "difficulty": "intermediate", "category": "tips"},
        {"title": "AI编程时代来了！普通人如何抓住这波红利", "tool": "general", "project_type": "other", "difficulty": "beginner", "category": "tips"},
    ]

    # ---- 描述模板库 ----
    DESC_TEMPLATES = [
        # 教程型
        "最近被问到最多的就是「这个项目怎么做的」，今天终于把教程肝出来了！\n\n全程用的{tool}，从0开始手把手教你。即使完全没写过代码也能跟着做出来，我已经尽量把每一步都截图标注了。\n\n📌 核心步骤：\n1️⃣ 先用一句话描述你想要的功能\n2️⃣ 让AI生成第一版代码\n3️⃣ 根据预览效果迭代优化\n4️⃣ 部署上线\n\n整个过程下来大概花了{time_desc}，以前让我手写至少要一周！\n\n姐妹们一定要收藏起来慢慢看，不然刷着刷着就找不到了 🔖",
        # 展示型 - 激动
        "谁懂啊！！我真的就是用一句话把这个{difficulty_desc}做出来了 🤯\n\n之前总觉得自己不懂编程做不了产品，直到朋友给我推荐了{tool}，简直打开了新世界的大门！\n\n🎯 项目功能：\n• {feature1}\n• {feature2}\n• {feature3}\n\n本来只是抱着试一试的心态，没想到真的能跑起来而且效果还不错。同事看到以后以为我偷偷报了个编程培训班 hhhh\n\n真的强烈推荐给所有想做自己产品但被代码劝退的宝子们 💪",
        # 对比型
        "作为一个重度AI编程用户，我把市面上主流的几款工具都深度用了一遍，今天给大家做个真实对比 📊\n\n目前体验过的工具：Cursor、Windsurf、Bolt.new、v0、Lovable、Replit、Copilot\n\n⚡ 速度：Bolt.new > v0 > Lovable\n🧠 代码质量：Cursor > Windsurf > Copilot\n💰 性价比：Trae > 通义灵码 > Copilot\n🎨 UI生成：v0 > Bolt.new > Lovable\n📚 学习曲线：Bolt.new最低 > v0 > Lovable\n\n详细的使用感受都写在图里了，建议保存！\n\n总体来说{tool}在{strength}方面真的是天花板级别的 👍",
        # 工作流分享型
        "分享一个我最近摸索出来的超高效 VibeCoding 工作流 🔄\n\n💡 核心思路：用{tool}负责{role1}，搭配其他工具负责{role2}\n\n我的日常开发流程：\n☀️ 早上：用AI生成项目框架和核心功能\n🔧 下午：手动微调和测试\n🚀 晚上：部署上线 + 收集反馈\n\n用了这个工作流以后，以前一个月的项目现在一周就能搞定。关键是不用再纠结技术细节，可以把精力放在产品想法和用户体验上！\n\n评论区告诉我你们用的是什么组合？👇",
        # 技巧型
        "整理了100条{tool}的Prompt技巧精华版！这些都是我踩了无数坑总结出来的 🎓\n\n❌ 错误做法：「帮我做一个网站」→ AI一脸懵逼\n✅ 正确做法：「用React做一个响应式的待办事项列表，支持添加/删除/标记完成，数据存localStorage」\n\n💡 核心心法：\n1. 描述越具体，生成越精准\n2. 拆分成小步骤，不要一次生成太多\n3. 善用「参考XX网站的XX功能」来描述\n4. 报错直接复制粘贴给AI，让它自己修\n5. 每次只改一个功能，改完测试再加新的\n\n掌握了这些技巧，效率至少翻3倍！赶紧码住慢慢消化 📌",
        # 实战案例型
        "分享一下我用{tool}做{difficulty_desc}的真实经历！\n\n💭 起因：{pain_point}\n🔧 工具：{tool}\n⏱️ 时间：{time_desc}\n💰 成本：几乎为0（就花了点电费 hhh）\n\n📈 上线后的数据：\n• 第一天{day1_users}个用户\n• 一周后{week_users}个用户\n• 收到了好多正向反馈\n\n这个项目虽然简单，但是扎扎实实解决了真实需求。VibeCoding 的魅力就在于 —— 想到就能做到，不需要纠结技术栈，不需要招研发团队，一个人就是一支军队 💪\n\n对项目感兴趣的宝子可以评论区扣1，我分享完整Prompt 👇",
        # 心得型
        "VibeCoding 这条路走了有{months}个月了，从一开始的各种翻车到现在的行云流水，有些真心话想说 📝\n\n🔸 不要追求一次生成完美——迭代才是王道\n🔸 不要跳过手动review环节——AI也会犯错\n🔸 不要上来就做复杂项目——从简单的工具开始\n🔸 不要把AI当作替代品——它是你的超级助手\n🔸 不要停止学习——至少理解代码的基本结构\n\n最重要的是：开始做，而不是一直观望！\n\n记得我当时第一个项目就花了一个下午，虽然很简陋但那种「我真的做出来了」的成就感至今难忘 ✨\n\n你开始用AI编程了吗？来评论区聊聊 👇",
        # 评测型
        "{tool}用了整整{time_desc}，今天来交作业了 🎯\n\n✅ 优点：\n• {pro1}\n• {pro2}\n• {pro3}\n\n⚠️ 缺点：\n• {con1}\n• {con2}\n\n💡 适合人群：{target_users}\n\n🏆 综合评分：{rating}/10分\n\n总体来说这款工具在{strength}方面表现非常出色，如果你也{user_scenario}，强烈建议试一下！\n\n关注我，持续分享AI编程工具真实体验 🫡",
        # 灵感型
        "分享10个用AI编程可以做的{difficulty_desc}项目灵感！每一个都是真实有人做出来的 💡\n\n1️⃣ {idea1}\n2️⃣ {idea2}\n3️⃣ {idea3}\n4️⃣ {idea4}\n5️⃣ {idea5}\n\n这些项目都不需要太深的技术背景，关键是要有好的想法和执行力！用{tool}基本半天到一天就能做一个出来。\n\n我自己已经在做第3个了，做完来分享效果！你们最想尝试哪个？评论区告诉我编号 👇",
    ]

    # ---- 标签池 ----
    TAG_POOL = {
        "tool": ["#Cursor", "#Windsurf", "#Boltnew", "#v0", "#Lovable", "#Replit", "#Copilot",
                 "#Claude", "#Trae", "#通义灵码", "#AI编程工具"],
        "theme": ["#VibeCoding", "#AI编程", "#AI写代码", "#0基础学编程", "#效率工具",
                  "#独立开发者", "#一人公司", "#副业搞钱", "#数字创业", "#无代码开发",
                  "#AI全栈", "#程序员日常", "#开发日记"],
        "project": ["#网站建设", "#浏览器插件", "#小程序开发", "#游戏开发", "#APP开发",
                    "#自动化脚本", "#数据可视化", "#AI应用", "#个人博客", "#SaaS"],
        "style": ["#保姆级教程", "#干货分享", "#宝藏工具", "#上手实测", "#好物推荐",
                  "#效率提升", "#工作流", "#自学编程"],
    }

    # ---- 作者名库 ----
    AUTHORS = [
        "独立开发者小王", "AI编程日记", "全栈小刘", "不码不行的Daye",
        "VibeCoding实践者", "AI全栈探索", "产品经理学编程", "数字游民Jack",
        "程序媛的日常", "一人公司笔记", "0基础码农进化中", "阿坤的AI编程",
        "效率工具挖掘机", "独立开发从0开始", "技术宅小鱼", "AI应用实验室",
        "代码与生活", "非典型程序员", "创业中的前端", "AI全栈练习生",
    ]

    # ---- 项目灵感库 ----
    PROJECT_IDEAS = [
        ["个人博客/作品集网站", "待办事项+番茄钟工具", "Markdown笔记应用", "图片压缩工具", "数字货币价格面板"],
        ["习惯打卡小程序", "追剧进度管理", "AI文案生成器", "个人财务管理", "读书笔记管理"],
        ["简历生成器", "倒计时合集", "链接收藏夹", "随机决策器", "表情包制作工具"],
        ["RSS阅读器", "文件批量重命名", "账单AA计算器", "密码生成器", "表情日记"],
    ]

    # ---- 描述模板的动态填充数据 ----
    TIME_DESCS = ["一个下午", "2小时", "3小时", "一个晚上", "周末两天", "半天", "不到一天", "一个小时"]
    PAIN_POINTS = [
        "每天手动整理报表太累了",
        "老板要做一个数据看板，但公司没前端资源",
        "想做个个人网站但请不起外包",
        "团队需要一个内部工具，排期排了三个月",
        "想验证一个产品想法但MVP都没人做",
    ]
    FEATURES_POOL = [
        ["用户注册登录系统", "数据可视化图表", "文件上传下载", "搜索和筛选功能", "响应式设计适配移动端"],
        ["实时数据更新", "深色模式切换", "多语言支持", "导出PDF/Excel", "社交分享功能"],
        ["拖拽排序", "标签分类管理", "关键词搜索", "消息推送通知", "权限管理系统"],
    ]
    PROS = [
        "生成速度极快，基本不用等",
        "代码质量高，bug少",
        "界面友好，上手零门槛",
        "支持中文Prompt，沟通无障碍",
        "免费额度够用，个人项目完全Cover",
        "社区生态好，模板和教程多",
        "部署一键搞定，不用配环境",
    ]
    CONS = [
        "复杂业务逻辑偶尔翻车",
        "对大型项目的上下文理解有限",
        "有时候会生成过时的API",
        "免费版有次数限制",
        "偶尔会自己'优化'掉你想要的功能",
        "对非英文Prompt的理解有时不够精准",
    ]
    TARGET_USERS = [
        "想快速验证产品想法的创业者",
        "不会写代码但想做工具的产品经理",
        "独立开发者/自由职业者",
        "想学编程但不知从何下手的初学者",
        "需要快速出Demo的创业者",
        "想做自己工具的运营/市场同学",
    ]

    @classmethod
    def _clean_keyword(cls, keyword: str) -> str:
        """清理关键词，提取有用信息"""
        kw = keyword.strip()
        # 去掉常见的无意义前缀
        for prefix in ["搜索", "查找", "爬取", "关于"]:
            if kw.startswith(prefix):
                kw = kw[len(prefix):].strip()
        return kw or "vibecoding AI编程"

    @classmethod
    def _pick_tool_for_keyword(cls, keyword: str) -> Optional[str]:
        """根据关键词推断目标工具"""
        kw_lower = keyword.lower()
        tool_map = {
            "cursor": "cursor",
            "windsurf": "windsurf",
            "bolt": "bolt",
            "v0": "v0",
            "lovable": "lovable",
            "replit": "replit",
            "copilot": "copilot",
            "claude": "claude",
            "trae": "trae",
            "通义": "tongyi",
            "灵码": "tongyi",
        }
        for k, v in tool_map.items():
            if k in kw_lower:
                return v
        return None

    # ---- 关键词注入标题模板 ----
    KEYWORD_TITLE_TEMPLATES = [
        "用AI做了个{keyword}，真的太香了！附完整教程",
        "{keyword}怎么做？AI编程10分钟帮你搞定",
        "被问爆了！{keyword}的AI实现方案全分享",
        "0基础用AI做{keyword}，保姆级教学来了",
        "{keyword}天花板！用AI编程轻松实现",
        "熬夜整理了{keyword}的AI开发攻略，建议收藏",
        "{keyword}｜AI编程初学者的第一个项目",
        "手把手教你用AI做{keyword}，一看就会",
        "{keyword}的AI实现方法，这也太好用了吧",
        "用AI编程做{keyword}是什么体验？太上头了",
        "分享一个{keyword}的AI全栈开发方案",
        "最近超火的{keyword}，用AI编程轻松复刻",
        "{keyword}灵感 | AI编程实现创意项目",
        "朋友都问链接的{keyword}，全程AI编写",
        "{keyword}的AI编程实战，从想法到上线",
    ]

    @classmethod
    def _pick_template_for_keyword(cls, keyword: str, index: int) -> dict:
        """根据关键词和索引选择标题模板，关键词不同结果不同"""
        target_tool = cls._pick_tool_for_keyword(keyword)
        kw_lower = keyword.lower()

        # 用关键词的 hash 来打乱顺序，确保不同关键词得到不同的模板顺序
        kw_hash = sum(ord(c) for c in keyword)
        rng = random.Random(kw_hash + index * 7)

        # 筛选候选模板
        candidates = cls.TITLE_TEMPLATES[:]

        if target_tool:
            # 优先选择匹配工具的模板
            tool_candidates = [t for t in candidates if t["tool"] == target_tool]
            if tool_candidates:
                candidates = tool_candidates

        # 根据关键词中的项目类型进一步筛选
        if "插件" in kw_lower or "chrome" in kw_lower:
            type_candidates = [t for t in candidates if t["project_type"] == "chrome_ext"]
            if type_candidates:
                candidates = type_candidates
        elif "游戏" in kw_lower:
            type_candidates = [t for t in candidates if t["project_type"] == "game"]
            if type_candidates:
                candidates = type_candidates
        elif "教程" in kw_lower or "入门" in kw_lower or "0基础" in kw_lower:
            type_candidates = [t for t in candidates if t["category"] == "tutorial"]
            if type_candidates:
                candidates = type_candidates

        # 打乱候选顺序（同关键词同 index 结果一致，不同关键词结果不同）
        rng.shuffle(candidates)

        return candidates[index % len(candidates)]

    @classmethod
    def _generate_keyword_title(cls, keyword: str, tool: str, index: int) -> str:
        """为搜索关键词动态生成标题——让不同搜索返回不同标题"""
        kw_hash = sum(ord(c) for c in keyword)
        rng = random.Random(kw_hash + index * 13)

        # 40% 概率使用关键词注入模板（让关键词直接出现在标题中）
        if rng.random() < 0.4:
            template = rng.choice(cls.KEYWORD_TITLE_TEMPLATES)
            return template.replace("{keyword}", keyword)

        # 否则用工具相关的默认标题
        return None  # 返回 None 表示使用原有模板逻辑

    @staticmethod
    def _format_description(template: str, item: dict) -> str:
        """填充描述模板中的动态变量"""
        tool_label = VIBECODING_TOOLS.get(item.get("tool_name", "general"), {}).get("label", "AI编程工具")
        diff_key = item.get("difficulty_level", "beginner")
        diff_label = DIFFICULTY_LEVELS.get(diff_key, {}).get("label", "入门级")

        replacements = {
            "{tool}": tool_label,
            "{difficulty_desc}": diff_label + "项目",
            "{time_desc}": random.choice(XiaohongshuCrawler.TIME_DESCS),
            "{pain_point}": random.choice(XiaohongshuCrawler.PAIN_POINTS),
            "{months}": str(random.choice([1, 2, 3, 6, 8])),
            "{day1_users}": str(random.choice([50, 100, 200, 500, 1000])),
            "{week_users}": str(random.choice([500, 1000, 2000, 5000, 10000])),
            "{rating}": str(random.choice([8, 8.5, 9, 9.5])),
            "{strength}": random.choice(["代码生成", "UI设计", "全栈开发", "上手速度", "性价比", "中文支持"]),
            "{role1}": random.choice(["生成核心代码", "搭建前端页面", "写后端逻辑", "设计UI组件"]),
            "{role2}": random.choice(["部署运维", "UI美化", "代码审查", "测试调试"]),
            "{pro1}": random.choice(XiaohongshuCrawler.PROS),
            "{pro2}": random.choice([p for p in XiaohongshuCrawler.PROS if p != "{pro1}"]),
            "{pro3}": random.choice(XiaohongshuCrawler.PROS[:4]),
            "{con1}": random.choice(XiaohongshuCrawler.CONS),
            "{con2}": random.choice([c for c in XiaohongshuCrawler.CONS if c != "{con1}"]),
            "{target_users}": random.choice(XiaohongshuCrawler.TARGET_USERS),
            "{user_scenario}": random.choice(["想做自己的小工具", "想快速上线MVP", "想做个人作品集", "想提高开发效率"]),
        }

        # 处理 features
        features = random.choice(XiaohongshuCrawler.FEATURES_POOL)
        for j in range(1, 4):
            replacements[f"{{feature{j}}}"] = features[j - 1] if j <= len(features) else ""

        # 处理 ideas
        ideas = random.choice(XiaohongshuCrawler.PROJECT_IDEAS)
        for j in range(1, 6):
            replacements[f"{{idea{j}}}"] = ideas[j - 1] if j <= len(ideas) else ""

        result = template
        for key, val in replacements.items():
            result = result.replace(key, val)

        return result

    @classmethod
    def _generate_vibecoding_mock_data(cls, keyword: str, count: int = 50) -> List[Dict]:
        """
        生成高质量的 VibeCoding 模拟数据

        核心改进：不同关键词返回不同结果
        - 标题动态融入搜索关键词
        - 使用关键词 hash 作为随机种子，同关键词结果可复现
        - 工具/项目类型/难度根据关键词智能选择
        """
        results = []
        now = datetime.now()
        cleaned_kw = cls._clean_keyword(keyword)

        # 用关键词 hash 作为主随机种子，确保不同关键词 → 不同结果
        kw_hash = sum(ord(c) for c in cleaned_kw)
        main_rng = random.Random(kw_hash)

        for i in range(count):
            # 每个 item 用独立种子（关键词+索引），保证同关键词同索引结果一致
            item_rng = random.Random(kw_hash + i * 31)

            # ---- 1. 选择模板 ----
            template = cls._pick_template_for_keyword(cleaned_kw, i)

            tool = template.get("tool", "general")
            project_type = template.get("project_type", "other")
            difficulty = template.get("difficulty", "beginner")
            category = template.get("category", "showcase")

            # 如果模板没有指定 tool，根据关键词智能选择
            if tool == "general":
                target_tool = cls._pick_tool_for_keyword(cleaned_kw)
                if target_tool:
                    tool = target_tool
                elif item_rng.random() < 0.7:
                    # 用 seeded rng 选择工具（不同关键词选不同工具）
                    all_tools = [t for t in VIBECODING_TOOLS.keys() if t != "general"]
                    tool = item_rng.choice(all_tools)

            # ---- 2. 标题 ----
            # 尝试用关键词注入生成标题
            keyword_title = cls._generate_keyword_title(cleaned_kw, tool, i)
            if keyword_title:
                title = keyword_title
                # 将 {tool} 替换为实际工具名
                if "{tool}" in title:
                    tool_label = VIBECODING_TOOLS.get(tool, {}).get("label", "AI编程工具")
                    title = title.replace("{tool}", tool_label)
            else:
                title = template["title"]
                if "{tool}" in title:
                    tool_label = VIBECODING_TOOLS.get(tool, {}).get("label", "AI编程工具")
                    title = title.replace("{tool}", tool_label)
                # 对于 general 类模板，有概率将关键词融入标题
                if template["tool"] == "general" and item_rng.random() < 0.3:
                    title = title.replace("AI编程", f"{cleaned_kw}")

            # ---- 3. 描述 ----
            desc_template = item_rng.choice(cls.DESC_TEMPLATES)
            item_data = {"tool_name": tool, "difficulty_level": difficulty}
            description = cls._format_description(desc_template, item_data)

            # ---- 4. 标签 ----
            tags = []
            tool_tags = [t for t in cls.TAG_POOL["tool"] if tool in t.lower() or "AI编程工具" in t]
            if not tool_tags:
                tool_tags = item_rng.sample(cls.TAG_POOL["tool"], min(2, len(cls.TAG_POOL["tool"])))
            tags.extend(item_rng.sample(tool_tags, min(2, len(tool_tags))))

            theme_sample = item_rng.sample(cls.TAG_POOL["theme"], min(2, 4))
            tags.extend(theme_sample)

            if item_rng.random() < 0.5:
                tags.append(item_rng.choice(cls.TAG_POOL["project"]))
            if item_rng.random() < 0.6:
                tags.append(item_rng.choice(cls.TAG_POOL["style"]))

            # 添加关键词相关标签
            if len(cleaned_kw) <= 8 and item_rng.random() < 0.4:
                tags.append(f"#{cleaned_kw}")

            tags = list(dict.fromkeys(tags))[:item_rng.randint(3, 6)]

            # ---- 5. 互动数据（幂律分布） ----
            if i < count * 0.05:
                base_likes = item_rng.randint(80000, 250000)
            elif i < count * 0.2:
                base_likes = item_rng.randint(20000, 80000)
            elif i < count * 0.5:
                base_likes = item_rng.randint(3000, 20000)
            else:
                base_likes = item_rng.randint(200, 3000)

            collect_ratio = item_rng.uniform(0.4, 0.9) if category in ("tutorial", "tips") else item_rng.uniform(0.2, 0.6)
            comment_ratio = item_rng.uniform(0.08, 0.2) if category in ("review", "comparison") else item_rng.uniform(0.03, 0.12)

            likes = base_likes
            collects = int(likes * collect_ratio)
            comments = int(likes * comment_ratio)
            shares = int(likes * item_rng.uniform(0.02, 0.08))

            # ---- 6. 时间戳 ----
            rand_val = item_rng.random()
            if rand_val < 0.7:
                days_ago = item_rng.randint(0, 7)
            elif rand_val < 0.9:
                days_ago = item_rng.randint(8, 30)
            else:
                days_ago = item_rng.randint(31, 90)

            hours_ago = item_rng.randint(0, 23)
            publish_dt = now - timedelta(days=days_ago, hours=hours_ago)

            if days_ago <= 3:
                likes = int(likes * item_rng.uniform(1.0, 1.3))
                collects = int(collects * item_rng.uniform(1.0, 1.3))
                comments = int(comments * item_rng.uniform(1.0, 1.2))

            # ---- 7. 封面图 ----
            note_id = hashlib.md5(f"vibecoding_{cleaned_kw}_{i}_{time.time()}".encode()).hexdigest()

            if project_type == "mobile_app":
                cover_url = f"https://picsum.photos/seed/{note_id[:8]}/360/640"
            elif project_type == "landing_page":
                cover_url = f"https://picsum.photos/seed/{note_id[:8]}/800/450"
            else:
                cover_url = f"https://picsum.photos/seed/{note_id[:8]}/400/400"

            # ---- 8. 是否热门 ----
            velocity = likes / max(days_ago + 1, 1)
            is_trending = velocity > 2000

            # ---- 9. 组装结果 ----
            results.append({
                "note_id": note_id,
                "title": title,
                "description": description,
                "author_name": item_rng.choice(cls.AUTHORS),
                "author_id": f"author_{item_rng.randint(10000, 99999)}",
                "cover_url": cover_url,
                "video_url": "",
                "images": [
                    f"https://picsum.photos/seed/{note_id[:6]}a/400/400",
                    f"https://picsum.photos/seed/{note_id[:6]}b/400/400",
                    f"https://picsum.photos/seed/{note_id[:6]}c/400/400",
                ],
                "likes": likes,
                "collects": collects,
                "comments": comments,
                "shares": shares,
                "tags": tags,
                "keyword": keyword,
                "tool_name": tool,
                "project_type": project_type,
                "difficulty_level": difficulty,
                "content_category": category,
                "source_url": f"https://www.xiaohongshu.com/explore/{note_id[:16]}",
                "source": "mock",
                "is_trending": is_trending,
                "ai_confidence": item_rng.uniform(0.85, 0.99),
                "publish_time": publish_dt.isoformat(),
            })

        # 按热度排序
        results.sort(key=lambda x: (x["is_trending"], x["likes"]), reverse=True)
        return results


# ==================== 废弃的旧方法（保留兼容） ====================
# _generate_mock_data 已替换为 _generate_vibecoding_mock_data
# 保留原方法引用以便向后兼容
XiaohongshuCrawler._generate_mock_data = XiaohongshuCrawler._generate_vibecoding_mock_data
