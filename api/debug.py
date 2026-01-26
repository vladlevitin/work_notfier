"""Debug endpoint to check environment variables."""

from http.server import BaseHTTPRequestHandler
import json
import os


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Get all environment variables that contain "SUPABASE" or "VERCEL"
        env_vars = {
            k: v[:50] + "..." if len(v) > 50 else v 
            for k, v in os.environ.items() 
            if "SUPABASE" in k or "VERCEL" in k or k in ["PATH", "PYTHON_VERSION", "AWS_REGION"]
        }
        
        response = {
            "all_env_count": len(os.environ),
            "supabase_vars": env_vars,
            "supabase_url_present": "SUPABASE_URL" in os.environ,
            "supabase_key_present": "SUPABASE_KEY" in os.environ,
            "supabase_service_key_present": "SUPABASE_SERVICE_KEY" in os.environ,
        }
        
        self.wfile.write(json.dumps(response, indent=2).encode())
