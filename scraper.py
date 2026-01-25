"""Facebook group scraper module."""

from __future__ import annotations

import random
import re
import time
from typing import TypedDict

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


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


def scrape_facebook_group(driver: WebDriver, group_url: str, scroll_steps: int = 5) -> list[Post]:
    """
    Scrape posts from a Facebook group.
    Returns a list of all posts with title, text, URL, timestamp, and group info.
    """
    driver.get(group_url)
    print("Edge opened with profile folder")
    print("Navigated to group:", group_url)

    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[role='feed']")))
    wait.until(
        lambda d: d.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-rendering-role='story_message']")
        or d.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-preview='message']")
    )

    # Extract group name from page title
    group_name = driver.title.split("|")[0].strip() if "|" in driver.title else "Facebook Group"

    # Random initial pause (1-3 seconds) - simulate human arriving at page
    time.sleep(random.uniform(1.0, 3.0))

    print(f"Scrolling {scroll_steps} times...")

    posts_dict: dict[str, Post] = {}

    for scroll_num in range(scroll_steps):
        # Random pause before reading posts (0.5-2 seconds)
        time.sleep(random.uniform(0.5, 2.0))
        
        # Find all post text elements - try multiple selectors
        text_elements = driver.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-rendering-role='story_message']")
        if not text_elements:
            # Fallback selector
            text_elements = driver.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-preview='message']")
        
        print(f"  Found {len(text_elements)} post elements on this scroll...")
        
        for text_element in text_elements:
            try:
                text = text_element.text.strip()
                
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
                        #     print(f"      DEBUG: Level {level}, tag={parent_tag}, role={parent_role}")
                        
                        # Check for article role OR a div that contains post links
                        if parent_role == "article":
                            article_found = True
                            print(f"      DEBUG: [OK] Found article at level {level}")
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
                                    print(f"      DEBUG: [OK] Found post container (div with post links) at level {level}")
                                    all_links = test_links
                                    break
                    
                    if article_found:
                        print(f"      DEBUG: Found {len(all_links)} links in container")
                        
                        # Look through all links for post URLs
                        for link in all_links:
                            try:
                                link_url = link.get_attribute("href")
                                if not link_url:
                                    continue
                                
                                # Debug: print first few URLs to see what we're getting
                                if all_links.index(link) < 3:
                                    print(f"      DEBUG: Sample URL: {link_url[:100]}...")
                                
                                # Check if this is a post URL
                                if "/groups/" in link_url and ("/posts/" in link_url or "/permalink/" in link_url or "story_fbid=" in link_url):
                                    url = link_url
                                    print(f"      DEBUG: Found post URL: {url}")
                                    
                                    # Extract post ID from URL - try multiple patterns
                                    match = re.search(r'/posts/(\d+)', url)
                                    if match:
                                        post_id = match.group(1)
                                        print(f"      DEBUG: Extracted post_id from /posts/: {post_id}")
                                        break
                                    match = re.search(r'/permalink/(\d+)', url)
                                    if match:
                                        post_id = match.group(1)
                                        print(f"      DEBUG: Extracted post_id from /permalink/: {post_id}")
                                        break
                                    match = re.search(r'story_fbid=(\d+)', url)
                                    if match:
                                        post_id = match.group(1)
                                        print(f"      DEBUG: Extracted post_id from story_fbid: {post_id}")
                                        break
                            except Exception as e:
                                continue
                        
                        # Try to find timestamp - Facebook timestamps are usually in specific locations
                        try:
                            # Facebook uses various selectors for timestamps
                            # Look for abbr tags (often contain time), spans with specific classes, and links
                            time_elements = parent.find_elements(By.CSS_SELECTOR, 
                                "abbr, span.x4k7w5x, span.x1heor9g, a[href*='posts'] span, a[href*='permalink'] span")
                            
                            print(f"      DEBUG: Found {len(time_elements)} potential timestamp elements")
                            
                            for idx, elem in enumerate(time_elements):
                                try:
                                    text_content = elem.text.strip()
                                    
                                    # Debug first few timestamp candidates
                                    if idx < 5:
                                        print(f"      DEBUG: Timestamp candidate {idx}: '{text_content}'")
                                    
                                    # Look for time indicators in multiple languages
                                    if text_content and any(indicator in text_content.lower() 
                                        for indicator in ["min", "m", "h", "t", "d", "w", "hour", "day", "week", 
                                                        "month", "year", ":", "ago", "siden", "timer", "dager"]):
                                        timestamp = text_content
                                        print(f"      DEBUG: [OK] Selected timestamp: '{timestamp}'")
                                        break
                                    
                                    # Also check the title attribute (abbr tags often have full date in title)
                                    title_attr = elem.get_attribute("title")
                                    if title_attr:
                                        print(f"      DEBUG: Found title attribute: '{title_attr}'")
                                        timestamp = title_attr
                                        break
                                        
                                except Exception as e:
                                    continue
                        except Exception as e:
                            print(f"      DEBUG: Error finding timestamp: {e}")
                    
                    if not article_found:
                        pass  # Could not find post container
                        
                except Exception as e:
                    print(f"    Warning: Could not traverse to article parent: {e}")
                
                # Use post_id as key to avoid duplicates, but fallback to text if post_id is unknown
                dict_key = post_id if post_id != "unknown" else text[:100]
                
                if dict_key not in posts_dict:
                    posts_dict[dict_key] = Post(
                        post_id=post_id,
                        title=title,
                        text=text,
                        url=url,
                        timestamp=timestamp,
                        group_name=group_name,
                        group_url=group_url,
                    )
                    print(f"    Captured post: {title} (ID: {post_id})")
                
            except Exception as e:
                # Skip posts that can't be parsed
                print(f"    Error parsing post: {e}")
                continue

        # Scroll down with random behavior
        # Sometimes scroll to bottom, sometimes scroll by random amount (simulate human scrolling)
        if random.random() < 0.7:  # 70% of the time, scroll to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        else:  # 30% of the time, scroll by random amount
            scroll_amount = random.randint(500, 1500)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        
        # Random pause after scrolling (2-5 seconds) - simulate human reading
        pause_time = random.uniform(2.0, 5.0)
        print(f"  Scroll {scroll_num + 1}/{scroll_steps} - pausing for {pause_time:.1f}s...")
        time.sleep(pause_time)

    # Final pause before collecting remaining posts (1-2 seconds)
    time.sleep(random.uniform(1.0, 2.0))

    # Final collection after scrolling
    print("\nFinal collection of posts...")
    text_elements = driver.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-rendering-role='story_message']")
    if not text_elements:
        text_elements = driver.find_elements(By.CSS_SELECTOR, "[role='feed'] [data-ad-preview='message']")
    
    for text_element in text_elements:
        try:
            text = text_element.text.strip()
            
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
                    
                    # Try to find timestamp
                    try:
                        time_elements = parent.find_elements(By.CSS_SELECTOR, 
                            "abbr, span.x4k7w5x, span.x1heor9g, a[href*='posts'] span, a[href*='permalink'] span")
                        
                        for elem in time_elements:
                            try:
                                text_content = elem.text.strip()
                                
                                # Look for time indicators in multiple languages
                                if text_content and any(indicator in text_content.lower() 
                                    for indicator in ["min", "m", "h", "t", "d", "w", "hour", "day", "week", 
                                                    "month", "year", ":", "ago", "siden", "timer", "dager"]):
                                    timestamp = text_content
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
            
            dict_key = post_id if post_id != "unknown" else text[:100]
            
            if dict_key not in posts_dict:
                posts_dict[dict_key] = Post(
                    post_id=post_id,
                    title=title,
                    text=text,
                    url=url,
                    timestamp=timestamp,
                    group_name=group_name,
                    group_url=group_url,
                )
            
        except Exception as e:
            print(f"Error parsing post: {e}")
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
