"""Supabase database module for Facebook Work Notifier backend."""

from __future__ import annotations

import os
from typing import Optional, TypedDict
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Post type definition
class Post(TypedDict):
    post_id: str
    title: str
    text: str
    url: str
    timestamp: str
    group_name: str
    group_url: str

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
# Priority: SERVICE_KEY > SECRET_KEY > ANON_KEY (same as Tinder automation)
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY") or 
    os.getenv("SUPABASE_SECRET_KEY") or 
    os.getenv("SUPABASE_KEY")
)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_KEY) must be set in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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
        
        # Order by most recent first
        query = query.order("scraped_at", desc=True)
        
        # Add pagination
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        return result.data
    except Exception as e:
        print(f"Error getting posts: {e}")
        raise


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
        raise


def get_stats() -> dict:
    """Get database statistics."""
    try:
        # Total posts
        total_result = supabase.table("posts").select("id", count="exact").execute()
        total = total_result.count if total_result.count else 0
        
        # New posts (not notified)
        new_result = supabase.table("posts").select("id", count="exact").eq("notified", False).execute()
        new_posts = new_result.count if new_result.count else 0
        
        # Posts by group - get all posts and group in Python
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
        raise
