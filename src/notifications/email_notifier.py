"""Email notification module for sending Facebook post alerts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

import requests
from dotenv import load_dotenv
from msal import ConfidentialClientApplication


class Post(TypedDict):
    """Represents a Facebook post."""
    post_id: str
    title: str
    text: str
    url: str
    timestamp: str
    group_name: str
    group_url: str


def load_env_config() -> dict[str, str]:
    """Load email configuration from .env file in project root."""
    # Try to find .env in project root (3 levels up from this file)
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # .env should already be loaded by main.py, just proceed
        pass

    config = {
        "tenant_id": os.getenv("GRAPH_TENANT_ID", os.getenv("TENANT_ID", "")).strip(),
        "client_id": os.getenv("GRAPH_CLIENT_ID", os.getenv("CLIENT_ID", "")).strip(),
        "client_secret": os.getenv("GRAPH_CLIENT_SECRET", os.getenv("CLIENT_SECRET", "")).strip(),
        "sender": os.getenv("GRAPH_SENDER", os.getenv("SENDER_EMAIL", "")).strip(),
        "recipient": os.getenv("RECIPIENT_EMAIL", "levitinvlad@hotmail.com").strip(),
    }

    missing = [k for k, v in config.items() if not v and k != "recipient"]
    if missing:
        print(f"[WARN] Email notification skipped - missing env vars: {', '.join(missing)}")
        print("       Set GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, GRAPH_SENDER in .env")
        return {}

    return config


def get_graph_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Get Microsoft Graph access token using application credentials."""
    app = ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
    )
    token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in token:
        raise SystemExit(f"Failed to get token: {token.get('error_description', 'Unknown error')}")
    return token["access_token"]


def get_category_emoji(category: str) -> str:
    """Get the emoji for a category — matches the dashboard icons."""
    emoji_map = {
        "Electrical": "⚡",
        "Plumbing": "🔧",
        "Transport / Moving": "🚚",
        "Manual Labor": "🏗️",
        "Painting / Renovation": "🎨",
        "Cleaning / Garden": "🧹",
        "Assembly / Furniture": "🪑",
        "Car Mechanic": "🔩",
        "Handyman / Misc": "🔨",
        "IT / Tech": "💻",
        "Other": "📦",
    }
    return emoji_map.get(category, "📦")


def send_email_notification(posts: list[Post], group_url: str) -> None:
    """Send email notification with matched Facebook posts."""
    config = load_env_config()
    
    # Skip if config is empty (missing credentials)
    if not config:
        return
    
    token = get_graph_token(config["tenant_id"], config["client_id"], config["client_secret"])

    # Build subject with category-specific emoji
    if len(posts) == 1:
        post = posts[0]
        category = post.get("category", "Other")
        emoji = get_category_emoji(category)
        post_time = post.get("timestamp", "Unknown time")
        title = post.get("title", "")[:60]
        subject = f"{emoji} {category} | {post_time} | {title}"
    else:
        # Multiple posts - show count and latest time
        latest_time = posts[0].get("timestamp", "Unknown time")
        categories = list(set(p.get("category", "Other") for p in posts))
        # Use emoji from the first category
        emoji = get_category_emoji(categories[0])
        cat_str = ", ".join(categories[:3])
        subject = f"{emoji} {len(posts)} jobs | {cat_str} | {latest_time}"

    # Determine header emoji and description based on categories present
    all_categories = list(set(p.get("category", "Other") for p in posts))
    if len(all_categories) == 1:
        header_emoji = get_category_emoji(all_categories[0])
        header_label = all_categories[0]
    else:
        header_emoji = "📋"
        header_label = "New Job Matches"

    html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; }}
        .header {{ background-color: #2c5aa0; color: white; padding: 20px; text-align: center; }}
        .post-card {{ margin: 20px 0; padding: 20px; background-color: #f5f5f5; border-left: 4px solid #2c5aa0; border-radius: 4px; }}
        .post-title {{ margin: 0 0 10px 0; color: #2c5aa0; font-size: 18px; }}
        .post-title a {{ color: #2c5aa0; text-decoration: none; }}
        .post-meta {{ font-size: 14px; color: #666; margin-bottom: 10px; }}
        .post-group {{ margin-bottom: 5px; }}
        .post-timestamp {{ margin-bottom: 10px; }}
        .post-id {{ margin-bottom: 10px; font-family: monospace; color: #888; }}
        .post-link {{ color: #2c5aa0; font-size: 14px; text-decoration: none; }}
        .post-text {{ white-space: pre-wrap; margin-top: 15px; }}
        .category-tag {{ display: inline-block; background-color: #e8f0fe; color: #2c5aa0; padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 600; margin-bottom: 10px; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center; }}
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin: 0;">{header_emoji} {header_label}</h1>
        <p style="margin: 10px 0 0 0;">Found <strong>{len(posts)}</strong> matching post(s)</p>
    </div>
"""

    for idx, post in enumerate(posts, start=1):
        # Escape HTML special characters
        title_html = post["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        post_html = post["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        post_url = post["url"]
        post_id = post["post_id"]
        timestamp = post["timestamp"]
        group_name = post["group_name"]
        group_url_post = post["group_url"]
        category = post.get("category", "Other")
        emoji = get_category_emoji(category)
        
        html_body += f"""
    <div class="post-card">
        <div class="category-tag">{emoji} {category}</div>
        <h3 class="post-title">
            <a href="{post_url}">{title_html}</a>
        </h3>
        <div class="post-meta">
            <div class="post-id">
                🆔 Post ID: {post_id}
            </div>
            <div class="post-group">
                📍 <a href="{group_url_post}" style="color: #666; text-decoration: none;">{group_name}</a>
            </div>
            <div class="post-timestamp">
                🕒 Posted: {timestamp}
            </div>
            <a href="{post_url}" class="post-link">View on Facebook →</a>
        </div>
        <div class="post-text">{post_html}</div>
    </div>
"""

    html_body += """
    <div class="footer">
        <p>This is an automated notification from your Facebook Work Notifier script.</p>
    </div>
</body>
</html>
"""

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Send to single recipient
    recipients = [
        {"emailAddress": {"address": "vladislavlevitin1999@gmail.com"}},
    ]
    
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": recipients,
        },
        "saveToSentItems": True,
    }

    resp = requests.post(
        f"https://graph.microsoft.com/v1.0/users/{config['sender']}/sendMail",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code >= 300:
        raise SystemExit(f"Failed to send email ({resp.status_code}): {resp.text[:500]}")
