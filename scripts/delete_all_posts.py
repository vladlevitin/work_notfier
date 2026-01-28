"""
Script to delete all posts from the Supabase database.
Run this to clear the database before re-scraping.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def delete_all_posts():
    """Delete all posts from the database."""
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("ERROR: Missing Supabase credentials in .env file")
        print("Required: SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_KEY)")
        return False
    
    # Create Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("="*60)
    print("DELETE ALL POSTS FROM DATABASE")
    print("="*60)
    
    # Get current count
    count_result = supabase.table("posts").select("*", count="exact", head=True).execute()
    current_count = count_result.count if count_result.count else 0
    
    print(f"\nCurrent posts in database: {current_count}")
    
    if current_count == 0:
        print("\nNo posts to delete. Database is already empty.")
        return True
    
    # Confirm deletion
    print(f"\nWARNING: This will DELETE ALL {current_count} posts!")
    confirm = input("Type 'DELETE' to confirm: ")
    
    if confirm != "DELETE":
        print("\nDeletion cancelled.")
        return False
    
    # Delete all posts
    print("\nDeleting all posts...")
    try:
        # Delete in batches to avoid timeout
        batch_size = 1000
        total_deleted = 0
        
        while True:
            # Get batch of post IDs
            result = supabase.table("posts").select("post_id").limit(batch_size).execute()
            
            if not result.data or len(result.data) == 0:
                break
            
            # Delete batch
            post_ids = [post["post_id"] for post in result.data]
            supabase.table("posts").delete().in_("post_id", post_ids).execute()
            
            total_deleted += len(post_ids)
            print(f"  Deleted {total_deleted} posts...")
        
        print(f"\n[OK] Successfully deleted {total_deleted} posts!")
        
        # Verify deletion
        verify_result = supabase.table("posts").select("*", count="exact", head=True).execute()
        remaining = verify_result.count if verify_result.count else 0
        
        print(f"[OK] Remaining posts: {remaining}")
        
        if remaining == 0:
            print("\n[OK] Database is now empty!")
            print("\nYou can now run:")
            print("  python main.py       (single scrape)")
            print("  python monitor.py    (continuous monitoring)")
            return True
        else:
            print(f"\n[WARNING] {remaining} posts remaining. Try running the script again.")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Failed to delete posts: {e}")
        return False

if __name__ == "__main__":
    delete_all_posts()
