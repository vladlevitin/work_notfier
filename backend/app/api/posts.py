"""API endpoints for Facebook posts."""

from fastapi import APIRouter, Query, HTTPException, Path
from typing import Optional

from app.db import get_posts, get_post_count, get_stats, get_post_by_id

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
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts/{post_id}")
async def get_single_post(post_id: str = Path(..., description="The unique post identifier")):
    """
    Get a single post by its ID.
    """
    try:
        post = get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        return {"post": post}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_statistics():
    """Get database statistics."""
    try:
        return get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
