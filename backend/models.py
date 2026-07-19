"""数据库模型定义"""
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Content(Base):
    """VibeCoding 小红书笔记内容模型"""
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(String(64), unique=True, index=True, comment="笔记ID")
    title = Column(String(512), comment="标题")
    description = Column(Text, comment="描述/正文")
    author_name = Column(String(128), comment="作者昵称")
    author_id = Column(String(64), comment="作者ID")
    cover_url = Column(String(1024), comment="封面图URL")
    video_url = Column(String(1024), comment="视频URL")
    images = Column(Text, comment="图片列表(JSON)")
    likes = Column(Integer, default=0, comment="点赞数")
    collects = Column(Integer, default=0, comment="收藏数")
    comments = Column(Integer, default=0, comment="评论数")
    shares = Column(Integer, default=0, comment="分享数")
    tags = Column(Text, comment="标签列表(JSON)")
    keyword = Column(String(128), index=True, comment="搜索关键词")

    # === VibeCoding 分类字段 ===
    tool_name = Column(String(64), nullable=True, index=True, comment="AI编程工具")
    project_type = Column(String(64), nullable=True, index=True, comment="项目类型")
    difficulty_level = Column(String(32), nullable=True, comment="难度等级")
    content_category = Column(String(64), nullable=True, comment="内容分类")
    source_url = Column(String(1024), nullable=True, comment="原始链接")
    source = Column(String(16), default="mock", index=True, comment="数据来源: mock/real")
    is_trending = Column(Boolean, default=False, comment="是否热门")
    ai_confidence = Column(Float, default=0.0, comment="AI分类置信度")

    publish_time = Column(String(64), comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, comment="爬取时间")

    def to_dict(self):
        """转为字典供API返回"""
        def safe_json_parse(val):
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return []
            return val if isinstance(val, list) else []

        return {
            "id": self.id,
            "note_id": self.note_id,
            "title": self.title,
            "description": self.description,
            "author_name": self.author_name,
            "author_id": self.author_id,
            "cover_url": self.cover_url,
            "video_url": self.video_url,
            "images": safe_json_parse(self.images),
            "likes": self.likes,
            "collects": self.collects,
            "comments": self.comments,
            "shares": self.shares,
            "tags": safe_json_parse(self.tags),
            "keyword": self.keyword,
            # VibeCoding fields
            "tool_name": self.tool_name,
            "project_type": self.project_type,
            "difficulty_level": self.difficulty_level,
            "content_category": self.content_category,
            "source_url": self.source_url,
            "source": self.source or "mock",
            "is_trending": self.is_trending,
            "ai_confidence": self.ai_confidence,
            "publish_time": self.publish_time,
            "crawled_at": self.crawled_at.isoformat() if self.crawled_at else None,
        }

    def __repr__(self):
        return f"<Content {self.id}: {self.title[:40]}...>"


class CategoryStat(Base):
    """预计算的分类统计（避免每次请求都做 COUNT 查询）"""
    __tablename__ = "category_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_type = Column(String(64), index=True, comment="分类维度: tool/project_type/difficulty/content_category")
    category_value = Column(String(128), index=True, comment="分类值")
    count = Column(Integer, default=0, comment="内容数量")
    updated_at = Column(DateTime, default=datetime.now, comment="更新时间")

    def to_dict(self):
        return {
            "type": self.category_type,
            "value": self.category_value,
            "count": self.count,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<CategoryStat {self.category_type}:{self.category_value}={self.count}>"


def init_db():
    """初始化数据库表"""
    db_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(db_dir), "data")
    os.makedirs(data_dir, exist_ok=True)
    Base.metadata.create_all(engine)
    print("数据库初始化完成")
