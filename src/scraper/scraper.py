"""Facebook group scraper module."""

from __future__ import annotations

import hashlib
import random
import re
import time
from datetime import datetime, timedelta
from typing import TypedDict

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException


def convert_relative_to_full_timestamp(timestamp_str: str) -> str:
    """
    Convert relative timestamps like '3h', '2d' to full date format.
    Returns the original string if it's already a full timestamp or can't be parsed.
    """
    now = datetime.now()
    timestamp_str = timestamp_str.strip()
    
    # Already a full timestamp (contains month name or date pattern)
    if any(month in timestamp_str.lower() for month in ['january', 'february', 'march', 'april', 
            'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
            'januar', 'februar', 'mars', 'april', 'mai', 'juni', 'juli', 'august',
            'september', 'oktober', 'november', 'desember']):
        return timestamp_str
    
    result_time = None
    
    # Format: "5m", "30m" (minutes ago)
    match = re.match(r'^(\d+)m$', timestamp_str)
    if match:
        minutes = int(match.group(1))
        result_time = now - timedelta(minutes=minutes)
    
    # Format: "7h", "10h" (hours ago)
    if not result_time:
        match = re.match(r'^(\d+)h$', timestamp_str)
        if match:
            hours = int(match.group(1))
            result_time = now - timedelta(hours=hours)
    
    # Format: "2d", "5d" (days ago)
    if not result_time:
        match = re.match(r'^(\d+)d$', timestamp_str)
        if match:
            days = int(match.group(1))
            result_time = now - timedelta(days=days)
    
    # Format: "1w", "2w" (weeks ago)
    if not result_time:
        match = re.match(r'^(\d+)w$', timestamp_str)
        if match:
            weeks = int(match.group(1))
            result_time = now - timedelta(weeks=weeks)
    
    # Handle "Recently", "Just now", etc. — convert to approximate current time
    if not result_time and timestamp_str.strip().lower() in ('recently', 'nylig', 'nettopp', 'just now', 'akkurat nå'):
        result_time = now - timedelta(minutes=1)
    
    # Convert to readable format
    if result_time:
        # Format: "Sunday 01 February 2026 at 19:30"
        return result_time.strftime("%A %d %B %Y at %H:%M")
    
    # Return original if we couldn't parse
    return timestamp_str


class Post(TypedDict):
    """Represents a Facebook post."""
    post_id: str
    title: str
    text: str
    url: str
    timestamp: str
    group_name: str
    group_url: str


KEYWORDS = [
    "kjøre",
    "kjøring",
    "bil",
    "flytte",
    "flytting",
    "transport",
    "sjåfør",
    "fører",
    "førerkort",
    "levering",
    "hente",
    "frakt",
    "flyttejobb",
    "kjøretur",
    "kjoring",
    "sjafoer",
    "forerkort",
]


def click_see_more(driver: WebDriver, parent_element) -> bool:
    """
    Click 'See more' button to expand the full post text.
    Returns True if clicked successfully, False otherwise.
    """
    try:
        see_more_patterns = ["see more", "se mer", "vis mer"]
        
        # Method 1: Find by role="button" with exact text
        buttons = parent_element.find_elements(By.CSS_SELECTOR, "div[role='button'][tabindex='0']")
        for btn in buttons:
            try:
                btn_text = btn.text.strip().lower()
                if btn_text in see_more_patterns:
                    driver.execute_script("arguments[0].click();", btn)
                    return True
            except Exception:
                continue
        
        # Method 2: Find any element with exact "See more" text using XPath
        for pattern in ["See more", "Se mer", "Vis mer"]:
            try:
                xpath = f".//*[normalize-space(text())='{pattern}']"
                elements = parent_element.find_elements(By.XPATH, xpath)
                for elem in elements:
                    try:
                        if elem.is_displayed():
                            driver.execute_script("arguments[0].click();", elem)
                            return True
                    except Exception:
                        continue
            except Exception:
                continue
            
    except Exception:
        pass  # Silently fail - not all posts have "See more"
    
    return False


def is_error_page(driver: WebDriver) -> bool:
    """
    Check if Facebook is showing an error page like 'This page isn't available'.
    """
    try:
        page_source = driver.page_source.lower()
        error_phrases = [
            "this page isn't available",
            "this page isn't available",
            "denne siden er ikke tilgjengelig",
            "technical error",
            "try reloading this page"
        ]
        return any(phrase in page_source for phrase in error_phrases)
    except:
        return False


