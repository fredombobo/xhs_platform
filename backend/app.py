"""VibeCoding 小红书热门内容爬取平台 - Flask 后端"""
import os
import sys
import json

# 确保能导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import func
from datetime import datetime

from crawler import XiaohongshuCrawler
from real_crawler import RealXiaohongshuCrawler
from models import init_db, Content, CategoryStat, Session
from config import (
    VIBECODING_TOOLS,
    PROJECT_TYPES,
    DIFFICULTY_LEVELS,
    CONTENT_CATEGORIES,
    SEED_ON_START,
    DEFAULT_KEYWORD,
)

# ---------- 初始化 ----------
app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)
crawler = XiaohongshuCrawler()
real_crawler = RealXiaohongshuCrawler(cookie=os.environ.get("XHS_COOKIE", ""), headless=False)


def _json_list(val):
    """将列表转为 JSON 字符串，供数据库存储"""
    if isinstance(val, list):
        return json.dumps(val, ensure_ascii=False)
    return val


def seed_if_empty():
    """如果数据库为空，自动生成 VibeCoding 示例数据"""
    session = Session()
    try:
        count = session.query(Content).count()
        if count == 0 and SEED_ON_START:
            print("=" * 50)
            print("  数据库为空，正在生成 VibeCoding 示例数据...")
            print("=" * 50)
            mock_data = crawler.search_notes(DEFAULT_KEYWORD, 120)
            saved = 0
            for item in mock_data:
                content = Content(
                    note_id=item["note_id"],
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    author_name=item.get("author_name", ""),
                    author_id=item.get("author_id", ""),
                    cover_url=item.get("cover_url", ""),
                    video_url=item.get("video_url", ""),
                    images=_json_list(item.get("images", [])),
                    likes=item.get("likes", 0),
                    collects=item.get("collects", 0),
                    comments=item.get("comments", 0),
                    shares=item.get("shares", 0),
                    tags=_json_list(item.get("tags", [])),
                    keyword=item.get("keyword", ""),
                    tool_name=item.get("tool_name"),
                    project_type=item.get("project_type"),
                    difficulty_level=item.get("difficulty_level"),
                    content_category=item.get("content_category"),
                    source_url=item.get("source_url", ""),
                    source=item.get("source", "mock"),
                    is_trending=item.get("is_trending", False),
                    ai_confidence=item.get("ai_confidence", 0.0),
                    publish_time=item.get("publish_time"),
                    crawled_at=datetime.now(),
                )
                session.add(content)
                saved += 1
            session.commit()
            _update_category_stats(session)
            print(f"  ✅ 已生成 {saved} 条 VibeCoding 示例数据")
            print("=" * 50)
    except Exception as e:
        session.rollback()
        print(f"  ⚠️  seed 数据失败: {e}")
    finally:
        session.close()


def _update_category_stats(session):
    """更新分类统计表"""
    # 清空旧统计
    session.query(CategoryStat).delete()

    stats = []

    # 按工具统计
    tool_rows = session.query(
        Content.tool_name, func.count(Content.id)
    ).filter(Content.tool_name.isnot(None)).group_by(Content.tool_name).all()
    for val, cnt in tool_rows:
        stats.append(CategoryStat(category_type="tool", category_value=val, count=cnt))

    # 按项目类型统计
    type_rows = session.query(
        Content.project_type, func.count(Content.id)
    ).filter(Content.project_type.isnot(None)).group_by(Content.project_type).all()
    for val, cnt in type_rows:
        stats.append(CategoryStat(category_type="project_type", category_value=val, count=cnt))

    # 按难度统计
    diff_rows = session.query(
        Content.difficulty_level, func.count(Content.id)
    ).filter(Content.difficulty_level.isnot(None)).group_by(Content.difficulty_level).all()
    for val, cnt in diff_rows:
        stats.append(CategoryStat(category_type="difficulty", category_value=val, count=cnt))

    # 按内容分类统计
    cat_rows = session.query(
        Content.content_category, func.count(Content.id)
    ).filter(Content.content_category.isnot(None)).group_by(Content.content_category).all()
    for val, cnt in cat_rows:
        stats.append(CategoryStat(category_type="content_category", category_value=val, count=cnt))

    session.add_all(stats)
    session.commit()


# ==================== 页面路由 ====================

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    target = os.path.join(app.static_folder, path)
    if os.path.isfile(target):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


# ==================== API 路由 ====================

