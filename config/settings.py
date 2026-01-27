"""Application settings and configuration."""

import json
import os
from pathlib import Path
from typing import List, Dict

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Configuration file paths
GROUPS_CONFIG = PROJECT_ROOT / "config" / "groups.json"


def load_facebook_groups() -> List[Dict]:
    """
    Load Facebook groups from config/groups.json.
    
    Returns:
        List of group configurations
    """
    with open(GROUPS_CONFIG, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Return only enabled groups
    return [g for g in config['facebook_groups'] if g.get('enabled', True)]


def get_all_groups() -> List[Dict]:
    """Get all groups (enabled and disabled)."""
    with open(GROUPS_CONFIG, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config['facebook_groups']


# Search keywords for filtering posts
KEYWORDS = [
    "kjøre", "kjøring", "bil", "flytte", "flytting",
    "transport", "sjåfør", "fører", "førerkort",
    "levering", "hente", "frakt", "flyttejobb", "kjøretur",
    "kjoring", "sjafoer", "forerkort"
]

# AI Processing
AI_ENABLED = os.getenv("OPENAI_API_KEY") is not None
AI_MODEL = "gpt-4o-mini"  # Fast and cost-effective

# Job Categories
CATEGORIES = [
    "Transport / Moving",
    "Painting / Renovation",
    "Cleaning / Garden",
    "Plumbing / Electrical",
    "Assembly / Furniture",
    "General"
]

# Email settings
EMAIL_ENABLED = os.getenv("GMAIL_APP_PASSWORD") is not None

if __name__ == "__main__":
    # Test configuration loading
    print("=== Facebook Work Notifier Configuration ===\n")
    
    groups = load_facebook_groups()
    print(f"Loaded {len(groups)} enabled groups:\n")
    
    for idx, group in enumerate(groups, 1):
        print(f"{idx}. {group['name']}")
        print(f"   URL: {group['url']}")
        print(f"   Scroll steps: {group.get('scroll_steps', 5)}")
        if group.get('description'):
            print(f"   Description: {group['description']}")
        print()
    
    print(f"\nAI Processing: {'Enabled' if AI_ENABLED else 'Disabled'}")
    print(f"Email Notifications: {'Enabled' if EMAIL_ENABLED else 'Disabled'}")
    print(f"\nKeywords: {len(KEYWORDS)} total")
    print(f"Categories: {len(CATEGORIES)} total")