def click_reload_button(driver: WebDriver) -> bool:
    """
    Click the 'Reload page' button on Facebook error pages.
    Returns True if button was found and clicked, False otherwise.
    """
    try:
        # Method 1: Find by exact aria-label (most reliable)
        try:
            reload_btn = driver.find_element(By.CSS_SELECTOR, "div[aria-label='Reload page'][role='button']")
            driver.execute_script("arguments[0].click();", reload_btn)
            print("    [SORT] Clicked 'Reload page' button")
            time.sleep(1.5)  # Wait for page to reload
            return True
        except:
            pass
        
        # Method 2: Norwegian version
        try:
            reload_btn = driver.find_element(By.CSS_SELECTOR, "div[aria-label='Last inn siden på nytt'][role='button']")
            driver.execute_script("arguments[0].click();", reload_btn)
            print("    [SORT] Clicked 'Reload page' button (Norwegian)")
            time.sleep(1.5)
            return True
        except:
            pass
        
        # Method 3: Find by text content
        buttons = driver.find_elements(By.CSS_SELECTOR, "div[role='button']")
        for btn in buttons:
            try:
                if "reload page" in btn.text.lower() or "last inn siden" in btn.text.lower():
                    driver.execute_script("arguments[0].click();", btn)
                    print("    [SORT] Clicked 'Reload page' button (by text)")
                    time.sleep(1.5)
                    return True
            except:
                continue
        
        # Method 4: Find span with reload text and click its parent button
        spans = driver.find_elements(By.TAG_NAME, "span")
        for span in spans:
            try:
                if span.text.strip().lower() == "reload page":
                    # Find parent button
                    parent = span
                    for _ in range(5):
                        parent = parent.find_element(By.XPATH, "..")
                        if parent.get_attribute("role") == "button":
                            driver.execute_script("arguments[0].click();", parent)
                            print("    [SORT] Clicked 'Reload page' button (via span)")
                            time.sleep(1.5)
                            return True
            except:
                continue
        
        return False
    except Exception as e:
        print(f"    [SORT] Could not find reload button: {str(e)[:30]}")
        return False


def sort_by_new_posts(driver: WebDriver, group_url: str = None, retry_count: int = 0) -> bool:
    """
    Sort the Facebook group feed by 'New posts' instead of 'Most relevant'.
    Returns True if successfully sorted, False otherwise.
    Will reload page and retry if Facebook shows an error page.
    """
    MAX_RETRIES = 3
    
    try:
        # Check if we're on an error page first
        if is_error_page(driver):
            if retry_count < MAX_RETRIES:
                print("    [SORT] Error page detected, reloading...")
                
                # First, try clicking the "Reload page" button
                if not click_reload_button(driver):
                    # If button not found, navigate back to group URL
                    if group_url:
                        driver.get(group_url)
                    else:
                        driver.refresh()
                    time.sleep(1.5)
                
                # Wait for feed to load
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[role='feed']"))
                    )
                    time.sleep(0.5)  # Brief wait for content to load
                except:
                    pass
                return sort_by_new_posts(driver, group_url, retry_count + 1)
            else:
                print("    [SORT] Error page persists after retries")
                return False
        
        # Facebook has a sort dropdown that shows "Most relevant" by default
        # We need to click it and select "New posts"
        
        # Method 1: Look for the sort button with text containing "Most relevant" or "Mest relevant"
        sort_button_texts = ["most relevant", "mest relevant", "mest relevante"]
        
        # Try to find button/span with these texts
        all_clickable = driver.find_elements(By.CSS_SELECTOR, "span, div[role='button']")
        
        sort_button = None
        for elem in all_clickable:
            try:
                elem_text = elem.text.strip().lower()
                if elem_text in sort_button_texts or any(t in elem_text for t in sort_button_texts):
                    sort_button = elem
                    break
            except:
                continue
        
        if not sort_button:
            # Method 2: Try finding by specific Facebook class patterns or aria-labels
            # Facebook uses aria-haspopup="menu" for dropdown buttons
            dropdown_buttons = driver.find_elements(By.CSS_SELECTOR, "[aria-haspopup='menu'], [aria-haspopup='listbox']")
            for btn in dropdown_buttons:
                try:
                    btn_text = btn.text.strip().lower()
                    if any(t in btn_text for t in sort_button_texts):
                        sort_button = btn
                        break
                except:
                    continue
        
        if not sort_button:
            # Method 3: Look in the feed header area for sort controls
            feed = driver.find_element(By.CSS_SELECTOR, "[role='feed']")
            # Look above the feed for sorting controls
            parent = feed
            for _ in range(5):
                try:
                    parent = parent.find_element(By.XPATH, "..")
                except:
                    break
                spans = parent.find_elements(By.TAG_NAME, "span")
                for span in spans:
                    try:
                        span_text = span.text.strip().lower()
                        if span_text in sort_button_texts:
                            # Found it - now we need the clickable parent
                            clickable = span
                            for _ in range(3):
                                try:
                                    clickable = clickable.find_element(By.XPATH, "..")
                                    if clickable.get_attribute("role") == "button" or clickable.tag_name == "div":
                                        sort_button = clickable
                                        break
                                except:
                                    break
                            if sort_button:
                                break
                    except:
                        continue
                if sort_button:
                    break
        
        if not sort_button:
            return False  # Silent fail - don't log to keep output clean
        
        # Click the sort button to open dropdown
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sort_button)
        time.sleep(0.3)  # Wait before clicking
        driver.execute_script("arguments[0].click();", sort_button)
        time.sleep(0.5)  # Wait for dropdown to appear
        
        # Now find and click "New posts" option
        new_posts_texts = ["new posts", "nye innlegg", "nyeste innlegg", "newest", "new"]
        
        # Look for menu items
        menu_items = driver.find_elements(By.CSS_SELECTOR, "[role='menuitem'], [role='menuitemradio'], [role='option']")
        
        new_posts_option = None
        for item in menu_items:
            try:
                item_text = item.text.strip().lower()
                if any(t in item_text for t in new_posts_texts):
                    new_posts_option = item
                    break
            except:
                continue
        
        if not new_posts_option:
            # Try looking for any clickable element with the new posts text
            all_elements = driver.find_elements(By.CSS_SELECTOR, "span, div")
            for elem in all_elements:
                try:
                    elem_text = elem.text.strip().lower()
                    if elem_text in new_posts_texts or any(t == elem_text for t in new_posts_texts):
                        new_posts_option = elem
                        break
                except:
                    continue
        
        if not new_posts_option:
            # Close dropdown by clicking elsewhere
            driver.execute_script("document.body.click();")
            return False
        
        # Click the "New posts" option
        driver.execute_script("arguments[0].click();", new_posts_option)
        print("    [SORT] Sorted by 'New posts'")
        
        # Wait for feed to reload with new sorting
        time.sleep(2.0)
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-rendering-role='story_message']")
                or d.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-preview='message']")
            )
            time.sleep(1.0)  # Extra settle time after content appears
        except Exception:
            time.sleep(2.0)  # Fallback wait if WebDriverWait fails
        
        # Check if error page appeared after clicking
        if is_error_page(driver):
            if retry_count < MAX_RETRIES:
                print("    [SORT] Error page after sort click, reloading...")
                
                # First, try clicking the "Reload page" button
                if not click_reload_button(driver):
                    # If button not found, navigate back to group URL
                    if group_url:
                        driver.get(group_url)
                    else:
                        driver.refresh()
                    time.sleep(1.5)
                
                # Wait for feed to load
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[role='feed']"))
                    )
                    time.sleep(0.5)  # Brief wait for content to load
                except:
                    pass
                return sort_by_new_posts(driver, group_url, retry_count + 1)
            else:
                print("    [SORT] Error page persists after retries")
                return False
        
        return True
        
    except Exception as e:
        return False