@app.route("/api/contents", methods=["GET"])
def get_contents():
    """获取已爬取的内容列表（支持分页、筛选、排序）"""
    session = Session()
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        keyword = request.args.get("keyword", "")
        sort_by = request.args.get("sort_by", "likes")

        # === VibeCoding 新增筛选参数 ===
        tool = request.args.get("tool", "")
        project_type = request.args.get("project_type", "")
        difficulty = request.args.get("difficulty", "")
        category = request.args.get("category", "")
        trending = request.args.get("trending", "")

        query = session.query(Content)

        # 关键词筛选
        if keyword:
            query = query.filter(
                Content.keyword.contains(keyword)
                | Content.title.contains(keyword)
                | Content.description.contains(keyword)
            )

        # VibeCoding 筛选
        if tool:
            query = query.filter(Content.tool_name == tool)
        if project_type:
            query = query.filter(Content.project_type == project_type)
        if difficulty:
            query = query.filter(Content.difficulty_level == difficulty)
        if category:
            query = query.filter(Content.content_category == category)
        if trending and trending.lower() == "true":
            query = query.filter(Content.is_trending == True)

        # 排序
        sort_map = {
            "likes": Content.likes.desc(),
            "collects": Content.collects.desc(),
            "comments": Content.comments.desc(),
            "shares": Content.shares.desc(),
            "time": Content.publish_time.desc(),
            "crawled": Content.crawled_at.desc(),
        }
        order = sort_map.get(sort_by, Content.likes.desc())
        query = query.order_by(order)

        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "code": 200,
            "data": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": max(1, (total + per_page - 1) // per_page),
                "items": [c.to_dict() for c in items],
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500
    finally:
        session.close()


