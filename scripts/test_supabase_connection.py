"""
Quick test to verify Supabase connection and data retrieval
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Get credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

print("=" * 60)
print("TESTING SUPABASE CONNECTION")
print("=" * 60)
print(f"\nSupabase URL: {SUPABASE_URL}")
print(f"Using Service Key: {SUPABASE_KEY[:20]}..." if SUPABASE_KEY else "No key found")

try:
    # Initialize Supabase client
    print("\n[1] Initializing Supabase client...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("[OK] Client created successfully")
    
    # Test 1: Count total posts
    print("\n[2] Fetching post count...")
    response = supabase.table("posts").select("*", count="exact").execute()
    total_count = response.count
    print(f"[OK] Total posts in database: {total_count}")
    
    # Test 2: Fetch first 5 posts
    print("\n[3] Fetching first 5 posts...")
    response = supabase.table("posts").select("*").limit(5).execute()
    posts = response.data
    print(f"[OK] Retrieved {len(posts)} posts")
    
    # Display post details
    if posts:
        print("\n[4] Sample post data:")
        for i, post in enumerate(posts, 1):
            print(f"\n  Post {i}:")
            print(f"    ID: {post.get('post_id', 'N/A')}")
            print(f"    Title: {post.get('title', 'N/A')[:50]}...")
            print(f"    Group: {post.get('group_name', 'N/A')}")
            print(f"    Timestamp: {post.get('timestamp', 'N/A')}")
            print(f"    Notified: {post.get('notified', False)}")
    
    # Test 3: Count new posts (not notified)
    print("\n[5] Counting new posts (not notified)...")
    response = supabase.table("posts").select("*", count="exact").eq("notified", False).execute()
    new_count = response.count
    print(f"[OK] New posts (not notified): {new_count}")
    
    # Test 4: Get stats like the API endpoint
    print("\n[6] Getting stats (like /api/stats endpoint)...")
    stats = {
        "total": total_count,
        "new": new_count,
        "notified": total_count - new_count
    }
    print(f"[OK] Stats: {stats}")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL TESTS PASSED - SUPABASE CONNECTION WORKS!")
    print("=" * 60)
    print("\nConclusion: Supabase connection is working perfectly.")
    print("The issue must be with the Render backend deployment.")
    print("\nNext steps:")
    print("1. Check Render environment variables are set")
    print("2. Check Render logs for errors")
    print("3. Verify backend is deployed from correct directory")
    
except Exception as e:
    print("\n" + "=" * 60)
    print("[ERROR] SUPABASE CONNECTION FAILED")
    print("=" * 60)
    print(f"\nError type: {type(e).__name__}")
    print(f"Error message: {str(e)}")
    print("\nPossible causes:")
    print("1. Supabase project is paused")
    print("2. API key is incorrect")
    print("3. Table 'posts' doesn't exist")
    print("4. Network/firewall issue")
