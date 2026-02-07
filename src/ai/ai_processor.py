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

# Define available categories with descriptions for AI classification
CATEGORIES = {
    "Electrical": "Electrician work, wiring, lights, mirrors with electrical connections, outlets, fuse boxes, stove guards",
    "Plumbing": "Pipes, water, drains, toilets, sinks, showers, bathrooms (water-related)",
    "Transport / Moving": "Physically moving/transporting ITEMS or FURNITURE from place A to place B, helping someone relocate, pickup/delivery of items, needing a moving van, lifting and carrying items to move them. The vehicle is the TOOL for transport, NOT the thing being worked on",
    "Manual Labor": "Heavy lifting, carrying heavy items, physical work, loading/unloading, demolition, removal work, outdoor physical labor - no qualifications required",
    "Painting / Renovation": "Painting walls, spackling, wallpaper, renovation, construction work, tiling (fliser), carpentry, demolition, removing walls or structures",
    "Cleaning / Garden": "House cleaning, garden work, lawn care, window washing, snow removal",
    "Assembly / Furniture": "IKEA assembly, furniture mounting, shelves, TV mounting, disassembly",
    "Car Mechanic": "Any mechanical/repair work ON a vehicle (car, truck/lastebil, van, motorcycle): brakes, engine, tire changes, inspections, diagnostics, car sounds/noises. If someone needs work DONE ON the vehicle itself, it's Car Mechanic",
    "Handyman / Misc": "Small repairs, odd jobs that don't fit other specific categories",
    "IT / Tech": "Computer help, phone repair, smart home, technical support",
    "Other": "Posts that don't fit any of the above categories - e.g. crowdfunding, pet care, babysitting, tutoring, personal services, etc."
}

CATEGORY_LIST = list(CATEGORIES.keys())


def is_service_request(title: str, text: str) -> bool:
    """
    Use AI to determine if a post is a SERVICE REQUEST (someone needs help)
    vs a SERVICE OFFER (someone offering their services).
    
    This is 100% AI-driven — no keyword matching.
    
    Returns True if it's a request for service (we want to keep these).
    Returns False if it's an offer/advertisement (we want to filter these out).
    """
    content = f"{title}\n{text}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-5.2-chat-latest",
            messages=[
                {"role": "system", "content": """You are an expert at analyzing Norwegian/English job postings from Facebook groups. Your job is to determine whether a post is someone ASKING for a service (REQUEST) or someone OFFERING/ADVERTISING a service (OFFER).

OFFER (return "OFFER") — The poster is OFFERING or ADVERTISING their services to others:
- They describe what services THEY can provide
- They list their skills, qualifications, experience, or equipment
- They mention prices, rates, or competitive pricing
- They invite people to contact them for services
- They ask rhetorical questions like "Trenger du hjelp?" (Do you need help?) followed by what they can do
- They use language like "Vi/Jeg tilbyr...", "Vi/Jeg utfører...", "Vi/Jeg kan...", "Vi fikser..."
- They describe their business, company, or professional background
- They list MULTIPLE services they provide
- Companies looking to HIRE workers for their business

REQUEST (return "REQUEST") — The poster NEEDS someone to do a specific job for them:
- They describe a specific task they need done
- They are asking for help with something concrete
- They use language like "Trenger hjelp med...", "Ser etter noen som kan...", "Noen som kan...?"
- They are an individual person needing a specific service performed
- They ask for price quotes or availability

KEY DISTINCTION: "Trenger du hjelp med...?" (Do YOU need help?) = OFFER (advertising to customers). "Trenger hjelp med..." (Need help with...) = REQUEST (asking for help).

When in doubt, classify as OFFER — we only want genuine requests where someone needs a job done.

Respond with ONLY one word: REQUEST or OFFER"""},
                {"role": "user", "content": content}
            ],
            temperature=0.1,
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip().upper()
        is_request = "REQUEST" in result
        if not is_request:
            print(f"    [AI FILTER] Rejected as OFFER")
        return is_request
        
    except Exception as e:
        print(f"    [AI FILTER] Error: {str(e)[:50]} - keeping post")
        # Default to keeping the post if AI fails
        return True


def process_post_with_ai(title: str, text: str, post_id: str) -> Dict[str, any]:
    """
    Use AI to classify a post into a category and extract location/features.
    
    This is 100% AI-driven — no keyword matching. The AI receives the full list
    of available categories and picks the best match.
    
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
        
        prompt = f"""Analyze this Norwegian job posting and classify it into the most appropriate category.

AVAILABLE CATEGORIES:
{category_desc}

Post Title: {title}
Post Content: {text}

