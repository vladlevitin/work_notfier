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
    "Manual Labor": "Heavy lifting, carrying heavy items, physical work, loading/unloading, demolition, removal work, outdoor physical labor - no qualifications required",
    "Painting / Renovation": "Painting walls, spackling, wallpaper, renovation, construction work, tiling (fliser), carpentry",
    "Cleaning / Garden": "House cleaning, garden work, lawn care, window washing, snow removal",
    "Assembly / Furniture": "IKEA assembly, furniture mounting, shelves, TV mounting, disassembly",
    "Car Mechanic": "Car repairs, car inspections, brakes, engine, mechanical work on vehicles, tire changes (dekk), bilmekaniker, car sounds/noises, vehicle diagnostics - ANY work ON the car itself",
    "Handyman / Misc": "Small repairs, odd jobs that don't fit other categories",
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
                {"role": "system", "content": """You analyze Norwegian/English job postings to classify them as REQUEST or OFFER.

OFFER (return "OFFER") - Someone is ADVERTISING/OFFERING their services:
- "Tilbyr..." / "Vi tilbyr..." / "Jeg tilbyr..."
- "Utfører..." / "Vi utfører..."  
- "Jeg kan hjelpe med..." / "Jeg kan..."
- Posts that LIST MULTIPLE SERVICES they can provide (like a menu of services)
- "TRENGER DU HJELP?" followed by listing what THEY can do = OFFER
- "Ledig kapasitet..." / "Vi har ledig tid..."
- "Ta kontakt for tilbud..." / "Send meg PM"
- "Rimelige priser..." / "Gode priser..."
- "Erfaren [profession] tilbyr..."
- Someone describing their experience/qualifications
- "Ønsker kun seriøse henvendelser" (only serious inquiries)
- Company/business/professional advertising services
- Looking to HIRE workers for their business
- "Flyttebyrå trenger..." (company looking for workers)

REQUEST (return "REQUEST") - Someone NEEDS a specific job done:
- "Trenger hjelp med..." / "Trenger noen som kan..."
- "Ser etter noen som kan..."
- "Ønsker å få [specific task]..." 
- "Noen som kan [specific task]?" (asking for help with ONE specific task)
- "Hva koster det å...?" (asking for price quote)
- Individual person needing ONE specific job done
- Asking for help with a concrete, specific task

CRITICAL: If someone lists MULTIPLE services they offer, it's an OFFER, not a request.
If someone says "Jeg kan..." (I can...) they are OFFERING, not requesting.

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
    Determine if a post is primarily about DRIVING/TRANSPORT work.
    
    Driving must be the PRIMARY task, not a secondary mention.
    Examples of YES: moving furniture, transporting items from A to B, delivery work
    Examples of NO: someone offering many services where driving is just one option
    """
    content = f"Title: {title}\n\nPost content:\n{text[:1500]}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-5.2-chat-latest",
            messages=[
                {"role": "system", "content": """Determine if DRIVING/TRANSPORT is the PRIMARY job in this post.

Answer "YES" ONLY if the MAIN task is:
- Moving/transporting items or furniture from location A to location B
- Driving someone's belongings during a move (flytting, flytte)
- Transporting/delivering specific items (frakte, transport, levere)
- Pickup service where driving is the main job (hente noe fra X til Y)
- Someone needs a vehicle with driver (varebil, henger)
- Driving a person from A to B as the main service

Answer "NO" if:
- Driving is just ONE of many services listed (like babysitting, cleaning, shopping, dog walking, etc.)
- The post mentions "Jeg kan kjøre deg" as a minor add-on to other services
- The main job is something else (cleaning, repairs, childcare) with driving as secondary
- Someone is OFFERING services (not requesting)
- The post is about car repairs/mechanics
- The post lists multiple unrelated services they offer

CRITICAL: If the post lists multiple different services (like shopping, babysitting, cleaning, pet care, etc.) and driving is just one option among many - answer NO.

Only answer YES if transporting items/people from A to B is the MAIN purpose of the job request."""},
                {"role": "user", "content": f"Is DRIVING/TRANSPORT the PRIMARY job in this post? Answer only YES or NO.\n\n{content}"}
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
