"""Vercel serverless function for posts API."""

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import os
from typing import Optional
from supabase import create_client, Client


def get_posts(
    limit: int = 100,
    offset: int = 0,
    group_url: Optional[str] = None,
    search: Optional[str] = None,
    only_new: bool = False
) -> list[dict]:
    """Retrieve posts from the database with optional filtering."""
    try:
        # Load environment variables at runtime
        supabase_url = os.getenv("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        supabase_key = (
            os.getenv("SUPABASE_SERVICE_KEY") or 
            os.getenv("SUPABASE_SECRET_KEY") or 
            os.getenv("SUPABASE_KEY") or
            os.environ.get("SUPABASE_SERVICE_KEY") or
            os.environ.get("SUPABASE_KEY")
        )
        
        if not supabase_url or not supabase_key:
            raise ValueError("Environment variables not available")
        
        supabase: Client = create_client(supabase_url, supabase_key)
        query = supabase.table("posts").select("*")
        
        if group_url:
            query = query.eq("group_url", group_url)
        
        if search:
            query = query.or_(f"title.ilike.%{search}%,text.ilike.%{search}%")
        
        if only_new:
            query = query.eq("notified", False)
        
        query = query.order("scraped_at", desc=True)
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
        # Load environment variables at runtime
        supabase_url = os.getenv("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        supabase_key = (
            os.getenv("SUPABASE_SERVICE_KEY") or 
            os.getenv("SUPABASE_SECRET_KEY") or 
            os.getenv("SUPABASE_KEY") or
            os.environ.get("SUPABASE_SERVICE_KEY") or
            os.environ.get("SUPABASE_KEY")
        )
        
        if not supabase_url or not supabase_key:
            raise ValueError("Environment variables not available")
        
        supabase: Client = create_client(supabase_url, supabase_key)
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


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests."""
        try:
            # Parse URL and query parameters
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            # Extract parameters with defaults
            limit = int(query_params.get('limit', ['100'])[0])
            offset = int(query_params.get('offset', ['0'])[0])
            group_url = query_params.get('group_url', [None])[0]
            search = query_params.get('search', [None])[0]
            only_new = query_params.get('only_new', ['false'])[0].lower() == 'true'
            
            # Validate limits
            limit = max(1, min(limit, 1000))
            offset = max(0, offset)
            
            # Get posts and count
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
            
            # Return response
            response = {
                "posts": posts,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(response).encode())
            
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