Instructions:
- Choose the single MOST SPECIFIC category that best matches the post.
- "Car Mechanic" is for work DONE ON a vehicle (repairs, brakes, tires, engine, inspections).
- "Transport / Moving" is for physically moving/transporting ITEMS from one place to another, or helping someone relocate. The vehicle is the tool, not the subject.
- Use "Other" for posts that genuinely don't fit any specific category (e.g. crowdfunding, pet care, tutoring).
- Extract the location if mentioned (city, area, or district name).

Respond in JSON format only:
{{
  "category": "one of the exact category names listed above",
  "location": "city or area name, or Unknown",
  "features": {{
    "urgency": "urgent/normal/flexible",
    "price_mentioned": true/false,
    "contact_method": "pm/phone/comment/not_specified"
  }}
}}"""

        response = client.chat.completions.create(
            model="gpt-5.2-chat-latest",
            messages=[
                {"role": "system", "content": "You are a Norwegian job posting classifier. Classify posts into the most specific matching category. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        result = json.loads(content)
        
        # Validate category is one of the valid ones
        category = result.get("category", "Other")
        if category not in CATEGORY_LIST:
            # Try to find a close match
            category_lower = category.lower()
            for valid_cat in CATEGORY_LIST:
                if valid_cat.lower() in category_lower or category_lower in valid_cat.lower():
                    category = valid_cat
                    break
            else:
                category = "Other"
        
        return {
            "category": category,
            "location": result.get("location", "Unknown"),
            "ai_features": result.get("features", {}),
            "ai_processed": True
        }
        
    except Exception as e:
        print(f"    [AI CLASSIFY] Error: {str(e)[:50]}")
        return {
            "category": "Other",
            "location": "Unknown",
            "ai_features": {},
            "ai_processed": False
        }


def is_driving_job(title: str, text: str) -> bool:
    """
    Determine if a post is about MOVING/TRANSPORT work.
    
    This function should match posts where someone needs help with:
    - Moving (flytte, flytting, flyttebil)
    - Transporting items (transport, frakte, hente, levere)
    - Delivery/pickup services
    """
    content = f"Title: {title}\n\nPost content:\n{text[:1500]}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-5.2-chat-latest",
            messages=[
                {"role": "system", "content": """Determine if this post is a REQUEST for MOVING or TRANSPORT help.

Answer "YES" if the person is ASKING FOR HELP with:
- Moving/relocating (flytte, flytting, skal flytte, trenger hjelp til å flytte)
- Needing a moving van or vehicle (flyttebil, varebil, henger)
- Transporting items from A to B (transport, frakte, hente, levere)
- Picking up or delivering something (hente noe, levere noe)
- Moving furniture or belongings

Answer "NO" if:
- Someone is OFFERING/ADVERTISING their services (not requesting)
- The post lists MULTIPLE services they can do (like "I can do cleaning, shopping, driving...")
- The main task is demolition, renovation, or repairs (not moving)
- The main task is car repairs/mechanics
- It's about something unrelated to moving/transport

IMPORTANT: If someone says "trenger hjelp til å flytte" (need help to move) or similar - that's a YES.
Focus on whether they are REQUESTING moving/transport help, not offering it."""},
                {"role": "user", "content": f"Is this a REQUEST for MOVING/TRANSPORT help? Answer only YES or NO.\n\n{content}"}
            ],
            temperature=0.1,
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip().upper()
        return "YES" in result
        
    except Exception:
        # If AI fails, be conservative and don't send email
        return False


def is_manual_labor_job(title: str, text: str) -> bool:
    """
    Determine if a post is about MANUAL LABOR work (heavy lifting, carrying, physical work).
    
    This is for low-skill labor that doesn't require qualifications.
    """
    content = f"Title: {title}\n\nPost content:\n{text[:1500]}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-5.2-chat-latest",
            messages=[
                {"role": "system", "content": """Determine if this post is requesting MANUAL LABOR / PHYSICAL WORK.

Answer "YES" if the MAIN task involves:
- Heavy lifting (løfte tungt, bære tungt)
- Carrying heavy items (bære møbler, bære ting)
- Moving furniture within a building (not transport between locations)
- Physical demolition/removal work (rive, fjerne, rydde)
- Loading/unloading items (laste, losse)
- Garden/outdoor physical work (grave, måke snø, klippe)
- Assembly requiring physical effort (montere møbler)
- General physical helper work (hjelpe med tungt arbeid)

Answer "NO" if:
- It's primarily about DRIVING/TRANSPORT (that's a different category)
- It requires professional qualifications (electrician, plumber, etc.)
- It's about cleaning, babysitting, pet care, or skilled trades
- Someone is OFFERING services (not requesting)
- The physical work is just a small part of a larger skilled job

This is for LOW-SKILL physical labor that someone can do without special qualifications."""},
                {"role": "user", "content": f"Is this post requesting MANUAL LABOR / PHYSICAL WORK? Answer only YES or NO.\n\n{content}"}
            ],
            temperature=0.1,
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip().upper()
        return "YES" in result
        
    except Exception:
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
