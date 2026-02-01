"""Supabase database module for Facebook Work Notifier."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Dict
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import TypedDict

# Type definition for Post
class Post(TypedDict):
    post_id: str
    title: str
    text: str
    url: str
    timestamp: str
    group_name: str
    group_url: str

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
# Priority: SERVICE_KEY > SECRET_KEY > ANON_KEY (same as Tinder automation)
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY") or 
    os.getenv("SUPABASE_SECRET_KEY") or 
    os.getenv("SUPABASE_KEY")
)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_KEY) must be set in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_existing_post(post_id: str) -> Optional[Dict]:
    """
    Get existing post data from the database.
    Returns post data if exists, None otherwise.
    """
    if post_id == "unknown":
        return None
    
    try:
        result = supabase.table("posts").select("*").eq("post_id", post_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error checking if post exists: {e}")
        return None


def post_exists(post_id: str) -> bool:
    """Check if a post already exists in the database."""
    return get_existing_post(post_id) is not None


def save_post(post: Post, use_ai: bool = False) -> bool:
    """
    Save a post to the database.
    
    Args:
        post: Post data from scraper
        use_ai: Whether to use AI to extract category/location (default: False)
    
    Returns:
        True if the post was newly added, False if it already existed.
    """
    # Check if post already exists
    existing = get_existing_post(post["post_id"])
    
    if existing:
        return False  # Post already existed
    
    try:
        # Parse the Facebook timestamp to get actual posted time
        posted_at = None
        try:
            from src.scraper.timestamp_parser import parse_facebook_timestamp
            parsed_time = parse_facebook_timestamp(post["timestamp"])
            if parsed_time:
                posted_at = parsed_time.isoformat()
        except Exception as e:
            print(f"  [WARN] Could not parse timestamp: {e}")
        
        # Get AI-extracted category
        category = "General"
        try:
            from src.ai.ai_processor import process_post_with_ai
            ai_result = process_post_with_ai(post["title"], post["text"], post["post_id"])
            category = ai_result.get("category", "General")
        except Exception as e:
            print(f"  [WARN] AI category extraction failed: {e}")
        
        # Build insert data with basic columns
        insert_data = {
            "post_id": post["post_id"],
            "title": post["title"],
            "text": post["text"],
            "url": post["url"],
            "timestamp": post["timestamp"],
            "group_name": post["group_name"],
            "group_url": post["group_url"],
            "category": category,
            "notified": False
        }
        
        # Add posted_at if we successfully parsed the timestamp
        if posted_at:
            insert_data["posted_at"] = posted_at
        
        supabase.table("posts").insert(insert_data).execute()
        
        if posted_at:
            print(f"  [SAVED] {post['title'][:40]}... (posted: {posted_at[:16]})")
        else:
            print(f"  [SAVED] {post['title'][:50]}...")
        
        return True
    except Exception as e:
        error_str = str(e)
        # If category or posted_at column doesn't exist, try without them
        if "category" in error_str or "posted_at" in error_str:
            try:
                insert_data_basic = {
                    "post_id": post["post_id"],
                    "title": post["title"],
                    "text": post["text"],
                    "url": post["url"],
                    "timestamp": post["timestamp"],
                    "group_name": post["group_name"],
                    "group_url": post["group_url"],
                    "notified": False
                }
                supabase.table("posts").insert(insert_data_basic).execute()
                print(f"  [SAVED] {post['title'][:50]}... (without category)")
                return True
            except Exception as e2:
                print(f"  [ERROR] Saving post: {e2}")
                return False
        else:
            print(f"  [ERROR] Saving post: {e}")
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
    try:
        query = supabase.table("posts").select("*")
        
        if group_url:
            query = query.eq("group_url", group_url)
        
        if search:
            # Use ilike for case-insensitive search
            query = query.or_(f"title.ilike.%{search}%,text.ilike.%{search}%")
        
        if only_new:
            query = query.eq("notified", False)
        
        # Order by most recent first (scraped_at, then by id for stable ordering)
        query = query.order("scraped_at", desc=True).order("id", desc=True)
        
        # Add pagination
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        return result.data
    except Exception as e:
        print(f"Error getting posts: {e}")
        return []


def get_post_count(
    group_url: Optional[str] = None,
    search: Optional[str] = None,
    only_new: bool = False
) -> int:
    """Get total count of posts matching the filters."""
    try:
        query = supabase.table("posts").select("id", count="exact")
        
        if group_url:
            query = query.eq("group_url", group_url)
        
        if search:
            query = query.or_(f"title.ilike.%{search}%,text.ilike.%{search}%")
        
        if only_new:
            query = query.eq("notified", False)
        
        result = query.execute()
        return result.count if result.count else 0
    except Exception as e:
        print(f"Error getting post count: {e}")
        return 0


def mark_as_notified(post_ids: list[str]) -> None:
    """Mark posts as notified (email has been sent)."""
    if not post_ids:
        return
    
    try:
        supabase.table("posts").update({"notified": True}).in_("post_id", post_ids).execute()
    except Exception as e:
        print(f"Error marking posts as notified: {e}")


def get_stats() -> dict:
    """Get database statistics."""
    try:
        # Total posts
        total_result = supabase.table("posts").select("id", count="exact").execute()
        total = total_result.count if total_result.count else 0
        
        # New posts (not notified)
        new_result = supabase.table("posts").select("id", count="exact").eq("notified", False).execute()
        new_posts = new_result.count if new_result.count else 0
        
        # Posts by group - use RPC or raw SQL for grouping
        # For now, get all posts and group in Python (not efficient for large datasets)
        all_posts = supabase.table("posts").select("group_name").execute()
        
        group_counts = {}
        for post in all_posts.data:
            group_name = post.get("group_name", "Unknown")
            group_counts[group_name] = group_counts.get(group_name, 0) + 1
        
        by_group = [{"group": group, "count": count} for group, count in group_counts.items()]
        by_group.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "total": total,
            "new": new_posts,
            "by_group": by_group
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {"total": 0, "new": 0, "by_group": []}


if __name__ == "__main__":
    # Test connection
    print(f"Connecting to Supabase at {SUPABASE_URL}")
    try:
        result = supabase.table("posts").select("id", count="exact").limit(1).execute()
        print(f"[OK] Successfully connected to Supabase!")
        print(f"Total posts in database: {result.count if result.count else 0}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Supabase: {e}")
