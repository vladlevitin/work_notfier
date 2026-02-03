"""Facebook group scraper module."""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from typing import TypedDict

from selenium.webdriver.common.by import By
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
    
    # Convert to readable format
    if result_time:
        # Format: "Sunday 1 February 2026 at 19:30"
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


def sort_by_new_posts(driver: WebDriver) -> bool:
    """
    Sort the Facebook group feed by 'New posts' instead of 'Most relevant'.
    Returns True if successfully sorted, False otherwise.
    """
    try:
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
        driver.execute_script("arguments[0].click();", sort_button)
        time.sleep(0.15)  # Brief wait for dropdown
        
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
        
        # Brief wait for page to refresh with new sorting
        time.sleep(0.3)
        
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
    Relative timestamps are converted by convert_relative_to_full_timestamp() later.
    """
    try:
        # First try aria-label (often has full datetime)
        aria_label = timestamp_element.get_attribute("aria-label")
        if aria_label and 5 < len(aria_label) < 60:
            return aria_label.rstrip(' ·').strip()
        
        # Try title attribute
        title_attr = timestamp_element.get_attribute("title")
        if title_attr and 5 < len(title_attr) < 60:
            return title_attr.rstrip(' ·').strip()
        
        # Fall back to text content
        text_content = timestamp_element.text.strip()
        if text_content and len(text_content) < 50:
            return text_content.rstrip(' ·').strip()
        
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
    sort_by_new_posts(driver)

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
                        elif parent_tag == "div" and level >= 5:
                            # After level 5, try to find links in this div
                            # If we find links with post URLs, this is likely our container
                            test_links = parent.find_elements(By.TAG_NAME, "a")
                            if test_links:
                                has_post_link = False
                                for test_link in test_links[:10]:  # Check first 10 links
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
                        
                        # Look through all links for post URLs
                        for link in all_links:
                            try:
                                link_url = link.get_attribute("href")
                                if not link_url:
                                    continue
                                
                                # Check if this is a post URL
                                if "/groups/" in link_url and ("/posts/" in link_url or "/permalink/" in link_url or "story_fbid=" in link_url):
                                    url = link_url
                                    
                                    # Extract post ID from URL - try multiple patterns
                                    match = re.search(r'/posts/(\d+)', url)
                                    if match:
                                        post_id = match.group(1)
                                        break
                                    match = re.search(r'/permalink/(\d+)', url)
                                    if match:
                                        post_id = match.group(1)
                                        break
                                    match = re.search(r'story_fbid=(\d+)', url)
                                    if match:
                                        post_id = match.group(1)
                                        break
                            except Exception as e:
                                continue
                        
                        # Try to find timestamp - Facebook timestamps are usually in specific locations
                        try:
                            # Facebook uses various selectors for timestamps
                            # First, look for the timestamp link (usually contains time like "7m", "2h", etc.)
                            # These links have hrefs to posts/comments and show full datetime on hover
                            timestamp_links = parent.find_elements(By.CSS_SELECTOR, 
                                "a[href*='posts'][href*='comment_id'], a[href*='permalink']")
                            
                            # Also try broader selectors
                            if not timestamp_links:
                                timestamp_links = parent.find_elements(By.CSS_SELECTOR, 
                                    "abbr, span.x4k7w5x, span.x1heor9g, a[href*='posts'] span, a[href*='permalink'] span")
                            
                            
                            timestamp_found = False
                            for idx, elem in enumerate(timestamp_links):
                                try:
                                    text_content = elem.text.strip()
                                    
                                    # Check if this looks like a relative timestamp (7m, 2h, Yesterday, etc.)
                                    if text_content and any(indicator in text_content.lower() 
                                        for indicator in ["min", "m", "h", "t", "d", "w", "hour", "day", "week", 
                                                        "month", "year", ":", "ago", "siden", "timer", "dager",
                                                        "yesterday", "recently", "just now", "january", "february",
                                                        "march", "april", "may", "june", "july", "august",
                                                        "september", "october", "november", "december"]):
                                        
                                        # Get timestamp quickly without hovering
                                        full_datetime = get_timestamp_fast(elem)
                                        if full_datetime:
                                            timestamp = full_datetime
                                            timestamp_found = True
                                            break
                                        else:
                                            timestamp = text_content.rstrip(' ·').strip()
                                            timestamp_found = True
                                            break
                                    
                                    # Also check the title attribute (abbr tags often have full date in title)
                                    title_attr = elem.get_attribute("title")
                                    if title_attr:
                                        timestamp = title_attr
                                        timestamp_found = True
                                        break
                                        
                                except Exception:
                                    continue
                        except Exception:
                            pass
                    
                    if not article_found:
                        pass  # Could not find post container
                        
                except Exception:
                    pass  # Could not traverse to article parent
                
                # Use post_id as key to avoid duplicates, but fallback to text if post_id is unknown
                dict_key = post_id if post_id != "unknown" else text[:100]
                
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
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Brief pause after scrolling for content to load
        time.sleep(0.4)

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
                    elif parent_tag == "div" and level >= 5:
                        # After level 5, try to find links in this div
                        test_links = parent.find_elements(By.TAG_NAME, "a")
                        if test_links:
                            has_post_link = False
                            for test_link in test_links[:10]:
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
                    # Look through all links for post URLs
                    for link in all_links:
                        try:
                            link_url = link.get_attribute("href")
                            if not link_url:
                                continue
                            
                            # Check if this is a post URL
                            if "/groups/" in link_url and ("/posts/" in link_url or "/permalink/" in link_url or "story_fbid=" in link_url):
                                url = link_url
                                
                                # Extract post ID from URL - try multiple patterns
                                match = re.search(r'/posts/(\d+)', url)
                                if match:
                                    post_id = match.group(1)
                                    break
                                match = re.search(r'/permalink/(\d+)', url)
                                if match:
                                    post_id = match.group(1)
                                    break
                                match = re.search(r'story_fbid=(\d+)', url)
                                if match:
                                    post_id = match.group(1)
                                    break
                        except Exception:
                            continue
                    
                    # Try to find timestamp with hover for full datetime
                    try:
                        timestamp_links = parent.find_elements(By.CSS_SELECTOR, 
                            "a[href*='posts'][href*='comment_id'], a[href*='permalink']")
                        
                        if not timestamp_links:
                            timestamp_links = parent.find_elements(By.CSS_SELECTOR, 
                                "abbr, span.x4k7w5x, span.x1heor9g, a[href*='posts'] span, a[href*='permalink'] span")
                        
                        for elem in timestamp_links:
                            try:
                                text_content = elem.text.strip()
                                
                                # Look for time indicators in multiple languages
                                if text_content and any(indicator in text_content.lower() 
                                    for indicator in ["min", "m", "h", "t", "d", "w", "hour", "day", "week", 
                                                    "month", "year", ":", "ago", "siden", "timer", "dager",
                                                    "yesterday", "recently", "just now", "january", "february",
                                                    "march", "april", "may", "june", "july", "august",
                                                    "september", "october", "november", "december"]):
                                    
                                    # Get timestamp quickly without hovering
                                    full_datetime = get_timestamp_fast(elem)
                                    if full_datetime:
                                        timestamp = full_datetime
                                    else:
                                        timestamp = text_content.rstrip(' ·').strip()
                                    break
                                
                                # Also check the title attribute (abbr tags often have full date in title)
                                title_attr = elem.get_attribute("title")
                                if title_attr:
                                    timestamp = title_attr
                                    break
                                    
                            except Exception:
                                continue
                    except Exception:
                        pass
                        
            except Exception:
                pass
            
            # If we still have "Recently" as timestamp, try one more time from any parent level
            if timestamp == "Recently":
                try:
                    # Go back up the DOM and look for any timestamp-like element
                    search_parent = text_element
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
                                    if full_dt:
                                        timestamp = full_dt
                                        break
                                    elif len(elem_text) < 30:
                                        timestamp = elem_text.rstrip(' ·').strip()
                                        break
                            except:
                                continue
                        
                        if timestamp != "Recently":
                            break
                except Exception:
                    pass
            
            dict_key = post_id if post_id != "unknown" else text[:100]
            
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