def expand_all_see_more(driver: WebDriver) -> int:
    """
    Click ALL 'See more' buttons visible on the page to expand all posts.
    Returns the number of buttons clicked.
    Call this after scrolling and before extracting text.
    """
    clicked = 0
    see_more_patterns = ["see more", "se mer", "vis mer"]
    
    try:
        # Find all buttons with role="button" on the page
        all_buttons = driver.find_elements(By.CSS_SELECTOR, "div[role='button'][tabindex='0']")
        
        for btn in all_buttons:
            try:
                btn_text = btn.text.strip().lower()
                if btn_text in see_more_patterns:
                    driver.execute_script("arguments[0].click();", btn)
                    clicked += 1
            except Exception:
                continue
        
        # No delay needed - JavaScript clicks are synchronous
            
    except Exception:
        pass
    
    return clicked


def get_timestamp_fast(timestamp_element) -> str | None:
    """
    Get timestamp from element quickly without hovering.
    Uses aria-label or text content directly.
    Also checks parent <a> tag's aria-label (Facebook stores full datetime there).
    Relative timestamps are converted by convert_relative_to_full_timestamp() later.
    """
    try:
        # First try aria-label on this element (often has full datetime)
        aria_label = timestamp_element.get_attribute("aria-label")
        if aria_label and 5 < len(aria_label) < 80:
            cleaned = aria_label.rstrip(' ·').strip()
            if cleaned.lower() not in ('recently', 'nylig', 'nettopp', 'just now'):
                return cleaned
        
        # Try title attribute
        title_attr = timestamp_element.get_attribute("title")
        if title_attr and 5 < len(title_attr) < 80:
            cleaned = title_attr.rstrip(' ·').strip()
            if cleaned.lower() not in ('recently', 'nylig', 'nettopp', 'just now'):
                return cleaned
        
        # If this is a span/abbr inside an <a> tag, check the parent <a>'s aria-label
        # Facebook stores the full datetime on the <a> tag, not the inner spans
        try:
            tag_name = timestamp_element.tag_name
            if tag_name in ('span', 'abbr', 'b', 'i', 'em', 'strong'):
                parent = timestamp_element
                for _ in range(4):  # Walk up max 4 levels to find <a>
                    parent = parent.find_element(By.XPATH, "..")
                    if parent.tag_name == 'a':
                        parent_aria = parent.get_attribute("aria-label")
                        if parent_aria and 10 < len(parent_aria) < 80:
                            cleaned = parent_aria.rstrip(' ·').strip()
                            if cleaned.lower() not in ('recently', 'nylig', 'nettopp', 'just now'):
                                return cleaned
                        break
        except Exception:
            pass
        
        # Fall back to text content
        text_content = timestamp_element.text.strip()
        if text_content and len(text_content) < 50:
            return text_content.rstrip(' ·').strip()
        
    except Exception:
        pass
    
    return None


