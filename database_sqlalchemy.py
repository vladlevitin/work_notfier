"""Database connection using SQLAlchemy for Supabase PostgreSQL."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, TIMESTAMP, func, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

from scraper import Post

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set in .env file")

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


# Define Post model
class PostModel(Base):
    """SQLAlchemy model for Facebook posts."""
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    timestamp = Column(Text, nullable=False)
    group_name = Column(Text, nullable=False)
    group_url = Column(Text, nullable=False, index=True)
    scraped_at = Column(TIMESTAMP, server_default=func.now())
    notified = Column(Boolean, default=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


# Create indexes
Index('idx_posts_scraped_at', PostModel.scraped_at.desc())


def init_database():
    """Initialize database schema."""
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database schema initialized")


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, let caller close


def post_exists(post_id: str) -> bool:
    """Check if a post already exists in the database."""
    if post_id == "unknown":
        return False
    
    db = SessionLocal()
    try:
        result = db.query(PostModel).filter(PostModel.post_id == post_id).first()
        return result is not None
    finally:
        db.close()


def save_post(post: Post) -> bool:
    """
    Save a post to the database.
    Returns True if the post was newly added, False if it already existed.
    """
    if post_exists(post["post_id"]):
        return False
    
    db = SessionLocal()
    try:
        db_post = PostModel(
            post_id=post["post_id"],
            title=post["title"],
            text=post["text"],
            url=post["url"],
            timestamp=post["timestamp"],
            group_name=post["group_name"],
            group_url=post["group_url"],
            notified=False
        )
        db.add(db_post)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error saving post: {e}")
        return False
    finally:
        db.close()


def save_posts(posts: list[Post]) -> tuple[int, int]:
    """
    Save multiple posts to the database.
    Returns (new_count, skipped_count).
    """
    new_count = 0
    skipped_count = 0
    
    for post in posts:
        if save_post(post):
            new_count += 1
        else:
            skipped_count += 1
    
    return new_count, skipped_count


def get_posts(
    limit: int = 100,
    offset: int = 0,
    group_url: Optional[str] = None,
    search: Optional[str] = None,
    only_new: bool = False
) -> list[dict]:
    """
    Retrieve posts from the database with optional filtering.
    
    Args:
        limit: Maximum number of posts to return
        offset: Number of posts to skip (for pagination)
        group_url: Filter by specific Facebook group
        search: Search term to filter posts (searches title and text)
        only_new: Only return posts that haven't been notified about
    
    Returns:
        List of post dictionaries
    """
    db = SessionLocal()
    try:
        query = db.query(PostModel)
        
        if group_url:
            query = query.filter(PostModel.group_url == group_url)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (PostModel.title.ilike(search_filter)) | (PostModel.text.ilike(search_filter))
            )
        
        if only_new:
            query = query.filter(PostModel.notified == False)
        
        # Order by most recent first
        query = query.order_by(PostModel.scraped_at.desc())
        
        # Add pagination
        query = query.limit(limit).offset(offset)
        
        results = query.all()
        
        # Convert to dictionaries
        return [{
            "id": r.id,
            "post_id": r.post_id,
            "title": r.title,
            "text": r.text,
            "url": r.url,
            "timestamp": r.timestamp,
            "group_name": r.group_name,
            "group_url": r.group_url,
            "scraped_at": r.scraped_at.isoformat() if r.scraped_at else None,
            "notified": r.notified,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        } for r in results]
    finally:
        db.close()


def get_post_count(
    group_url: Optional[str] = None,
    search: Optional[str] = None,
    only_new: bool = False
) -> int:
    """Get total count of posts matching the filters."""
    db = SessionLocal()
    try:
        query = db.query(PostModel)
        
        if group_url:
            query = query.filter(PostModel.group_url == group_url)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (PostModel.title.ilike(search_filter)) | (PostModel.text.ilike(search_filter))
            )
        
        if only_new:
            query = query.filter(PostModel.notified == False)
        
        return query.count()
    finally:
        db.close()


def mark_as_notified(post_ids: list[str]) -> None:
    """Mark posts as notified (email has been sent)."""
    if not post_ids:
        return
    
    db = SessionLocal()
    try:
        db.query(PostModel).filter(PostModel.post_id.in_(post_ids)).update(
            {"notified": True},
            synchronize_session=False
        )
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error marking posts as notified: {e}")
    finally:
        db.close()


def get_stats() -> dict:
    """Get database statistics."""
    db = SessionLocal()
    try:
        # Total posts
        total = db.query(PostModel).count()
        
        # New posts (not notified)
        new_posts = db.query(PostModel).filter(PostModel.notified == False).count()
        
        # Posts by group
        from sqlalchemy import func as sqlfunc
        group_counts = db.query(
            PostModel.group_name,
            sqlfunc.count(PostModel.id).label('count')
        ).group_by(PostModel.group_name).all()
        
        by_group = [{"group": group, "count": count} for group, count in group_counts]
        by_group.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "total": total,
            "new": new_posts,
            "by_group": by_group
        }
    finally:
        db.close()


if __name__ == "__main__":
    # Test connection
    print(f"Connecting to database...")
    try:
        init_database()
        db = SessionLocal()
        count = db.query(PostModel).count()
        db.close()
        print(f"✅ Successfully connected to database!")
        print(f"Total posts in database: {count}")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
