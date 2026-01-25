"""API endpoints for Facebook posts."""

from fastapi import APIRouter, Query
from typing import Optional
import sys
from pathlib import Path

# Add parent directory to path to import supabase_db module
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from supabase_db import get_posts, get_post_count, get_stats

router = APIRouter()


@router.get("/posts")
async def list_posts(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    group_url: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    only_new: bool = Query(default=False)
):
    """
    Get posts with optional filtering.
    
    Query params:
        - limit: Max posts to return (1-1000)
        - offset: Number of posts to skip
        - group_url: Filter by specific Facebook group
        - search: Search term for title/text
        - only_new: Only return posts not yet notified
    """
    posts = get_posts(
        limit=limit,
        offset=offset,
        group_url=group_url,
        search=search,
        only_new=only_new
    )
    
    total = get_post_count(
        group_url=group_url,
        search=search,
        only_new=only_new
    )
    
    return {
        "posts": posts,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/stats")
async def get_statistics():
    """Get database statistics."""
    return get_stats()
