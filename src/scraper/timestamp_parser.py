"""Parse Facebook timestamp formats to Python datetime."""

import re
from datetime import datetime, timedelta
from typing import Optional


# Map month names to numbers (Norwegian and English)
MONTHS = {
    'january': 1, 'januar': 1, 'jan': 1,
    'february': 2, 'februar': 2, 'feb': 2,
    'march': 3, 'mars': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5, 'mai': 5,
    'june': 6, 'juni': 6, 'jun': 6,
    'july': 7, 'juli': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sep': 9, 'sept': 9,
    'october': 10, 'oktober': 10, 'oct': 10, 'okt': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'desember': 12, 'dec': 12, 'des': 12
}

# Norwegian day names for timestamp matching
NORWEGIAN_DAYS = ['mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', 'lørdag', 'søndag']


def parse_facebook_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse Facebook timestamp formats to datetime.
    
    Supports formats like:
    - "5m" (5 minutes ago)
    - "7h" (7 hours ago)
    - "2d" (2 days ago)
    - "Yesterday at 17:48"
    - "24 January at 08:42"
    - "5 May 2025"
    - "Sunday 1 February 2026 at 13:56" (full tooltip format)
    - "Recently"
    
    Args:
        timestamp_str: Facebook timestamp string
    
    Returns:
        datetime object or None if parsing fails
    """
    now = datetime.now()
    timestamp_str = timestamp_str.strip()
    
    # Format: "Sunday 1 February 2026 at 13:56" (full tooltip format with day name)
    match = re.match(r'^(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)\s+(\d+)\s+(\w+)\s+(\d{4})\s+at\s+(\d+):(\d+)$', timestamp_str, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        month_str = match.group(2)
        year = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))
        
        month = MONTHS.get(month_str.lower())
        if month:
            try:
                return datetime(year, month, day, hour, minute)
            except ValueError:
                return None
    
    # Format: Norwegian "lørdag 7. februar 2026 kl. 17:43" or "lørdag 7 februar 2026 kl. 17:43"
    match = re.match(r'^(?:\w+)\s+(\d+)\.?\s+(\w+)\s+(\d{4})\s+kl\.?\s+(\d+):(\d+)$', timestamp_str, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        month_str = match.group(2)
        year = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))
        
        month = MONTHS.get(month_str.lower())
        if month:
            try:
                return datetime(year, month, day, hour, minute)
            except ValueError:
                return None
    
    # Format: "7. februar kl. 17:43" or "7 februar kl. 17:43" (Norwegian without year)
    match = re.match(r'^(\d+)\.?\s+(\w+)\s+kl\.?\s+(\d+):(\d+)$', timestamp_str, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        month_str = match.group(2)
        hour = int(match.group(3))
        minute = int(match.group(4))
        
        month = MONTHS.get(month_str.lower())
        if month:
            year = now.year
            try:
                parsed_date = datetime(year, month, day, hour, minute)
                if parsed_date > now:
                    parsed_date = datetime(year - 1, month, day, hour, minute)
                return parsed_date
            except ValueError:
                return None
    
    # Format: "5m", "30m" or "5 min", "30 min" (minutes ago)
    match = re.match(r'^(\d+)\s*(?:m|min)$', timestamp_str, re.IGNORECASE)
    if match:
        minutes = int(match.group(1))
        return now - timedelta(minutes=minutes)
    
    # Format: "7h", "10h" or "7 t", "10 t" or "7 timer" (hours ago - English + Norwegian)
    match = re.match(r'^(\d+)\s*(?:h|t|timer?)$', timestamp_str, re.IGNORECASE)
    if match:
        hours = int(match.group(1))
        return now - timedelta(hours=hours)
    
    # Format: "2d", "5d" or "2 dager" (days ago)
    match = re.match(r'^(\d+)\s*(?:d|dager?)$', timestamp_str, re.IGNORECASE)
    if match:
        days = int(match.group(1))
        return now - timedelta(days=days)
    
    # Format: "1w", "2w" or "1 uke", "2 uker" (weeks ago)
    match = re.match(r'^(\d+)\s*(?:w|uke[r]?)$', timestamp_str, re.IGNORECASE)
    if match:
        weeks = int(match.group(1))
        return now - timedelta(weeks=weeks)
    
    # Format: "Yesterday at 17:48" or "I går kl. 17:48" (Norwegian)
    match = re.match(r'^(?:Yesterday|I går)\s+(?:at|kl\.?)\s+(\d+):(\d+)$', timestamp_str, re.IGNORECASE)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        yesterday = now - timedelta(days=1)
        return yesterday.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Format: "Yesterday" or "I går" (without time)
    if timestamp_str.lower() in ('yesterday', 'i går'):
        return now - timedelta(days=1)
    
    # Format: "24 January at 08:42"
    match = re.match(r'^(\d+)\s+(\w+)\s+at\s+(\d+):(\d+)$', timestamp_str)
    if match:
        day = int(match.group(1))
        month_str = match.group(2)
        hour = int(match.group(3))
        minute = int(match.group(4))
        
        month = MONTHS.get(month_str.lower(), now.month)
        
        # Assume current year, or previous year if the date is in the future
        year = now.year
        try:
            parsed_date = datetime(year, month, day, hour, minute)
            if parsed_date > now:
                # If date is in future, it must be from last year
                parsed_date = datetime(year - 1, month, day, hour, minute)
            return parsed_date
        except ValueError:
            return None
    
    # Format: "5 May 2025" (date with year, no time)
    match = re.match(r'^(\d+)\s+(\w+)\s+(\d{4})$', timestamp_str)
    if match:
        day = int(match.group(1))
        month_str = match.group(2)
        year = int(match.group(3))
        
        month = MONTHS.get(month_str.lower())
        if month:
            try:
                return datetime(year, month, day, 12, 0)  # Default to noon
            except ValueError:
                return None
    
    # Format: "Recently" or unknown - use current time
    if timestamp_str.lower() == 'recently':
        return now - timedelta(minutes=1)
    
    # Unknown format - return None
    return None


if __name__ == "__main__":
    # Test cases
    test_cases = [
        "7h",
        "10h",
        "2d",
        "24 January at 08:42",
        "15 January at 11:23",
        "Recently"
    ]
    
    print("Testing timestamp parser:")
    for ts in test_cases:
        parsed = parse_facebook_timestamp(ts)
        print(f"  '{ts}' -> {parsed}")
