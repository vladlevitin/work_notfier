"""Parse Facebook timestamp formats to Python datetime."""

import re
from datetime import datetime, timedelta
from typing import Optional


# Map month names to numbers (Norwegian and English)
MONTHS = {
    'january': 1, 'januar': 1,
    'february': 2, 'februar': 2,
    'march': 3, 'mars': 3,
    'april': 4,
    'may': 5, 'mai': 5,
    'june': 6, 'juni': 6,
    'july': 7, 'juli': 7,
    'august': 8,
    'september': 9,
    'october': 10, 'oktober': 10,
    'november': 11,
    'december': 12, 'desember': 12
}


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
    - "Recently"
    
    Args:
        timestamp_str: Facebook timestamp string
    
    Returns:
        datetime object or None if parsing fails
    """
    now = datetime.now()
    timestamp_str = timestamp_str.strip()
    
    # Format: "5m", "30m" (minutes ago)
    match = re.match(r'^(\d+)m$', timestamp_str)
    if match:
        minutes = int(match.group(1))
        return now - timedelta(minutes=minutes)
    
    # Format: "7h", "10h" (hours ago)
    match = re.match(r'^(\d+)h$', timestamp_str)
    if match:
        hours = int(match.group(1))
        return now - timedelta(hours=hours)
    
    # Format: "2d", "5d" (days ago)
    match = re.match(r'^(\d+)d$', timestamp_str)
    if match:
        days = int(match.group(1))
        return now - timedelta(days=days)
    
    # Format: "Yesterday at 17:48"
    match = re.match(r'^Yesterday\s+at\s+(\d+):(\d+)$', timestamp_str, re.IGNORECASE)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        yesterday = now - timedelta(days=1)
        return yesterday.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
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
