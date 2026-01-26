"""Vercel serverless function for posts API."""

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.app.db import get_posts, get_post_count


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests."""
        # Enable CORS
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
        
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
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            error_response = {"error": str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