@app.route("/api/crawl", methods=["POST"])
def trigger_crawl():
    """触发爬取任务"""
    data = request.get_json(silent=True) or {}
    keyword = (data.get("keyword") or DEFAULT_KEYWORD).strip()
    count = min(data.get("count", 50), 200)  # 限制单次最多200条

    session = Session()
    try:
        # 执行爬取
        results = crawler.search_notes(keyword, count)

        saved = 0
        duplicates = 0

        for item in results:
            existing = session.query(Content).filter_by(note_id=item["note_id"]).first()
            if existing:
                # 更新互动数据
                existing.likes = max(existing.likes, item.get("likes", 0))
                existing.collects = max(existing.collects, item.get("collects", 0))
                existing.comments = max(existing.comments, item.get("comments", 0))
                existing.shares = max(existing.shares, item.get("shares", 0))
                duplicates += 1
            else:
                content = Content(
                    note_id=item["note_id"],
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    author_name=item.get("author_name", ""),
                    author_id=item.get("author_id", ""),
                    cover_url=item.get("cover_url", ""),
                    video_url=item.get("video_url", ""),
                    images=_json_list(item.get("images", [])),
                    likes=item.get("likes", 0),
                    collects=item.get("collects", 0),
                    comments=item.get("comments", 0),
                    shares=item.get("shares", 0),
                    tags=_json_list(item.get("tags", [])),
                    keyword=keyword,
                    tool_name=item.get("tool_name"),
                    project_type=item.get("project_type"),
                    difficulty_level=item.get("difficulty_level"),
                    content_category=item.get("content_category"),
                    source_url=item.get("source_url", ""),
                    source=item.get("source", "mock"),
                    is_trending=item.get("is_trending", False),
                    ai_confidence=item.get("ai_confidence", 0.0),
                    publish_time=item.get("publish_time"),
                    crawled_at=datetime.now(),
                )
                session.add(content)
                saved += 1

        session.commit()
        _update_category_stats(session)

        return jsonify({
            "code": 200,
            "message": f"爬取完成！新增 {saved} 条，更新 {duplicates} 条",
            "data": {
                "keyword": keyword,
                "saved": saved,
                "saved_count": saved,  # 兼容前端
                "duplicates": duplicates,
                "total_results": len(results),
            }
        })
    except Exception as e:
        session.rollback()
        return jsonify({"code": 500, "message": str(e)}), 500
    finally:
        session.close()


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """获取统计概览（含 VibeCoding 分类分布）"""
    session = Session()
    try:
        total = session.query(Content).count()

        agg = session.query(
            func.count(Content.id).label("total"),
            func.avg(Content.likes).label("avg_likes"),
            func.max(Content.likes).label("max_likes"),
            func.avg(Content.collects).label("avg_collects"),
            func.avg(Content.comments).label("avg_comments"),
        ).first()

        # 热门数量
        trending_count = session.query(Content).filter(Content.is_trending == True).count()

        # 关键词分布
        kw_rows = session.query(
            Content.keyword, func.count(Content.id)
        ).group_by(Content.keyword).order_by(
            func.count(Content.id).desc()
        ).limit(10).all()

        # 工具分布
        tool_dist = session.query(
            Content.tool_name, func.count(Content.id)
        ).filter(Content.tool_name.isnot(None)).group_by(
            Content.tool_name
        ).order_by(func.count(Content.id).desc()).all()

        # 难度分布
        diff_dist = session.query(
            Content.difficulty_level, func.count(Content.id)
        ).filter(Content.difficulty_level.isnot(None)).group_by(
            Content.difficulty_level
        ).order_by(func.count(Content.id).desc()).all()

        # 项目类型分布
        type_dist = session.query(
            Content.project_type, func.count(Content.id)
        ).filter(Content.project_type.isnot(None)).group_by(
            Content.project_type
        ).order_by(func.count(Content.id).desc()).all()

        return jsonify({
            "code": 200,
            "data": {
                "total_contents": total,
                "avg_likes": round(agg.avg_likes or 0, 1),
                "max_likes": agg.max_likes or 0,
                "avg_collects": round(agg.avg_collects or 0, 1),
                "avg_comments": round(agg.avg_comments or 0, 1),
                "total_trending": trending_count,
                "top_keywords": [{"keyword": k, "count": c} for k, c in kw_rows],
                "tool_distribution": [
                    {"tool": t, "label": VIBECODING_TOOLS.get(t, {}).get("label", t), "count": c}
                    for t, c in tool_dist
                ],
                "difficulty_distribution": [
                    {"level": d, "label": DIFFICULTY_LEVELS.get(d, {}).get("label", d), "count": c}
                    for d, c in diff_dist
                ],
                "type_distribution": [
                    {"type": t, "label": PROJECT_TYPES.get(t, {}).get("label", t), "count": c}
                    for t, c in type_dist
                ],
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500
    finally:
        session.close()


@app.route("/api/keywords", methods=["GET"])
def get_keywords():
    """获取已有的关键词列表（用于下拉选择）"""
    session = Session()
    try:
        rows = session.query(
            Content.keyword, func.count(Content.id).label("cnt")
        ).group_by(Content.keyword).order_by(func.count(Content.id).desc()).all()

        return jsonify({
            "code": 200,
            "data": [{"keyword": r[0], "count": r[1]} for r in rows],
        })
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500
    finally:
        session.close()


# ==================== VibeCoding 专用 API ====================

@app.route("/api/vibecoding/tools", methods=["GET"])
def get_tools():
    """获取所有 AI 编程工具及内容数量"""
    session = Session()
    try:
        rows = session.query(
            Content.tool_name, func.count(Content.id)
        ).filter(Content.tool_name.isnot(None)).group_by(
            Content.tool_name
        ).order_by(func.count(Content.id).desc()).all()

        tools_data = []
        for tool_code, cnt in rows:
            tool_info = VIBECODING_TOOLS.get(tool_code, {})
            tools_data.append({
                "tool": tool_code,
                "label": tool_info.get("label", tool_code),
                "icon": tool_info.get("icon", "💡"),
                "color": tool_info.get("color", "#64748b"),
                "count": cnt,
            })

        return jsonify({"code": 200, "data": tools_data})
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500
    finally:
        session.close()


@app.route("/api/vibecoding/categories", methods=["GET"])
def get_categories():
    """获取所有筛选分类选项及数量"""
    session = Session()
    try:
        # 工具统计
        tool_rows = session.query(
            Content.tool_name, func.count(Content.id)
        ).filter(Content.tool_name.isnot(None)).group_by(Content.tool_name).all()
        tools = []
        for t, c in tool_rows:
            info = VIBECODING_TOOLS.get(t, {})
            tools.append({
                "value": t, "label": info.get("label", t),
                "icon": info.get("icon", "💡"), "color": info.get("color", "#64748b"), "count": c,
            })

        # 项目类型统计
        type_rows = session.query(
            Content.project_type, func.count(Content.id)
        ).filter(Content.project_type.isnot(None)).group_by(Content.project_type).all()
        project_types = []
        for t, c in type_rows:
            info = PROJECT_TYPES.get(t, {})
            project_types.append({
                "value": t, "label": info.get("label", t), "icon": info.get("icon", "📦"), "count": c,
            })

        # 难度统计
        diff_rows = session.query(
            Content.difficulty_level, func.count(Content.id)
        ).filter(Content.difficulty_level.isnot(None)).group_by(Content.difficulty_level).all()
        difficulties = []
        for d, c in diff_rows:
            info = DIFFICULTY_LEVELS.get(d, {})
            difficulties.append({
                "value": d, "label": info.get("label", d), "color": info.get("color", "#64748b"), "count": c,
            })

        # 内容分类统计
        cat_rows = session.query(
            Content.content_category, func.count(Content.id)
        ).filter(Content.content_category.isnot(None)).group_by(Content.content_category).all()
        categories = []
        for cat, c in cat_rows:
            info = CONTENT_CATEGORIES.get(cat, {})
            categories.append({
                "value": cat, "label": info.get("label", cat), "icon": info.get("icon", "📄"), "count": c,
            })

        return jsonify({
            "code": 200,
            "data": {
                "tools": tools,
                "project_types": project_types,
                "difficulties": difficulties,
                "content_categories": categories,
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500
    finally:
        session.close()


@app.route("/api/vibecoding/trending", methods=["GET"])
def get_trending():
    """获取热门排行（按 velocity 排序）"""
    session = Session()
    try:
        limit = request.args.get("limit", 20, type=int)

        # 获取热门内容，按点赞数排序
        items = session.query(Content).filter(
            Content.is_trending == True
        ).order_by(Content.likes.desc()).limit(limit).all()

        # 如果热门内容不够，补充高点赞内容
        if len(items) < limit:
            extra = session.query(Content).filter(
                Content.is_trending == False
            ).order_by(Content.likes.desc()).limit(limit - len(items)).all()
            items.extend(extra)

        # 计算热度 velocity
        result = []
        for item in items:
            d = item.to_dict()
            # 简易热度分 = likes / (days_since_publish + 1)
            try:
                if item.publish_time:
                    pub_dt = datetime.fromisoformat(item.publish_time) if isinstance(item.publish_time, str) else item.publish_time
                    days_ago = max((datetime.now() - pub_dt).total_seconds() / 86400, 0.1)
                else:
                    days_ago = 7
            except Exception:
                days_ago = 7
            d["velocity"] = round(item.likes / days_ago)
            result.append(d)

        # 按 velocity 降序
        result.sort(key=lambda x: x["velocity"], reverse=True)

        return jsonify({
            "code": 200,
            "data": result[:limit],
        })
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500
    finally:
        session.close()


@app.route("/api/vibecoding/seed", methods=["POST"])
def seed_data():
    """手动触发生成示例数据"""
    data = request.get_json(silent=True) or {}
    keyword = data.get("keyword", DEFAULT_KEYWORD)
    count = min(data.get("count", 120), 300)

    session = Session()
    try:
        mock_data = crawler.search_notes(keyword, count)
        saved = 0
        for item in mock_data:
            content = Content(
                note_id=item["note_id"],
                title=item.get("title", ""),
                description=item.get("description", ""),
                author_name=item.get("author_name", ""),
                author_id=item.get("author_id", ""),
                cover_url=item.get("cover_url", ""),
                video_url=item.get("video_url", ""),
                images=_json_list(item.get("images", [])),
                likes=item.get("likes", 0),
                collects=item.get("collects", 0),
                comments=item.get("comments", 0),
                shares=item.get("shares", 0),
                tags=_json_list(item.get("tags", [])),
                keyword=item.get("keyword", keyword),
                tool_name=item.get("tool_name"),
                project_type=item.get("project_type"),
                difficulty_level=item.get("difficulty_level"),
                content_category=item.get("content_category"),
                source_url=item.get("source_url", ""),
                is_trending=item.get("is_trending", False),
                ai_confidence=item.get("ai_confidence", 0.0),
                publish_time=item.get("publish_time"),
                crawled_at=datetime.now(),
            )
            session.add(content)
            saved += 1
        session.commit()
        _update_category_stats(session)

        return jsonify({
            "code": 200,
            "message": f"已生成 {saved} 条 VibeCoding 示例数据",
            "data": {"saved": saved},
        })
    except Exception as e:
        session.rollback()
        return jsonify({"code": 500, "message": str(e)}), 500
    finally:
        session.close()


# ==================== 真实浏览器爬取 API ====================

@app.route("/api/crawl/real", methods=["POST"])
def trigger_real_crawl():
    """使用真实 Playwright 浏览器爬取小红书数据"""
    if not real_crawler.is_available:
        return jsonify({
            "code": 500,
            "message": "Playwright 未安装。请运行: pip install playwright && python -m playwright install chromium"
        }), 500

    data = request.get_json(silent=True) or {}
    keyword = (data.get("keyword") or DEFAULT_KEYWORD).strip()
    count = min(data.get("count", 30), 100)
    login_first = data.get("login_first", False)

    session = Session()
    try:
        # 使用真实浏览器爬取
        results = real_crawler.search_notes(keyword, count, login_first=login_first)

        if not results:
            return jsonify({
                "code": 200,
                "message": "未获取到数据。可能需要先登录小红书账号。",
                "data": {"saved": 0, "total_results": 0, "mode": "real", "need_login": True},
            })

        saved = 0
        duplicates = 0

        for item in results:
            existing = session.query(Content).filter_by(note_id=item["note_id"]).first()
            if existing:
                existing.likes = max(existing.likes, item.get("likes", 0))
                existing.collects = max(existing.collects, item.get("collects", 0))
                existing.comments = max(existing.comments, item.get("comments", 0))
                existing.shares = max(existing.shares, item.get("shares", 0))
                duplicates += 1
            else:
                content = Content(
                    note_id=item["note_id"],
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    author_name=item.get("author_name", ""),
                    author_id=item.get("author_id", ""),
                    cover_url=item.get("cover_url", ""),
                    video_url=item.get("video_url", ""),
                    images=_json_list(item.get("images", [])),
                    likes=item.get("likes", 0),
                    collects=item.get("collects", 0),
                    comments=item.get("comments", 0),
                    shares=item.get("shares", 0),
                    tags=_json_list(item.get("tags", [])),
                    keyword=keyword,
                    tool_name=item.get("tool_name"),
                    project_type=item.get("project_type"),
                    difficulty_level=item.get("difficulty_level"),
                    content_category=item.get("content_category"),
                    source_url=item.get("source_url", f"https://www.xiaohongshu.com/explore/{item['note_id']}"),
                    is_trending=item.get("is_trending", False),
                    ai_confidence=item.get("ai_confidence", 0.0),
                    publish_time=item.get("publish_time"),
                    crawled_at=datetime.now(),
                )
                session.add(content)
                saved += 1

        session.commit()
        _update_category_stats(session)

        return jsonify({
            "code": 200,
            "message": f"真实爬取完成！新增 {saved} 条，更新 {duplicates} 条",
            "data": {
                "keyword": keyword,
                "saved": saved,
                "saved_count": saved,
                "duplicates": duplicates,
                "total_results": len(results),
                "mode": "real",
            }
        })
    except Exception as e:
        session.rollback()
        return jsonify({"code": 500, "message": str(e)}), 500
    finally:
        session.close()


@app.route("/api/login-browser", methods=["POST"])
def open_login_browser():
    """打开可见浏览器窗口让用户扫码登录小红书"""
    if not real_crawler.is_available:
        return jsonify({
            "code": 500,
            "message": "Playwright 未安装"
        }), 500

    try:
        # 强制使用可见浏览器
        real_crawler.headless = False
        result = real_crawler.open_login_window()
        return jsonify({
            "code": 200 if result["success"] else 500,
            "message": result["message"],
            "data": result,
        })
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500


@app.route("/api/login-status", methods=["GET"])
def check_login_status():
    """检查小红书登录状态"""
    if not real_crawler.is_available:
        return jsonify({
            "code": 200,
            "data": {"logged_in": False, "reason": "Playwright not installed"}
        })

    try:
        status = real_crawler.check_login_status()
        return jsonify({"code": 200, "data": status})
    except Exception as e:
        return jsonify({
            "code": 200,
            "data": {"logged_in": False, "error": str(e)}
        })


@app.route("/api/set-cookie", methods=["POST"])
def set_cookie():
    """设置小红书 Cookie（用于 API 模式）"""
    global crawler, real_crawler
    data = request.get_json(silent=True) or {}
    cookie = data.get("cookie", "").strip()

    if cookie:
        os.environ["XHS_COOKIE"] = cookie
        crawler = XiaohongshuCrawler(cookie=cookie)
        real_crawler.cookie = cookie
        return jsonify({"code": 200, "message": "Cookie 已设置"})
    else:
        return jsonify({"code": 400, "message": "Cookie 不能为空"}), 400


@app.route("/api/crawler-mode", methods=["GET"])
def get_crawler_mode():
    """获取当前爬虫模式信息"""
    return jsonify({
        "code": 200,
        "data": {
            "has_cookie": bool(os.environ.get("XHS_COOKIE", "")),
            "playwright_available": real_crawler.is_available,
            "current_mode": "real_api" if os.environ.get("XHS_COOKIE", "") else "mock",
            "note": "设置 Cookie 后可使用真实 API；Playwright 模式请在「真实爬取」按钮中使用",
        }
    })


# ==================== 启动 ====================

if __name__ == "__main__":
    init_db()
    seed_if_empty()
    print("=" * 50)
    print("  ⚡ VibeCoding 灵感发现平台")
    print("  小红书热门 AI 编程项目爬取")
    print("  访问地址: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
