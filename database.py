"""Database module for storing and retrieving Facebook posts."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from scraper import Post


# Database file path
DB_PATH = Path(__file__).parent / "facebook_posts.db"


def init_database() -> None:
    """Initialize the database schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create posts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            post_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            url TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            group_name TEXT NOT NULL,
            group_url TEXT NOT NULL,
            scraped_at TEXT NOT NULL,
            notified BOOLEAN DEFAULT 0
        )
    """)
    
    # Create index on group_url for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_group_url ON posts(group_url)
    """)
    
    # Create index on scraped_at for sorting by most recent
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_scraped_at ON posts(scraped_at DESC)
    """)
    
    # Create index on notified for filtering
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_notified ON posts(notified)
    """)
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {DB_PATH}")


def post_exists(post_id: str) -> bool:
    """Check if a post already exists in the database."""
    if post_id == "unknown":
        return False  # Don't skip posts with unknown IDs
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM posts WHERE post_id = ?", (post_id,))
    exists = cursor.fetchone() is not None
    
    conn.close()
    return exists


def save_post(post: Post) -> bool:
    """
    Save a post to the database.
    Returns True if the post was newly added, False if it already existed.
    """
    if post_exists(post["post_id"]):
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    try:
        cursor.execute("""
            INSERT INTO posts (post_id, title, text, url, timestamp, group_name, group_url, scraped_at, notified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            post["post_id"],
            post["title"],
            post["text"],
            post["url"],
            post["timestamp"],
            post["group_name"],
            post["group_url"],
            now
        ))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Post already exists (race condition)
        conn.close()
        return False


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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    cursor = conn.cursor()
    
    # Build query
    query = "SELECT * FROM posts WHERE 1=1"
    params: list = []
    
    if group_url:
        query += " AND group_url = ?"
        params.append(group_url)
    
    if search:
        query += " AND (title LIKE ? OR text LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])
    
    if only_new:
        query += " AND notified = 0"
    
    # Order by most recent first
    query += " ORDER BY scraped_at DESC"
    
    # Add pagination
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    conn.close()
    
    # Convert to list of dictionaries
    return [dict(row) for row in rows]


def get_post_count(
    group_url: Optional[str] = None,
    search: Optional[str] = None,
    only_new: bool = False
) -> int:
    """Get total count of posts matching the filters."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT COUNT(*) FROM posts WHERE 1=1"
    params: list = []
    
    if group_url:
        query += " AND group_url = ?"
        params.append(group_url)
    
    if search:
        query += " AND (title LIKE ? OR text LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])
    
    if only_new:
        query += " AND notified = 0"
    
    cursor.execute(query, params)
    count = cursor.fetchone()[0]
    
    conn.close()
    return count


def mark_as_notified(post_ids: list[str]) -> None:
    """Mark posts as notified (email has been sent)."""
    if not post_ids:
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    placeholders = ",".join("?" * len(post_ids))
    cursor.execute(f"""
        UPDATE posts
        SET notified = 1
        WHERE post_id IN ({placeholders})
    """, post_ids)
    
    conn.commit()
    conn.close()


def get_stats() -> dict:
    """Get database statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total posts
    cursor.execute("SELECT COUNT(*) FROM posts")
    total = cursor.fetchone()[0]
    
    # Posts by group
    cursor.execute("""
        SELECT group_name, COUNT(*) as count
        FROM posts
        GROUP BY group_name
        ORDER BY count DESC
    """)
    by_group = [{"group": row[0], "count": row[1]} for row in cursor.fetchall()]
    
    # New posts (not notified)
    cursor.execute("SELECT COUNT(*) FROM posts WHERE notified = 0")
    new_posts = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total": total,
        "new": new_posts,
        "by_group": by_group
    }


if __name__ == "__main__":
    # Initialize database when run directly
    init_database()