# Vague timestamp strings that should trigger a hover to get the full datetime
_VAGUE_TIMESTAMPS = {'recently', 'nylig', 'nettopp', 'just now', 'akkurat nå'}


def _is_vague_timestamp(ts: str) -> bool:
    """Check if a timestamp string is vague (e.g. 'Recently') and needs hover extraction."""
    return ts.strip().lower() in _VAGUE_TIMESTAMPS


def get_timestamp_with_hover(driver: WebDriver, timestamp_element) -> str | None:
    """
    Get the full datetime by hovering over a timestamp element to reveal Facebook's tooltip.
    Used when the visible text shows 'Recently' or similar vague timestamps.
    
    Facebook displays the full datetime (e.g. 'Sunday 08 February 2026 at 04:15')
    in a tooltip that appears on hover.
    
    Returns the full datetime string, or None if hover didn't reveal it.
    """
    try:
        # Find the best hover target - walk up to the parent <a> tag
        hover_target = timestamp_element
        try:
            parent = timestamp_element
            for _ in range(5):
                if parent.tag_name == 'a':
                    hover_target = parent
                    break
                parent = parent.find_element(By.XPATH, "..")
        except Exception:
            pass
        
        # Scroll element into view so hover works
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", hover_target)
        time.sleep(0.15)
        
        # Hover over the element using ActionChains
        actions = ActionChains(driver)
        actions.move_to_element(hover_target).perform()
        time.sleep(0.7)  # Wait for tooltip to appear
        
        # --- Method 1: aria-describedby on the hovered element points to tooltip ---
        described_by = hover_target.get_attribute("aria-describedby")
        if described_by:
            try:
                tooltip = driver.find_element(By.ID, described_by)
                tooltip_text = tooltip.text.strip()
                if tooltip_text and len(tooltip_text) > 5 and not _is_vague_timestamp(tooltip_text):
                    return tooltip_text
            except Exception:
                pass
        
        # --- Method 2: Find div[role='tooltip'] anywhere on the page ---
        tooltips = driver.find_elements(By.CSS_SELECTOR, "div[role='tooltip']")
        for tooltip in tooltips:
            try:
                tooltip_text = tooltip.text.strip()
                if not tooltip_text or len(tooltip_text) < 5 or _is_vague_timestamp(tooltip_text):
                    continue
                # Verify it looks like a date/time string
                lower = tooltip_text.lower()
                date_indicators = [
                    'january', 'february', 'march', 'april', 'may', 'june',
                    'july', 'august', 'september', 'october', 'november', 'december',
                    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
                    'januar', 'februar', 'mars', 'mai', 'juni',
                    'juli', 'august', 'september', 'oktober', 'november', 'desember',
                    'mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', 'lørdag', 'søndag',
                    'at ', 'kl.', ':'
                ]
                if any(ind in lower for ind in date_indicators):
                    return tooltip_text
            except Exception:
                continue
        
        # --- Method 3: Check if aria-label or title changed after hover ---
        try:
            new_aria = hover_target.get_attribute("aria-label")
            if new_aria and not _is_vague_timestamp(new_aria) and len(new_aria) > 5:
                return new_aria.rstrip(' ·').strip()
        except Exception:
            pass
        
        # --- Method 4: Look for a newly appeared span near the element ---
        try:
            nearby_spans = hover_target.find_elements(By.CSS_SELECTOR, "span")
            for span in nearby_spans:
                try:
                    span_text = span.text.strip()
                    if span_text and len(span_text) > 10 and not _is_vague_timestamp(span_text):
                        lower = span_text.lower()
                        if any(ind in lower for ind in ['at ', 'kl.', ':', 'january', 'february',
                                                         'march', 'april', 'may', 'june', 'july',
                                                         'august', 'september', 'october', 'november',
                                                         'december']):
                            return span_text
                except Exception:
                    continue
        except Exception:
            pass
        
        # Move mouse away to close any tooltip
        try:
            actions.move_by_offset(0, 100).perform()
        except Exception:
            pass
        
    except Exception:
        pass
    
    return None


