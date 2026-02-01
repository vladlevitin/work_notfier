"""
AI-powered post processor using OpenAI to extract:
- Category (Transport, Painting, Cleaning, etc.)
- Location (Oslo, Asker, etc.)
- Post type (request vs offer)
- Other relevant features
"""

import os
import json
from typing import Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define available categories with descriptions
CATEGORIES = {
    "Electrical": "Electrician work, wiring, lights, mirrors with electrical, outlets, fuse boxes, stove guards",
    "Plumbing": "Pipes, water, drains, toilets, sinks, showers, bathrooms (water-related)",
    "Transport / Moving": "Moving items, transporting goods, pickup/delivery, using vehicles",
    "Painting / Renovation": "Painting walls, spackling, wallpaper, renovation, construction work", 
    "Cleaning / Garden": "House cleaning, garden work, lawn care, window washing",
    "Assembly / Furniture": "IKEA assembly, furniture mounting, shelves, TV mounting",
    "Mechanic / Car": "Car repairs, brakes, mechanical work on vehicles",
    "General": "Anything that doesn't fit the other categories"
}

CATEGORY_LIST = list(CATEGORIES.keys())


def is_service_request(title: str, text: str) -> bool:
    """
    Use OpenAI to determine if a post is a SERVICE REQUEST (someone needs help)
    vs a SERVICE OFFER (someone offering their services).
    
    Returns True if it's a request for service (we want to keep these).
    Returns False if it's an offer/advertisement (we want to filter these out).
    """
    try:
        content = f"{title}\n{text}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """You analyze Norwegian job postings to determine if they are:
- SERVICE_REQUEST: Someone NEEDS help/service (e.g., "Trenger hjelp med...", "Ser etter noen som kan...", "Ønsker å få...")
- SERVICE_OFFER: Someone is OFFERING their services (e.g., "Tilbyr...", "Leier ut...", "Vi utfører...", "Jeg kan hjelpe med...")

Respond with ONLY one word: REQUEST or OFFER"""},
                {"role": "user", "content": content}
            ],
            temperature=0.1,
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip().upper()
        print(f"    [AI] Post type: {result}")
        
        return "REQUEST" in result
        
    except Exception as e:
        print(f"    [AI] Classification failed: {e}")
        # Default to keeping the post if classification fails
        return True


def process_post_with_ai(title: str, text: str, post_id: str) -> Dict[str, any]:
    """
    Use OpenAI to extract category, location, and features from a post.
    
    Args:
        title: Post title
        text: Post content
        post_id: Post ID (for caching/tracking)
    
    Returns:
        Dictionary with: category, location, features
    """
    try:
        # Build category descriptions for the prompt
        category_desc = "\n".join([f"- {cat}: {desc}" for cat, desc in CATEGORIES.items()])
        
        prompt = f"""Analyze this Norwegian job posting and classify it.

CATEGORIES (choose the MOST SPECIFIC one that matches):
{category_desc}

Post Title: {title}
Post Content: {text}

IMPORTANT: 
- If the post mentions "elektriker" (electrician), lights, wiring, outlets, mirrors with electrical connections, or any electrical work -> choose "Electrical"
- If the post mentions moving/transporting items from A to B -> choose "Transport / Moving"
- If the post mentions painting, spackling, walls -> choose "Painting / Renovation"
- Be SPECIFIC - don't default to General if a specific category fits

Respond in JSON format:
{{
  "category": "one of the exact category names above",
  "location": "city or area name, or Unknown",
  "features": {{
    "urgency": "urgent/normal/flexible",
    "price_mentioned": true/false,
    "contact_method": "pm/phone/comment/not_specified"
  }}
}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cost-effective
            messages=[
                {"role": "system", "content": "You are a job posting analyzer for Norwegian small jobs. Classify posts accurately into the MOST SPECIFIC category. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Lower temperature for more consistent classification
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        result = json.loads(content)
        
        # Validate category is one of the valid ones
        category = result.get("category", "General")
        if category not in CATEGORY_LIST:
            # Try to find a close match
            category_lower = category.lower()
            for valid_cat in CATEGORY_LIST:
                if valid_cat.lower() in category_lower or category_lower in valid_cat.lower():
                    category = valid_cat
                    break
            else:
                category = "General"
        
        print(f"    [AI] Category: {category}")
        
        return {
            "category": category,
            "location": result.get("location", "Unknown"),
            "ai_features": result.get("features", {}),
            "ai_processed": True
        }
        
    except Exception as e:
        print(f"AI processing failed for post {post_id}: {str(e)}")
        # Return fallback values
        return {
            "category": "General",
            "location": "Unknown",
            "ai_features": {},
            "ai_processed": False
        }


def should_process_with_ai(post_id: str, existing_data: Optional[Dict] = None) -> bool:
    """
    Check if post should be processed with AI.
    
    Args:
        post_id: Post ID
        existing_data: Existing post data from database (if any)
    
    Returns:
        True if should process, False if already processed
    """
    # If no existing data, need to process
    if not existing_data:
        return True
    
    # If already processed with AI, skip
    if existing_data.get('ai_processed'):
        return False
    
    # If missing category or location, process
    if not existing_data.get('category') or not existing_data.get('location'):
        return True
    
    return False
