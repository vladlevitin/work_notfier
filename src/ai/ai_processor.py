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

# Model to use for all AI calls (must be a valid OpenAI model)
AI_MODEL = "gpt-4o-mini"

# Define available categories with descriptions for AI classification
CATEGORIES = {
    "Electrical": "Electrician work, wiring, lights, mirrors with electrical connections, outlets, fuse boxes, stove guards",
    "Plumbing": "Pipes, water, drains, toilets, sinks, showers, bathrooms (water-related), rørlegger/rørleggerarbeid, relocating/moving kitchen or bathroom plumbing to a new room within a home",
    "Transport / Moving": "ONLY for physically moving/transporting ITEMS or FURNITURE from place A to place B, helping someone relocate to a new address, pickup/delivery of items, needing a moving van. NOT for building, constructing, or assembling things even if the words 'carry' or 'foldable' appear. NOT for relocating rooms/fixtures within a home (that's Plumbing or Painting / Renovation)",
    "Manual Labor": "Heavy lifting, carrying heavy items, physical work, loading/unloading, demolition, removal work, outdoor physical labor - no qualifications required",
    "Painting / Renovation": "Painting walls, spackling, wallpaper, renovation, construction work, tiling (fliser), carpentry (snekker), building/constructing custom items or structures, woodwork, demolition, removing walls or structures",
    "Cleaning / Garden": "House cleaning, garden work, lawn care, window washing, snow removal",
    "Assembly / Furniture": "IKEA assembly, furniture mounting, shelves, TV mounting, disassembly",
    "Car Mechanic": "Any mechanical/repair work ON a vehicle (car, truck/lastebil, van, motorcycle): brakes, engine, tire changes, inspections, diagnostics, car sounds/noises. If someone needs work DONE ON the vehicle itself, it's Car Mechanic",
    "Handyman / Misc": "Small repairs, odd jobs that don't fit other specific categories",
    "IT / Tech": "Computer help, phone repair, smart home, technical support",
    "Other": "Posts that don't fit any of the above categories - e.g. crowdfunding, pet care, babysitting, tutoring, personal services, etc."
}

CATEGORY_LIST = list(CATEGORIES.keys())


def _is_obvious_offer(title: str, text: str) -> bool:
    """
    Fast deterministic pre-filter to catch obvious service OFFERS before calling AI.
    Returns True if the post is clearly an offer/advertisement (should be filtered out).
    Returns False if uncertain — let the AI decide.
    
    This catches patterns that gpt-4o-mini repeatedly misclassifies.
    """
    import re as _re
    
    combined = f"{title}\n{text}".lower()
    
    # --- Pattern 1: "Trenger du/dere/noen hjelp" = asking if YOU need help = OFFER ---
    # "Trenger noen hjelp til å vaske huset?" / "Trenger du hjelp med flytting?"
    if _re.search(r'trenger\s+(du|dere|noen)\s+hjelp', combined):
        return True
    
    # --- Pattern 2: "Tilbyr" / "utfører" / "vi fikser" / "jeg kan" service language ---
    offer_verbs = [
        r'\b(vi|jeg)\s+(tilbyr|utfører|fikser|ordner|gjør|kan hjelpe)',
        r'\b(tilbyr|utfører)\s+\w+',
        r'\bvi\s+kan\s+hjelpe\s+deg',
        r'\bjeg\s+kan\s+hjelpe\s+deg',
    ]
    for pattern in offer_verbs:
        if _re.search(pattern, combined):
            return True
    
    # --- Pattern 3: Short post + "send pm/melding" + no specific task ---
    # Offers are typically short and just say "contact me"
    is_short = len(combined) < 200
    has_contact_invite = bool(_re.search(r'send\s*(gjerne\s*)?(en\s*)?(pm|melding|msg|dm)', combined))
    has_specific_task = bool(_re.search(r'(trenger\s+hjelp\s+(med|til)\b(?!.*\?))', combined))  # "trenger hjelp med/til" NOT ending in ?
    
    if is_short and has_contact_invite and not has_specific_task:
        return True
    
    # --- Pattern 4: Job seeker patterns ---
    job_seeker_patterns = [
        r'søk(er|nad)\s+(om\s+)?jobb',
        r'leter\s+etter\s+(en\s+)?jobb',
        r'på\s+utkikk\s+etter\s+(en\s+)?(ny\s+)?jobb',
        r'looking\s+for\s+(a\s+)?(new\s+)?job',
        r'available\s+for\s+work',
        r'ledig\s+for\s+oppdrag',
    ]
    for pattern in job_seeker_patterns:
        if _re.search(pattern, combined):
            return True
    
    return False


