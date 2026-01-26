"""Vercel serverless function for stats API."""

from http.server import BaseHTTPRequestHandler
import json
import os
from typing import Optional
from supabase import create_client, Client


def get_stats() -> dict:
    """Get database statistics."""
    try:
        # Load environment variables at runtime (inside the function)
        supabase_url = os.getenv("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        supabase_key = (
            os.getenv("SUPABASE_SERVICE_KEY") or 
            os.getenv("SUPABASE_SECRET_KEY") or 
            os.getenv("SUPABASE_KEY") or
            os.environ.get("SUPABASE_SERVICE_KEY") or
            os.environ.get("SUPABASE_KEY")
        )
        
        # Debug: Check if env vars are loaded
        if not supabase_url or not supabase_key:
            # List all available env vars for debugging
            env_vars = {k: v[:20] + "..." if len(v) > 20 else v for k, v in os.environ.items() if "SUPABASE" in k}
            raise ValueError(f"Environment variables missing: URL={supabase_url is not None}, KEY={supabase_key is not None}, Available: {env_vars}")
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Total posts
        total_result = supabase.table("posts").select("id", count="exact").execute()
        total = total_result.count if total_result.count else 0
        
        # New posts (not notified)
        new_result = supabase.table("posts").select("id", count="exact").eq("notified", False).execute()
        new_posts = new_result.count if new_result.count else 0
        
        # Posts by group
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


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests."""
        try:
            # Get stats
            stats = get_stats()
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(stats).encode())
            
        except Exception as e:
            # Send error response
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {"error": str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