def scrape_facebook_group(driver: WebDriver, group_url: str, scroll_steps: int = 5) -> list[Post]:
    """
    Scrape posts from a Facebook group.
    Returns a list of all posts with title, text, URL, timestamp, and group info.
    """
    driver.get(group_url)

    try:
        wait = WebDriverWait(driver, 90)  # 90 second timeout for parallel mode
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[role='feed']")))
        wait.until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-rendering-role='story_message']")
            or d.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-preview='message']")
        )
    except TimeoutException:
        print(f"[TIMEOUT] Page failed to load within 90s, skipping...")
        return []

    # Extract group name from page title
    group_name = driver.title.split("|")[0].strip() if "|" in driver.title else "Facebook Group"

    # Sort by "New posts" instead of "Most relevant" before scraping
    sort_by_new_posts(driver, group_url)

    posts_dict: dict[str, Post] = {}

    for scroll_num in range(scroll_steps):
        # Expand all "See more" buttons on visible page before extracting text
        expand_all_see_more(driver)
        
        # Find all post text elements - try multiple selectors
        text_elements = driver.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-rendering-role='story_message']")
        if not text_elements:
            # Fallback selector
            text_elements = driver.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-preview='message']")
        
        for text_element in text_elements:
            try:
                # Get the text (already expanded by expand_all_see_more)
                # Wrap in try/except for stale elements
                try:
                    text = text_element.text.strip()
                except StaleElementReferenceException:
                    # Element was removed from DOM (page updated), skip silently
                    continue
                
                if not text:
                    continue
                
                # Extract title (first line or first 60 chars)
                title_parts = text.split("\n", 1)
                title = title_parts[0][:60] + ("..." if len(title_parts[0]) > 60 else "")
                
                # Try to find the post link and timestamp by traversing up to the article container
                url = group_url
                timestamp = "Recently"
                post_id = "unknown"
                
                try:
                    # Get the parent article element
                    # Facebook's DOM can vary - look for both role="article" and div containers
                    parent = text_element
                    article_found = False
                    
                    for level in range(20):  # Search up to 20 levels
                        parent = parent.find_element(By.XPATH, "..")
                        parent_role = parent.get_attribute("role")
                        parent_tag = parent.tag_name
                        
                        # Debug: show what we're finding (use safe ASCII)
                        # if level < 5:
                        
                        # Check for article role OR a div that contains post links
                        if parent_role == "article":
                            article_found = True
                            all_links = parent.find_elements(By.TAG_NAME, "a")
                            break
                        elif parent_tag == "div" and level >= 3:
                            # After level 3, try to find links in this div
                            # If we find links with post URLs, this is likely our container
                            test_links = parent.find_elements(By.TAG_NAME, "a")
                            if test_links:
                                has_post_link = False
                                for test_link in test_links[:30]:  # Check first 30 links
                                    try:
                                        test_url = test_link.get_attribute("href")
                                        if test_url and "/groups/" in test_url and ("/posts/" in test_url or "/permalink/" in test_url or "story_fbid=" in test_url):
                                            has_post_link = True
                                            break
                                    except:
                                        continue
                                
                                if has_post_link:
                                    article_found = True
                                    all_links = test_links
                                    break
                    
                    if article_found:
                        
                        # Look through all links for post URLs AND timestamp
                        # In Facebook's DOM, the timestamp link IS also a post URL link
                        # The <a> tag shows "7h" / "Recently" as text and has full datetime in aria-label
                        # NOTE: No hovering here — scroll loop must not disrupt lazy-loading
                        _first_post_url = None  # Save the first post URL we find
                        for link in all_links:
                            try:
                                link_url = link.get_attribute("href")
                                if not link_url:
                                    continue
                                
                                # Check if this is a post URL
                                if "/groups/" in link_url and ("/posts/" in link_url or "/permalink/" in link_url or "story_fbid=" in link_url):
                                    url = link_url
                                    if _first_post_url is None:
                                        _first_post_url = link_url  # Remember the first post URL
                                    
                                    # Extract post ID from URL - try multiple patterns
                                    # Numeric IDs: /posts/1234567890
                                    id_match = re.search(r'/posts/(\d+)', url)
                                    if id_match:
                                        post_id = id_match.group(1)
                                    else:
                                        id_match = re.search(r'/permalink/(\d+)', url)
                                        if id_match:
                                            post_id = id_match.group(1)
                                        else:
                                            id_match = re.search(r'story_fbid=(\d+)', url)
                                            if id_match:
                                                post_id = id_match.group(1)
                                            else:
                                                # Handle Facebook's newer pfbid format: /posts/pfbid02xyz...
                                                id_match = re.search(r'/posts/(pfbid\w+)', url)
                                                if id_match:
                                                    post_id = id_match.group(1)
                                                else:
                                                    id_match = re.search(r'/permalink/(pfbid\w+)', url)
                                                    if id_match:
                                                        post_id = id_match.group(1)
                                    
                                    # Also try to extract timestamp from this link's aria-label
                                    # Facebook stores the full datetime on the <a> tag
                                    if timestamp == "Recently" or _is_vague_timestamp(timestamp):
                                        link_aria = link.get_attribute("aria-label")
                                        if link_aria and 10 < len(link_aria) < 80:
                                            cleaned_aria = link_aria.rstrip(' ·').strip()
                                            if not _is_vague_timestamp(cleaned_aria):
                                                timestamp = cleaned_aria
                                        
                                        # Check link text for relative timestamps (7h, 2d, etc.)
                                        if _is_vague_timestamp(timestamp) or timestamp == "Recently":
                                            link_text = link.text.strip()
                                            if link_text and len(link_text) < 30:
                                                ts_fast = get_timestamp_fast(link)
                                                if ts_fast and not _is_vague_timestamp(ts_fast):
                                                    timestamp = ts_fast
                                    
                                    # Stop after finding the first post URL with an ID
                                    if post_id != "unknown":
                                        break
                            except Exception:
                                continue
                        
                        # Ensure url points to the actual post, not the group
                        if url == group_url and _first_post_url:
                            url = _first_post_url
                        
                        # Try dedicated timestamp selectors if still not found
                        # NOTE: No hovering during scroll loop — it disrupts Facebook's lazy-loading.
                        # Timestamps will be resolved via hover in the final collection phase.
                        if _is_vague_timestamp(timestamp) or timestamp == "Recently":
                            try:
                                # Find timestamp links - the <a> tags that link to posts
                                timestamp_links = parent.find_elements(By.CSS_SELECTOR, 
                                    "a[href*='/posts/'], a[href*='permalink']")
                                
                                # Also try broader selectors
                                if not timestamp_links:
                                    timestamp_links = parent.find_elements(By.CSS_SELECTOR, 
                                        "abbr, span.x4k7w5x, span.x1heor9g, a[href*='posts'] span, a[href*='permalink'] span")
                                
                                for elem in timestamp_links:
                                    try:
                                        text_content = elem.text.strip()
                                        
                                        # Check if this looks like a timestamp
                                        if text_content and any(indicator in text_content.lower() 
                                            for indicator in ["min", "m", "h", "t", "d", "w", "hour", "day", "week", 
                                                            "month", "year", ":", "ago", "siden", "timer", "dager",
                                                            "yesterday", "recently", "just now", "january", "february",
                                                            "march", "april", "may", "june", "july", "august",
                                                            "september", "october", "november", "december"]):
                                            
                                            full_datetime = get_timestamp_fast(elem)
                                            if full_datetime and not _is_vague_timestamp(full_datetime):
                                                timestamp = full_datetime
                                                break
                                        
                                        # Also check the title attribute
                                        title_attr = elem.get_attribute("title")
                                        if title_attr and not _is_vague_timestamp(title_attr):
                                            timestamp = title_attr
                                            break
                                            
                                    except Exception:
                                        continue
                            except Exception:
                                pass
                    
                    if not article_found:
                        pass  # Could not find post container
                        
                except Exception:
                    pass  # Could not traverse to article parent
                
                # Generate a deterministic hash-based post_id if URL extraction failed
                if post_id == "unknown":
                    hash_input = f"{group_url}:{text[:200]}"
                    post_id = "h_" + hashlib.md5(hash_input.encode('utf-8')).hexdigest()[:16]
                
                dict_key = post_id
                
                if dict_key not in posts_dict:
                    # Convert relative timestamps to full format before storing
                    full_timestamp = convert_relative_to_full_timestamp(timestamp)
                    
                    posts_dict[dict_key] = Post(
                        post_id=post_id,
                        title=title,
                        text=text,
                        url=url,
                        timestamp=full_timestamp,
                        group_name=group_name,
                        group_url=group_url,
                    )
            except StaleElementReferenceException:
                # Element became stale (page updated), skip silently
                continue
            except Exception as e:
                # Skip posts that can't be parsed (only log non-stale errors briefly)
                if "stale" not in str(e).lower():
                    print(f"    [WARN] Skipped post: {str(e)[:50]}...")
                continue

        # Scroll down to load more posts
        prev_count = len(posts_dict)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait for new content to load (Facebook lazy-loads posts)
        time.sleep(random.uniform(2.0, 3.5))
        
        # Extra wait if no new posts appeared (give Facebook more time)
        if len(posts_dict) == prev_count and scroll_num < scroll_steps - 1:
            time.sleep(1.5)

    # Final collection after scrolling
    # Expand all "See more" buttons before final collection
    expand_all_see_more(driver)
    
    text_elements = driver.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-rendering-role='story_message']")
    if not text_elements:
        text_elements = driver.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-preview='message']")
    
    for text_element in text_elements:
        try:
            # Get the text (already expanded by expand_all_see_more)
            try:
                text = text_element.text.strip()
            except StaleElementReferenceException:
                continue
            
            if not text:
                continue
            
            title_parts = text.split("\n", 1)
            title = title_parts[0][:60] + ("..." if len(title_parts[0]) > 60 else "")
            
            url = group_url
            timestamp = "Recently"
            post_id = "unknown"
            
            try:
                parent = text_element
                article_found = False
                
                for level in range(20):
                    parent = parent.find_element(By.XPATH, "..")
                    parent_role = parent.get_attribute("role")
                    parent_tag = parent.tag_name
                    
                    # Check for article role OR a div that contains post links
                    if parent_role == "article":
                        article_found = True
                        all_links = parent.find_elements(By.TAG_NAME, "a")
                        break
                    elif parent_tag == "div" and level >= 3:
                        # After level 3, try to find links in this div
                        test_links = parent.find_elements(By.TAG_NAME, "a")
                        if test_links:
                            has_post_link = False
                            for test_link in test_links[:30]:
                                try:
                                    test_url = test_link.get_attribute("href")
                                    if test_url and "/groups/" in test_url and ("/posts/" in test_url or "/permalink/" in test_url or "story_fbid=" in test_url):
                                        has_post_link = True
                                        break
                                except:
                                    continue
                            
                            if has_post_link:
                                article_found = True
                                all_links = test_links
                                break
                
                if article_found:
                    # Look through all links for post URLs AND timestamp
                    _hover_candidate_elem = None
                    _first_post_url = None
                    for link in all_links:
                        try:
                            link_url = link.get_attribute("href")
                            if not link_url:
                                continue
                            
                            # Check if this is a post URL
                            if "/groups/" in link_url and ("/posts/" in link_url or "/permalink/" in link_url or "story_fbid=" in link_url):
                                url = link_url
                                if _first_post_url is None:
                                    _first_post_url = link_url
                                
                                # Extract post ID from URL
                                id_match = re.search(r'/posts/(\d+)', url)
                                if id_match:
                                    post_id = id_match.group(1)
                                else:
                                    id_match = re.search(r'/permalink/(\d+)', url)
                                    if id_match:
                                        post_id = id_match.group(1)
                                    else:
                                        id_match = re.search(r'story_fbid=(\d+)', url)
                                        if id_match:
                                            post_id = id_match.group(1)
                                        else:
                                            # Handle Facebook's newer pfbid format
                                            id_match = re.search(r'/posts/(pfbid\w+)', url)
                                            if id_match:
                                                post_id = id_match.group(1)
                                            else:
                                                id_match = re.search(r'/permalink/(pfbid\w+)', url)
                                                if id_match:
                                                    post_id = id_match.group(1)
                                
                                # Also try to extract timestamp from this link's aria-label
                                if timestamp == "Recently" or _is_vague_timestamp(timestamp):
                                    link_aria = link.get_attribute("aria-label")
                                    if link_aria and 10 < len(link_aria) < 80:
                                        cleaned_aria = link_aria.rstrip(' ·').strip()
                                        if not _is_vague_timestamp(cleaned_aria):
                                            timestamp = cleaned_aria
                                    
                                    if _is_vague_timestamp(timestamp) or timestamp == "Recently":
                                        link_text = link.text.strip()
                                        if link_text and len(link_text) < 30:
                                            ts_fast = get_timestamp_fast(link)
                                            if ts_fast and not _is_vague_timestamp(ts_fast):
                                                timestamp = ts_fast
                                            elif link_text and _is_vague_timestamp(link_text):
                                                _hover_candidate_elem = link
                                
                                if post_id != "unknown":
                                    break
                        except Exception:
                            continue
                    
                    # Ensure url points to the actual post, not the group
                    if url == group_url and _first_post_url:
                        url = _first_post_url
                    
                    # Try dedicated timestamp selectors if still not found
                    if _is_vague_timestamp(timestamp) or timestamp == "Recently":
                        try:
                            timestamp_links = parent.find_elements(By.CSS_SELECTOR, 
                                "a[href*='/posts/'], a[href*='permalink']")
                            
                            if not timestamp_links:
                                timestamp_links = parent.find_elements(By.CSS_SELECTOR, 
                                    "abbr, span.x4k7w5x, span.x1heor9g, a[href*='posts'] span, a[href*='permalink'] span")
                            
                            for elem in timestamp_links:
                                try:
                                    text_content = elem.text.strip()
                                    
                                    if text_content and any(indicator in text_content.lower() 
                                        for indicator in ["min", "m", "h", "t", "d", "w", "hour", "day", "week", 
                                                        "month", "year", ":", "ago", "siden", "timer", "dager",
                                                        "yesterday", "recently", "just now", "january", "february",
                                                        "march", "april", "may", "june", "july", "august",
                                                        "september", "october", "november", "december"]):
                                        
                                        full_datetime = get_timestamp_fast(elem)
                                        if full_datetime and not _is_vague_timestamp(full_datetime):
                                            timestamp = full_datetime
                                            break
                                        elif _is_vague_timestamp(text_content):
                                            _hover_candidate_elem = elem
                                    
                                    title_attr = elem.get_attribute("title")
                                    if title_attr and not _is_vague_timestamp(title_attr):
                                        timestamp = title_attr
                                        break
                                        
                                except Exception:
                                    continue
                        except Exception:
                            pass
                    
                    # If we got a vague timestamp, try hovering for full datetime
                    if _is_vague_timestamp(timestamp) and _hover_candidate_elem is not None:
                        hover_result = get_timestamp_with_hover(driver, _hover_candidate_elem)
                        if hover_result:
                            timestamp = hover_result
                        
            except Exception:
                pass
            
            # If we still have a vague timestamp, try one more time from any parent level
            if _is_vague_timestamp(timestamp):
                try:
                    # Go back up the DOM and look for any timestamp-like element
                    search_parent = text_element
                    _fallback_hover_elem = None
                    for _ in range(10):
                        try:
                            search_parent = search_parent.find_element(By.XPATH, "..")
                        except:
                            break
                        
                        # Look for timestamp elements at this level
                        timestamp_candidates = search_parent.find_elements(By.CSS_SELECTOR,
                            "a[href*='posts'], abbr, span[dir='auto']")
                        
                        for elem in timestamp_candidates[:15]:
                            try:
                                elem_text = elem.text.strip()
                                if not elem_text or len(elem_text) > 50:
                                    continue
                                    
                                # Check if this looks like a timestamp
                                time_indicators = ["min", "h", "t", "d", "w", "hour", "day", "week",
                                                  "ago", "siden", "timer", "yesterday", "recently",
                                                  "january", "february", "march", "april", "may", "june",
                                                  "july", "august", "september", "october", "november", "december",
                                                  "at ", ":"]
                                
                                if any(ind in elem_text.lower() for ind in time_indicators):
                                    full_dt = get_timestamp_fast(elem)
                                    if full_dt and not _is_vague_timestamp(full_dt):
                                        timestamp = full_dt
                                        break
                                    elif _is_vague_timestamp(elem_text):
                                        # Remember for hover attempt
                                        _fallback_hover_elem = elem
                                    elif len(elem_text) < 30:
                                        timestamp = elem_text.rstrip(' ·').strip()
                                        break
                            except:
                                continue
                        
                        if not _is_vague_timestamp(timestamp):
                            break
                    
                    # Last resort: hover over the fallback element
                    if _is_vague_timestamp(timestamp) and _fallback_hover_elem is not None:
                        hover_result = get_timestamp_with_hover(driver, _fallback_hover_elem)
                        if hover_result:
                            timestamp = hover_result
                except Exception:
                    pass
            
            # Generate a deterministic hash-based post_id if URL extraction failed
            if post_id == "unknown":
                hash_input = f"{group_url}:{text[:200]}"
                post_id = "h_" + hashlib.md5(hash_input.encode('utf-8')).hexdigest()[:16]
            
            dict_key = post_id
            
            if dict_key not in posts_dict:
                # Convert relative timestamps to full format before storing
                full_timestamp = convert_relative_to_full_timestamp(timestamp)
                
                posts_dict[dict_key] = Post(
                    post_id=post_id,
                    title=title,
                    text=text,
                    url=url,
                    timestamp=full_timestamp,
                    group_name=group_name,
                    group_url=group_url,
                )
            
        except StaleElementReferenceException:
            # Element became stale (page updated), skip silently
            continue
        except Exception as e:
            # Only log non-stale errors briefly
            if "stale" not in str(e).lower():
                print(f"    [WARN] Skipped post: {str(e)[:50]}...")
            continue

    return list(posts_dict.values())


def filter_posts_by_keywords(posts: list[Post], keywords: list[str] | None = None) -> list[Post]:
    """
    Filter posts that match any of the keywords.
    Uses default KEYWORDS if none provided.
    """
    if keywords is None:
        keywords = KEYWORDS

    filtered = []
    for post in posts:
        lower_text = post["text"].lower()
        if any(keyword in lower_text for keyword in keywords):
            filtered.append(post)

    return filtered


def print_posts(posts: list[Post], title: str = "Posts") -> None:
    """Print posts with formatting."""
    print(f"\n{title}: {len(posts)}")
    for idx, post in enumerate(posts, start=1):
        print(f"\n--- Post {idx} ---")
        print(f"Post ID: {post['post_id']}")
        print(f"Title: {post['title']}")
        print(f"Group: {post['group_name']}")
        print(f"Posted: {post['timestamp']}")
        print(f"URL: {post['url']}")
        print(f"\n{post['text']}")


def print_keywords(keywords: list[str] | None = None) -> None:
    """Print the keywords being searched for."""
    if keywords is None:
        keywords = KEYWORDS
    print("\nSearching for posts matching these keywords:")
    print(", ".join(keywords))
    print()