def is_service_request(title: str, text: str) -> bool:
    """
    Determine if a post is a SERVICE REQUEST (someone needs help)
    vs a SERVICE OFFER (someone offering their services).
    
    Uses a fast deterministic pre-filter first, then falls back to AI.
    
    Returns True if it's a request for service (we want to keep these).
    Returns False if it's an offer/advertisement (we want to filter these out).
    """
    # Fast pre-filter: catch obvious offers without calling AI
    if _is_obvious_offer(title, text):
        print(f"    [AI FILTER] Rejected as OFFER (pre-filter)")
        return False
    
    content = f"{title}\n{text}"
    
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": """You are an expert at analyzing Norwegian/English job postings from Facebook groups. Your job is to determine whether a post is someone ASKING for a service (REQUEST) or someone OFFERING/ADVERTISING a service or SEEKING EMPLOYMENT (OFFER).

OFFER (return "OFFER") — The poster is OFFERING services, ADVERTISING themselves, or SEEKING EMPLOYMENT:
- They describe what services THEY can provide
- They list their skills, qualifications, experience, or equipment
- They mention prices, rates, or competitive pricing
- They invite people to contact them for services ("send PM", "ta kontakt", "ring meg")
- They ask rhetorical questions like "Trenger du/noen hjelp?" (Do you/anyone need help?) — this is advertising, NOT requesting
- They use language like "Vi/Jeg tilbyr...", "Vi/Jeg utfører...", "Vi/Jeg kan...", "Vi fikser..."
- They describe their business, company, or professional background
- They list MULTIPLE services they provide
- They cover a WIDE geographic area (e.g. "Oslo og omegn", "Østfold & Oslo") — real requests are at a specific address/location
- Companies looking to HIRE workers for their business
- **JOB SEEKERS**: Someone LOOKING FOR WORK, applying for a job, seeking employment ("søker jobb", "søknad om jobb", "leter etter jobb", "på utkikk etter jobb", "looking for work")
- **CV/RESUME posts**: Someone presenting themselves, their experience, and contact info to get hired
- People saying "I can do X, Y, Z — contact me" or "I'm available for work"
- People describing themselves and asking others to hire them
- Short/vague posts that just advertise a service without a specific task (e.g. "Need cleaning? Send PM")

REQUEST (return "REQUEST") — The poster NEEDS someone to do a specific job for them:
- They describe a SPECIFIC task they need done (e.g., "need help moving a sofa", "need a plumber for my bathroom", "looking for someone to paint my apartment")
- They mention a SPECIFIC location where the work needs to happen (an address, building, apartment, specific neighborhood)
- They use language like "Trenger hjelp med...", "Ser etter noen som kan...", "Noen som kan...?"
- They are an individual person needing a specific service performed
- They ask for price quotes or availability FOR A SPECIFIC JOB
- The post contains DETAILS about the job (dimensions, materials, what exactly needs to be done)

