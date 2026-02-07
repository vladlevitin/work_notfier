"""Supabase database module for Facebook Work Notifier backend."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from typing import Optional, TypedDict
from supabase import create_client, Client
from dotenv import load_dotenv


def parse_facebook_timestamp(timestamp: str) -> datetime:
    """Parse Facebook timestamp strings into datetime objects."""
    now = datetime.now()
    
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    # Handle full format with day name: "Sunday 1 February 2026 at 14:08"
    match = re.match(r'^(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)\s+(\d+)\s+(\w+)\s+(\d{4})\s+at\s+(\d+):(\d+)$', timestamp, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        month_name = match.group(2)
        year = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))
        
        month = month_map.get(month_name)
        if month:
            try:
                return datetime(year, month, day, hour, minute)
            except ValueError:
                pass
    
    # Handle "Xm" format (X minutes ago)
    match = re.match(r'^(\d+)m$', timestamp)
    if match:
        minutes = int(match.group(1))
        return now - timedelta(minutes=minutes)
    
    # Handle "Xh" format (X hours ago)
    match = re.match(r'^(\d+)h$', timestamp)
    if match:
        hours = int(match.group(1))
        return now - timedelta(hours=hours)
    
    # Handle "Xd" format (X days ago)
    match = re.match(r'^(\d+)d$', timestamp)
    if match:
        days = int(match.group(1))
        return now - timedelta(days=days)
    
    # Handle "Yesterday at HH:MM" format
    match = re.match(r'^Yesterday\s+at\s+(\d+):(\d+)$', timestamp)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        yesterday = now - timedelta(days=1)
        return yesterday.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Handle "DD Month at HH:MM" format (e.g., "24 January at 08:42")
    match = re.match(r'^(\d+)\s+(\w+)\s+at\s+(\d+):(\d+)$', timestamp)
    if match:
        day = int(match.group(1))
        month_name = match.group(2)
        hour = int(match.group(3))
        minute = int(match.group(4))
        
        month = month_map.get(month_name)
        if month:
            year = now.year
            try:
                date = datetime(year, month, day, hour, minute)
                # If date is in the future, it's from last year
                if date > now:
                    date = datetime(year - 1, month, day, hour, minute)
                return date
            except ValueError:
                pass
    
    # Handle "DD Month YYYY at HH:MM" format (e.g., "5 May 2025 at 14:30")
    match = re.match(r'^(\d+)\s+(\w+)\s+(\d{4})\s+at\s+(\d+):(\d+)$', timestamp)
    if match:
        day = int(match.group(1))
        month_name = match.group(2)
        year = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))
        
        month = month_map.get(month_name)
        if month:
            try:
                return datetime(year, month, day, hour, minute)
            except ValueError:
                pass
    
    # Handle "DD Month YYYY" format (e.g., "5 May 2025")
    match = re.match(r'^(\d+)\s+(\w+)\s+(\d{4})$', timestamp)
    if match:
        day = int(match.group(1))
        month_name = match.group(2)
        year = int(match.group(3))
        
        month = month_map.get(month_name)
        if month:
            try:
                return datetime(year, month, day, 12, 0)
            except ValueError:
                pass
    
    # Handle "Recently" - treat as very recent
    if timestamp.lower() == 'recently':
        return now - timedelta(minutes=1)
    
    # Unknown formats - return very old date
    return datetime(1970, 1, 1)

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


def normalize_group_name(name: str) -> str:
    """Strip '(1) ', '(2) ', etc. prefixes from Facebook tab group names."""
    return re.sub(r'^\(\d+\)\s*', '', name)


def get_posts(
    limit: int = 100,
    offset: int = 0,
    group_url: Optional[str] = None,
    group_name: Optional[str] = None,
    search: Optional[str] = None,
    only_new: bool = False
) -> list[dict]:
    """
    Retrieve posts from the database with optional filtering.
    
    Args:
        limit: Maximum number of posts to return
        offset: Number of posts to skip (for pagination)
        group_url: Filter by specific Facebook group URL
        group_name: Filter by normalized group name
        search: Search term to filter posts (searches title and text)
        only_new: Only return posts that haven't been notified about
    
    Returns:
        List of post dictionaries sorted by Facebook timestamp (most recent first)
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
        
        # Fetch all matching posts (we'll sort in Python by parsed timestamp)
        result = query.execute()
        all_posts = result.data or []
        
        # Normalize group names in all posts
        for post in all_posts:
            post["group_name"] = normalize_group_name(post.get("group_name", "Unknown"))
        
        # Filter by normalized group name (after normalization)
        if group_name:
            all_posts = [p for p in all_posts if p.get("group_name") == group_name]
        
        # Sort by parsed Facebook timestamp (most recent first)
        all_posts.sort(
            key=lambda p: parse_facebook_timestamp(p.get('timestamp', '')),
            reverse=True
        )
        
        # Apply pagination after sorting
        paginated_posts = all_posts[offset:offset + limit]
        
        return paginated_posts
    except Exception as e:
        print(f"Error getting posts: {e}")
        raise


def get_post_count(
    group_url: Optional[str] = None,
    group_name: Optional[str] = None,
    search: Optional[str] = None,
    only_new: bool = False
) -> int:
    """Get total count of posts matching the filters."""
    try:
        # If filtering by normalized group_name, we need to count in Python
        if group_name:
            query = supabase.table("posts").select("group_name")
            if search:
                query = query.or_(f"title.ilike.%{search}%,text.ilike.%{search}%")
            if only_new:
                query = query.eq("notified", False)
            result = query.execute()
            return sum(1 for p in (result.data or []) if normalize_group_name(p.get("group_name", "")) == group_name)
        
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


def get_post_by_id(post_id: str) -> Optional[dict]:
    """
    Get a single post by its post_id.
    
    Args:
        post_id: The unique post identifier
    
    Returns:
        Post dictionary if found, None otherwise
    """
    try:
        result = supabase.table("posts").select("*").eq("post_id", post_id).execute()
        if result.data and len(result.data) > 0:
            post = result.data[0]
            post["group_name"] = normalize_group_name(post.get("group_name", "Unknown"))
            return post
        return None
    except Exception as e:
        print(f"Error getting post by id: {e}")
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
            group_name = normalize_group_name(post.get("group_name", "Unknown"))
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
