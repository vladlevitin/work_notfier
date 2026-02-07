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
    "Transport / Moving": "ONLY for: Moving/relocating (flytte, flytting), transporting items/furniture from A to B, pickup/delivery services, needing a moving van (flyttebil). NOT for demolition, repairs, or renovation work",
    "Manual Labor": "Heavy lifting, carrying heavy items, physical work, loading/unloading, demolition, removal work, outdoor physical labor - no qualifications required",
    "Painting / Renovation": "Painting walls, spackling, wallpaper, renovation, construction work, tiling (fliser), carpentry, demolition (rive, riving), removing walls or structures",
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
    content = f"{title}\n{text}"
    content_lower = content.lower()
    
    # Quick keyword-based pre-filter for obvious service OFFERS
    # These patterns clearly indicate someone is OFFERING services, not requesting
    offer_patterns = [
        "vi tilbyr",           # We offer
        "jeg tilbyr",          # I offer
        "tilbyr mine tjenester",  # Offer my services
        "tilbyr hjelp",        # Offer help
        "tilbyr flyttehjelp",  # Offer moving help
        "tilbyr tjenester",    # Offer services
        "utfører alle typer",  # Perform all types
        "utfører oppdrag",     # Perform jobs
        "vi utfører",          # We perform
        "jeg utfører",         # I perform
        "ledig kapasitet",     # Available capacity
        "har ledig tid",       # Have available time
        "ta kontakt for",      # Contact for
        "kontakt meg for",     # Contact me for
        "send pm for",         # Send PM for
        "send melding for",    # Send message for
        "rimelige priser",     # Reasonable prices
        "konkurransedyktige priser",  # Competitive prices
        "gode priser",         # Good prices
        "erfaren håndverker",  # Experienced handyman
        "erfaren snekker",     # Experienced carpenter
        "erfaren elektriker",  # Experienced electrician
        "erfaren maler",       # Experienced painter
        "vi kan hjelpe",       # We can help
        "jeg kan hjelpe",      # I can help
        "jeg kan også",        # I can also (offering additional services)
        "effektive og hyggelige",  # Efficient and friendly (common ad phrase)
        "hyggelige karer",     # Friendly guys (common ad phrase)
        "ønsker kun seriøse",  # Only want serious (inquiries)
        "kun seriøse henvendelser",  # Only serious inquiries
        "vi er et firma",      # We are a company
        "vårt firma",          # Our company
        "min bedrift",         # My business
        "stiller med",         # Come with (equipment/van)
        "stor kassebil",       # Large box van (advertising their equipment)
        "egen bil",            # Own car (advertising their equipment)
        "har fagbrev",         # Has trade certificate (advertising qualifications)
        "års erfaring",        # Years of experience (advertising qualifications)
        "lang erfaring",       # Long experience
        "ta kontakt så",       # Contact us and we'll... (offering services)
        "jeg kan bygge",       # I can build
        "jeg kan fikse",       # I can fix
        "jeg kan reparere",    # I can repair
        "jeg kan montere",     # I can install/assemble
        "jeg kan male",        # I can paint
        "jeg kan pusse",       # I can renovate
        "jeg kan gjøre",       # I can do
        "vi kan gjøre",        # We can do
        "vi kan fikse",        # We can fix
        "vi kan bygge",        # We can build
        "vi kan montere",      # We can install/assemble
        "dersom det er ønskelig",  # If desired (offering optional services)
        "trenger du hjelp",    # Do you need help? (asking if YOU need = offering)
        "trenger du noen",     # Do you need someone? (offering)
        "trenger du flyttehjelp",  # Do you need moving help? (offering)
        "fikser vi",           # We fix (advertising services)
        "ordner vi",           # We arrange/fix (advertising services)
        "beste prisene",       # Best prices
        "de beste prisene",    # The best prices
        "billigste prisene",   # Cheapest prices
        "send pm om",          # Send PM if (offering services)
        "send melding om",     # Send message if (offering services)
        "om du trenger",       # If you need (offering services)
        "hvis du trenger",     # If you need (offering services)
        "vi har de beste",     # We have the best
        "vi fikser",           # We fix
        "vi ordner",           # We arrange
        "alt fra",             # Everything from (listing multiple services)
    ]
    
    for pattern in offer_patterns:
        if pattern in content_lower:
            print(f"    [FILTER] Rejected as OFFER (keyword: '{pattern}')")
            return False
    
    # If no obvious offer keywords, use OpenAI for nuanced classification
    try:
        response = client.chat.completions.create(
            model="gpt-5.2-chat-latest",
            messages=[
                {"role": "system", "content": """You analyze Norwegian/English job postings to classify them as REQUEST or OFFER.

OFFER (return "OFFER") - Someone is ADVERTISING/OFFERING their services:
- "Tilbyr..." / "Vi tilbyr..." / "Jeg tilbyr..."
- "Utfører..." / "Vi utfører..."  
- "Jeg kan hjelpe med..." / "Jeg kan..." / "Jeg kan også..."
- Posts that LIST MULTIPLE SERVICES they can provide (like a menu of services)
- "TRENGER DU HJELP?" / "Trenger du hjelp med...?" = OFFER (asking if YOU need help = advertising!)
- "Har du en [thing] som trenger [service]?" = OFFER (asking if YOU need their service)
- "Trenger du [service]? Vi/Jeg kan..." = OFFER (question directed at reader + what they offer)
- "Send PM om du trenger hjelp" = OFFER (inviting customers to contact them)
- "Ledig kapasitet..." / "Vi har ledig tid..."
- "Ta kontakt for tilbud..." / "Send meg PM" / "Ta kontakt så..."
- "Rimelige priser..." / "Gode priser..." / "Beste prisene..."
- "Erfaren [profession] tilbyr..."
- Someone describing their experience, qualifications, or certifications (e.g. "fagbrev", "års erfaring")
- "Ønsker kun seriøse henvendelser" (only serious inquiries)
- Company/business/professional advertising services
- Looking to HIRE workers for their business
- "Flyttebyrå trenger..." (company looking for workers)
- Someone saying what THEY can do for YOU (building, fixing, repairing, installing)
- "Dersom det er ønskelig" (if desired) - offering optional extras
- "Vi fikser..." / "Vi ordner..." / "...fikser vi" = OFFER (we fix/arrange)
- "Alt fra [X] til [Y]" = OFFER (listing range of services)

REQUEST (return "REQUEST") - Someone NEEDS a specific job done:
- "Trenger hjelp med..." / "Trenger noen som kan..."
- "Ser etter noen som kan..."
- "Ønsker å få [specific task]..." 
- "Noen som kan [specific task]?" (asking for help with ONE specific task)
- "Hva koster det å...?" (asking for price quote)
- Individual person needing ONE specific job done
- Asking for help with a concrete, specific task

CRITICAL RULES:
1. If someone lists MULTIPLE services they offer, it's an OFFER, not a request.
2. If someone says "Jeg kan..." (I can...) or "Vi fikser..." (We fix...) they are OFFERING, not requesting.
3. If someone mentions their qualifications (fagbrev, erfaring, sertifikat) they are OFFERING.
4. If the post is structured as "Do you need X? I/We can do X" it's an OFFER.
5. "Trenger du hjelp med...?" (Do YOU need help with...?) is an OFFER - they're advertising to potential customers!
   This is different from "Trenger hjelp med..." (Need help with...) which is a REQUEST.
6. If someone mentions prices ("beste prisene", "gode priser") they are OFFERING.
7. "Send PM om du trenger..." (Send PM if you need...) is an OFFER.
8. When in doubt, lean towards OFFER - we only want genuine requests for help.

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
