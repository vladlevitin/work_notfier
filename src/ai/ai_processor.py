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
    "Electrical": "Electrician work, wiring, lights, mirrors with electrical connections, outlets, fuse boxes, stove guards",
    "Plumbing": "Pipes, water, drains, toilets, sinks, showers, bathrooms (water-related)",
    "Transport / Moving": "Moving furniture/items from one place to another, helping with relocation, transporting goods, pickup/delivery services, moving companies (flytting, flytte, hente, levere, transport)",
    "Painting / Renovation": "Painting walls, spackling, wallpaper, renovation, construction work, tiling (fliser), carpentry",
    "Cleaning / Garden": "House cleaning, garden work, lawn care, window washing, snow removal",
    "Assembly / Furniture": "IKEA assembly, furniture mounting, shelves, TV mounting, disassembly",
    "Car Mechanic": "Car repairs, car inspections, brakes, engine, mechanical work on vehicles, tire changes (dekk), bilmekaniker, car sounds/noises, vehicle diagnostics - ANY work ON the car itself",
    "Handyman / Misc": "Small repairs, odd jobs, demolition, removal of items",
    "IT / Tech": "Computer help, phone repair, smart home, technical support",
    "General": "Only use if NOTHING else fits"
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
            model="gpt-5.2-chat-latest",
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
        return "REQUEST" in result
        
    except Exception as e:
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

CRITICAL RULES - READ CAREFULLY:
1. "Car Mechanic" = ANY work ON a car (repairs, inspections, tire changes, noises, diagnostics, brakes, engine)
   - "bilmekaniker", "verksted", "dekk", "lyd på bilen", "sjekke bilen" = Car Mechanic
   
2. "Transport / Moving" = Moving ITEMS/FURNITURE from place A to place B, helping someone relocate
   - "flytte", "flytting", "hente noe", "levere noe", "transport av møbler" = Transport / Moving
   - This is NOT about fixing cars, it's about transporting things!

3. "Electrical" = Electrician work, wiring, lights, outlets, fuse boxes
   - "elektriker", "stikkontakt", "lys", "speil med lys" = Electrical

4. Do NOT use "General" unless absolutely nothing else fits

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
            model="gpt-5.2-chat-latest",  # Fast and cost-effective
            messages=[
                {"role": "system", "content": """You are a job posting analyzer for Norwegian small jobs. 
CRITICAL: Car mechanic work (repairs, inspections, tire changes) is "Car Mechanic", NOT "Transport / Moving".
Transport/Moving is ONLY for moving furniture/items between locations.
Classify posts accurately into the MOST SPECIFIC category. Always respond with valid JSON only."""},
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
        
        return {
            "category": category,
            "location": result.get("location", "Unknown"),
            "ai_features": result.get("features", {}),
            "ai_processed": True
        }
        
    except Exception as e:
        # Silently handle AI failures
        # Return fallback values
        return {
            "category": "General",
            "location": "Unknown",
            "ai_features": {},
            "ai_processed": False
        }


def is_driving_job(title: str, text: str) -> bool:
    """
    Use AI to determine if a post is PRIMARILY a driving/transport job.
    
    Returns True only if the MAIN work is driving, transport, or moving items.
    Returns False if driving/transport is just a minor part of another job
    (e.g., kitchen installation that needs transport).
    """
    content = f"Title: {title}\n\nPost content:\n{text[:1500]}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-5.2-chat-latest",
            messages=[
                {"role": "system", "content": """You determine if a job post is PRIMARILY a driving/transport job.

Answer "YES" only if the MAIN work requested is:
- Driving a vehicle (being a driver/chauffeur)
- Transporting items from A to B (the main job is the transport itself)
- Moving/relocation services (flytting, moving help)
- Delivery/pickup services where driving is the main task
- Looking for someone with a vehicle to transport things

Answer "NO" if:
- Transport is just a SMALL PART of a larger job (e.g., kitchen renovation that includes transport)
- The main job is something else (plumbing, painting, assembly) even if transport is mentioned
- Someone needs help with manual work that happens to mention transport
- The post is about car repairs (mechanic work, not driving)

Be strict - only say YES if driving/transport IS the main job being requested."""},
                {"role": "user", "content": f"Is this PRIMARILY a driving/transport job? Answer only YES or NO.\n\n{content}"}
            ],
            temperature=0.1,
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip().upper()
        return "YES" in result
        
    except Exception:
        # If AI fails, be conservative and don't send email
        return False


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