KEY DISTINCTIONS:
- "Trenger du/noen hjelp med...?" (Do you/someone need help with...?) = OFFER (advertising to potential customers)
- "Trenger noen hjelp til å vaske huset?" = OFFER (asking if anyone needs cleaning — they're offering the service)
- "Trenger hjelp med..." / "Trenger hjelp til..." (I need help with...) = REQUEST (the poster needs help)
- "Søker jobb" / "Leter etter jobb" / "Søknad om jobb" = OFFER (seeking employment)
- "Jeg kan gjøre X" (I can do X) = OFFER (advertising skills)
- "Trenger noen til å gjøre X" (Need someone to do X) = REQUEST (looking for a worker)
- Short post + "send PM" + wide area = OFFER (advertising)
- Detailed post + specific location + specific task = REQUEST (genuine job)

When in doubt, classify as OFFER — we only want genuine requests where someone needs a specific job done.

EXAMPLES:
- "Trenger noen hjelp til å vaske huset? Østfold & Oslo og omegn. Send gjerne en pm" → OFFER (asking if anyone needs cleaning, advertising)
- "Hei! Vi utfører alt av maling, sparkling og tapetsering. Ta kontakt!" → OFFER (advertising services)
- "Søknad om jobb. Mitt navn er X, jeg har erfaring med Y..." → OFFER (job seeker)
- "Trenger hjelp med å flytte en sofa fra 3. etasje ned til bilen. Bor på Grünerløkka." → REQUEST (specific task, specific location)
- "Noen som kan skifte registerreim på en Peugeot 106?" → REQUEST (specific task needed)
- "Hei! Trenger hjelp til å legge gips i et kjellerrom over panel" → REQUEST (specific task)

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
        
        prompt = f"""Analyze this Norwegian job posting and classify it into categories.

AVAILABLE CATEGORIES:
{category_desc}

Post Title: {title}
Post Content: {text}

Instructions:
- Choose exactly ONE primary category — the MAIN task the person needs done.
- Also list any secondary categories if the post involves additional tasks from other categories. Only include secondary categories that are clearly mentioned — don't guess.
- "Car Mechanic" is for work DONE ON a vehicle (repairs, brakes, tires, engine, inspections, tow bar/tilhengerfeste installation, car painting/lakkering, software updates on cars). If someone needs something installed or fixed ON their car, it's Car Mechanic.
- "Transport / Moving" is ONLY for physically moving/transporting items from place A to place B, or helping someone relocate to a new address. NOT for installing parts on vehicles. NOT for relocating a kitchen/bathroom/room within a home — that's a renovation/plumbing job.
- "Plumbing" includes any rørlegger/rørleggerarbeid, setting up pipes for kitchens or bathrooms, AND relocating plumbing to a different room within a home (e.g. "kjøkken som skal flyttes fra et rom til et annet").
- "Painting / Renovation" covers carpentry (snekker), building custom items, woodwork, construction.
- "Assembly / Furniture" is for assembling pre-made/flat-pack items (IKEA, shelves, TV mounting).
- "Manual Labor" is for heavy lifting, carrying, demolition, removal work.
- Use "Other" for posts that genuinely don't fit any specific category.
- Extract the location if mentioned (city, area, or district name).

EXAMPLES:
- "Trenger hjelp med flyttevask, innbo skal kastes, men noen ting må gamles til loppemarked" → primary: "Cleaning / Garden", secondary: ["Transport / Moving"]
- "Trenger å flytte en sofa fra 3.etg ned til bilen" → primary: "Transport / Moving", secondary: ["Manual Labor"]
- "Sparkle, slipe og male et rom + montere ny lampe" → primary: "Painting / Renovation", secondary: ["Electrical"]
- "Trenger hjelp til å kaste søppel, noe bæring involvert" → primary: "Manual Labor", secondary: ["Transport / Moving"]
- "Montere tilhengerfeste med software på en Volvo XC90" → primary: "Car Mechanic", secondary: [] (work ON a vehicle)
- Building foldable wall panels by a carpenter → primary: "Painting / Renovation", secondary: []
- "Ønsker pris på rørleggerarbeid til bad, samt opplegg og montering av rør til kjøkken som skal flyttes fra naborom til stue" → primary: "Plumbing", secondary: [] (rørlegger work + relocating kitchen plumbing within a home is NOT transport)

Respond in JSON format only:
{{
  "category": "one of the exact category names listed above",
  "secondary_categories": ["other relevant category names, or empty array if none"],
  "location": "city or area name, or Unknown",
  "features": {{
    "urgency": "urgent/normal/flexible",
    "price_mentioned": true/false,
    "contact_method": "pm/phone/comment/not_specified"
  }}
}}"""

        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a Norwegian job posting classifier. Classify posts with a primary category and optional secondary categories. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=250
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        result = json.loads(content)
        
        # Validate primary category
        category = result.get("category", "Other")
        if category not in CATEGORY_LIST:
            category_lower = category.lower()
            for valid_cat in CATEGORY_LIST:
                if valid_cat.lower() in category_lower or category_lower in valid_cat.lower():
                    category = valid_cat
                    break
            else:
                category = "Other"
        
        # Validate secondary categories
        raw_secondary = result.get("secondary_categories", [])
        secondary_categories = []
        if isinstance(raw_secondary, list):
            for sec in raw_secondary:
                if sec in CATEGORY_LIST and sec != category:
                    secondary_categories.append(sec)
                else:
                    # Try fuzzy match
                    sec_lower = sec.lower() if isinstance(sec, str) else ""
                    for valid_cat in CATEGORY_LIST:
                        if valid_cat.lower() in sec_lower or sec_lower in valid_cat.lower():
                            if valid_cat != category and valid_cat not in secondary_categories:
                                secondary_categories.append(valid_cat)
                            break
        
        return {
            "category": category,
            "secondary_categories": secondary_categories,
            "location": result.get("location", "Unknown"),
            "ai_features": result.get("features", {}),
            "ai_processed": True
        }
        
    except Exception as e:
        print(f"    [AI CLASSIFY] Error: {str(e)[:50]}")
        return {
            "category": "Other",
            "secondary_categories": [],
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
            model=AI_MODEL,
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
            model=AI_MODEL,
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
