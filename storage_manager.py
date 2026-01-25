"""Supabase Storage manager for Facebook Work Notifier.

Uploads scraped posts to Supabase Storage in timestamped folders,
similar to Tinder automation pattern.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

from scraper import Post

# Load environment variables
load_dotenv()

# Storage configuration
BUCKET_NAME = "work_notifier"
STORAGE_BASE_PATH = "listing_data"

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_timestamp_folder() -> str:
    """Get current timestamp folder name (format: YYYY-MM-DD_HH-MM-SS)."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def upload_posts_to_storage(posts: list[Post], group_name: str) -> tuple[str, int]:
    """
    Upload posts to Supabase Storage in timestamped folder.
    
    Args:
        posts: List of posts to upload
        group_name: Name of Facebook group (for folder organization)
    
    Returns:
        Tuple of (folder_path, upload_count)
    """
    if not posts:
        return ("", 0)
    
    # Create timestamp folder
    timestamp = get_timestamp_folder()
    
    # Sanitize group name for folder path
    safe_group_name = group_name.replace(" ", "_").replace("/", "_")[:50]
    
    # Storage path: listing_data/GroupName/YYYY-MM-DD_HH-MM-SS/posts.json
    folder_path = f"{STORAGE_BASE_PATH}/{safe_group_name}/{timestamp}"
    file_path = f"{folder_path}/posts.json"
    
    # Convert posts to JSON
    posts_data = {
        "scrape_timestamp": timestamp,
        "group_name": group_name,
        "post_count": len(posts),
        "posts": posts
    }
    
    json_bytes = json.dumps(posts_data, indent=2, ensure_ascii=False).encode('utf-8')
    
    try:
        # Upload to Supabase Storage
        print(f"📤 Uploading {len(posts)} posts to Storage: {file_path}")
        supabase.storage.from_(BUCKET_NAME).upload(
            file_path,
            json_bytes,
            {"content-type": "application/json", "upsert": "true"}
        )
        
        print(f"✅ Successfully uploaded to Storage: {folder_path}")
        return (folder_path, len(posts))
        
    except Exception as e:
        print(f"❌ Failed to upload to Storage: {e}")
        return ("", 0)


def upload_all_groups_to_storage(groups_posts: dict[str, list[Post]]) -> dict:
    """
    Upload posts from multiple groups to Storage.
    
    Args:
        groups_posts: Dictionary mapping group_name to list of posts
    
    Returns:
        Dictionary with upload statistics
    """
    stats = {
        "total_posts": 0,
        "total_groups": len(groups_posts),
        "uploaded_folders": [],
        "timestamp": get_timestamp_folder()
    }
    
    for group_name, posts in groups_posts.items():
        if posts:
            folder_path, count = upload_posts_to_storage(posts, group_name)
            if folder_path:
                stats["total_posts"] += count
                stats["uploaded_folders"].append({
                    "group": group_name,
                    "folder": folder_path,
                    "count": count
                })
    
    return stats


def list_storage_folders(group_name: Optional[str] = None) -> list[str]:
    """
    List all timestamped folders in Storage.
    
    Args:
        group_name: Optional filter by group name
    
    Returns:
        List of folder paths
    """
    try:
        if group_name:
            safe_group_name = group_name.replace(" ", "_").replace("/", "_")[:50]
            path = f"{STORAGE_BASE_PATH}/{safe_group_name}"
        else:
            path = STORAGE_BASE_PATH
        
        items = supabase.storage.from_(BUCKET_NAME).list(path)
        folders = [item["name"] for item in items if item.get("id")]
        return folders
        
    except Exception as e:
        print(f"❌ Failed to list Storage folders: {e}")
        return []


def download_posts_from_storage(folder_path: str) -> Optional[dict]:
    """
    Download posts from a specific Storage folder.
    
    Args:
        folder_path: Path to folder in Storage
    
    Returns:
        Dictionary with posts data, or None if failed
    """
    try:
        file_path = f"{folder_path}/posts.json"
        data = supabase.storage.from_(BUCKET_NAME).download(file_path)
        return json.loads(data)
        
    except Exception as e:
        print(f"❌ Failed to download from Storage: {e}")
        return None


if __name__ == "__main__":
    # Test connection
    print(f"Connecting to Supabase Storage...")
    print(f"   URL: {SUPABASE_URL}")
    print(f"   Bucket: {BUCKET_NAME}")
    
    try:
        # List root folders
        folders = list_storage_folders()
        print(f"\nSuccessfully connected to Storage!")
        print(f"Found {len(folders)} group folders")
        for folder in folders:
            print(f"   - {folder}")
            
    except Exception as e:
        print(f"\nFailed to connect to Storage: {e}")
