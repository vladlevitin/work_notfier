"""Database module - Supabase database operations."""

from .supabase_db import (
    save_post,
    save_posts,
    get_posts,
    get_post_count,
    post_exists,
    is_duplicate_post,
    find_duplicate_by_text,
    get_existing_post,
    mark_as_notified,
    get_stats,
    was_auto_message_sent,
    mark_auto_message_sent,
)

__all__ = [
    'save_post',
    'save_posts',
    'get_posts',
    'get_post_count',
    'post_exists',
    'is_duplicate_post',
    'find_duplicate_by_text',
    'get_existing_post',
    'mark_as_notified',
    'get_stats',
    'was_auto_message_sent',
    'mark_auto_message_sent',
]
