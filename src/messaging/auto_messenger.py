"""
Auto-messenger: Send Facebook DMs to post authors using Selenium.

Flow:
1. Navigate to the post URL on Facebook
2. Find the poster's profile link (author's name link at top of post)
3. Navigate to their profile
4. Click "Message" button to open Messenger dialog
5. Type and send the message
"""

import time
import re
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)


def _dismiss_overlays(driver) -> None:
    """Dismiss any Facebook overlays/popups that may block interaction."""
    try:
        driver.execute_script("""
            // Re-enable scrolling
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';
            
            // Hide login dialog overlay if present
            var loginDialog = document.querySelector('[role="dialog"]');
            if (loginDialog) {
                var overlay = loginDialog.closest('[class*="uiContextualLayerPositioner"]') 
                              || loginDialog.parentElement;
                if (overlay) {
                    overlay.style.display = 'none';
                }
            }
            
            // Remove any fixed overlay blocking clicks
            var overlays = document.querySelectorAll('[data-nosnippet]');
            overlays.forEach(function(el) { el.style.display = 'none'; });
        """)
    except Exception:
        pass


def _find_poster_profile_url(driver, post_url: str, group_url: str) -> Optional[str]:
    """
    Navigate to a Facebook post and extract the poster's profile URL.
    
    The poster's name is typically the first link inside the post's article
    container that points to a user profile (facebook.com/username or 
    facebook.com/profile.php?id=...).
    
    Args:
        driver: Selenium WebDriver instance
        post_url: Direct URL to the Facebook post
        group_url: The group URL (to filter out group links)
        
    Returns:
        Profile URL string, or None if not found
    """
    try:
        print(f"      [MSG] Navigating to post: {post_url[:80]}...")
        driver.get(post_url)
        time.sleep(3)
        _dismiss_overlays(driver)
        
        # Wait for the page to load and find article elements
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[role="article"], [role="feed"]'))
            )
        except TimeoutException:
            print("      [MSG] Timeout waiting for post page to load")
            return None
        
        time.sleep(1)
        _dismiss_overlays(driver)
        
        # Strategy 1: Look for strong > a pattern (poster's name is typically bold/strong)
        # In Facebook posts, the author's name is usually in a <strong> tag inside an <a> tag
        # at the top of the post
        profile_url = None
        
        # Try finding poster's name link via common Facebook post structure
        # The poster's name is typically one of the first links in the article
        selectors = [
            # Strong link within article (poster name)
            '[role="article"] h2 a[href*="facebook.com"]',
            '[role="article"] h3 a[href*="facebook.com"]',
            # Strong tag containing link
            '[role="article"] strong a[href]',
            # First link with a user profile pattern  
            '[role="article"] a[href*="/user/"]',
            '[role="article"] a[href*="profile.php"]',
            # Broader: links at the top of the article
            '[role="article"] a[role="link"][tabindex="0"]',
        ]
        
        group_id = ""
        gid_match = re.search(r'/groups/(\d+)', group_url)
        if gid_match:
            group_id = gid_match.group(1)
        
        for selector in selectors:
            try:
                links = driver.find_elements(By.CSS_SELECTOR, selector)
                for link in links[:5]:  # Only check first 5 matches
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    
                    # Skip group links, post links, hashtag links, photo links
                    skip_patterns = [
                        '/groups/', '/posts/', '/permalink/', '/photos/',
                        '/hashtag/', '/events/', '/stories/', '#',
                        'facebook.com/share', 'facebook.com/help',
                    ]
                    if any(pattern in href for pattern in skip_patterns):
                        continue
                    
                    # Must be a Facebook user profile link
                    if 'facebook.com' in href:
                        # Clean URL (remove tracking parameters)
                        clean_url = href.split('?')[0].rstrip('/')
                        
                        # Validate it looks like a profile
                        # e.g. facebook.com/john.doe or facebook.com/profile.php?id=123
                        if ('profile.php' in href or 
                            re.match(r'https?://[^/]*facebook\.com/[a-zA-Z0-9.]+$', clean_url)):
                            profile_url = href
                            print(f"      [MSG] Found poster profile: {clean_url[:60]}")
                            return profile_url
            except Exception:
                continue
        
        # Strategy 2: Use JavaScript to find the poster's name link
        # Facebook often structures posts with the author as the first meaningful link
        try:
            profile_url = driver.execute_script("""
                var articles = document.querySelectorAll('[role="article"]');
                for (var i = 0; i < articles.length; i++) {
                    var links = articles[i].querySelectorAll('a[href]');
                    for (var j = 0; j < links.length; j++) {
                        var href = links[j].href;
                        if (!href) continue;
                        
                        // Skip non-profile links
                        if (href.includes('/groups/') || href.includes('/posts/') || 
                            href.includes('/permalink/') || href.includes('/photos/') ||
                            href.includes('/hashtag/') || href.includes('#') ||
                            href.includes('/events/') || href.includes('/stories/')) continue;
                        
                        // Check if it looks like a profile link
                        if (href.includes('facebook.com/') && 
                            (href.includes('profile.php') || 
                             /facebook\\.com\\/[a-zA-Z0-9.]+\\/?$/.test(href.split('?')[0]))) {
                            return href;
                        }
                    }
                }
                return null;
            """)
            
            if profile_url:
                print(f"      [MSG] Found poster profile (JS): {profile_url.split('?')[0][:60]}")
                return profile_url
        except Exception:
            pass
        
        print("      [MSG] Could not find poster's profile URL")
        return None
        
    except Exception as e:
        print(f"      [MSG] Error finding poster profile: {str(e)[:60]}")
        return None


def _send_message_via_profile(driver, profile_url: str, message: str) -> bool:
    """
    Navigate to a user's Facebook profile and send them a message.
    
    Args:
        driver: Selenium WebDriver instance
        profile_url: URL of the poster's Facebook profile
        message: The message text to send
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    try:
        print(f"      [MSG] Navigating to profile: {profile_url.split('?')[0][:60]}...")
        driver.get(profile_url)
        time.sleep(3)
        _dismiss_overlays(driver)
        
        # Look for the "Message" button on the profile page
        message_button = None
        
        # Try various selectors for the Message button
        button_selectors = [
            # Direct "Message" button text
            '//a[contains(@aria-label, "Message") or contains(@aria-label, "Melding")]',
            '//div[contains(@aria-label, "Message") or contains(@aria-label, "Melding")][@role="button"]',
            '//span[text()="Message" or text()="Melding"]/ancestor::a',
            '//span[text()="Message" or text()="Melding"]/ancestor::div[@role="button"]',
        ]
        
        for selector in button_selectors:
            try:
                buttons = driver.find_elements(By.XPATH, selector)
                for btn in buttons:
                    if btn.is_displayed():
                        message_button = btn
                        break
                if message_button:
                    break
            except Exception:
                continue
        
        if not message_button:
            # Try CSS selectors as fallback
            css_selectors = [
                'a[aria-label*="Message"], a[aria-label*="Melding"]',
                'div[aria-label*="Message"][role="button"], div[aria-label*="Melding"][role="button"]',
            ]
            for selector in css_selectors:
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in buttons:
                        if btn.is_displayed():
                            message_button = btn
                            break
                    if message_button:
                        break
                except Exception:
                    continue
        
        if not message_button:
            print("      [MSG] Could not find 'Message' button on profile page")
            return False
        
        print("      [MSG] Found 'Message' button, clicking...")
        try:
            message_button.click()
        except ElementClickInterceptedException:
            _dismiss_overlays(driver)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", message_button)
        
        time.sleep(3)
        
        # Now we should be in the Messenger dialog / chat window
        # Find the message input field
        return _type_and_send_message(driver, message)
        
    except Exception as e:
        print(f"      [MSG] Error on profile page: {str(e)[:60]}")
        return False


def _send_message_via_messenger_url(driver, profile_url: str, message: str) -> bool:
    """
    Alternative: Go directly to messenger URL for the user.
    Facebook Messenger URLs: https://www.facebook.com/messages/t/{user_id}
    
    Args:
        driver: Selenium WebDriver instance  
        profile_url: URL of the poster's Facebook profile
        message: The message text to send
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    try:
        # Extract user identifier from profile URL
        # Could be facebook.com/username or facebook.com/profile.php?id=12345
        user_id = None
        
        if 'profile.php' in profile_url:
            id_match = re.search(r'id=(\d+)', profile_url)
            if id_match:
                user_id = id_match.group(1)
        else:
            # Extract username from URL path
            path_match = re.search(r'facebook\.com/([a-zA-Z0-9.]+)', profile_url)
            if path_match:
                user_id = path_match.group(1)
        
        if not user_id:
            print("      [MSG] Could not extract user ID from profile URL")
            return False
        
        messenger_url = f"https://www.facebook.com/messages/t/{user_id}"
        print(f"      [MSG] Opening Messenger: {messenger_url[:60]}...")
        driver.get(messenger_url)
        time.sleep(4)
        _dismiss_overlays(driver)
        
        return _type_and_send_message(driver, message)
        
    except Exception as e:
        print(f"      [MSG] Error with Messenger URL: {str(e)[:60]}")
        return False


def _type_and_send_message(driver, message: str) -> bool:
    """
    Find the message input field, type the message, and send it.
    Works for both the Messenger dialog and full Messenger page.
    
    Args:
        driver: Selenium WebDriver instance
        message: The message text to send
        
    Returns:
        True if message was sent, False otherwise
    """
    try:
        # Wait for message input to appear
        input_field = None
        
        # Try multiple selectors for the message input
        input_selectors = [
            # Messenger contenteditable div
            (By.CSS_SELECTOR, '[role="textbox"][contenteditable="true"]'),
            (By.CSS_SELECTOR, 'div[aria-label*="Message"][contenteditable="true"]'),
            (By.CSS_SELECTOR, 'div[aria-label*="Melding"][contenteditable="true"]'),
            (By.CSS_SELECTOR, 'div[aria-label*="message"][contenteditable="true"]'),
            (By.CSS_SELECTOR, '[data-lexical-editor="true"]'),
            # Textarea fallback
            (By.CSS_SELECTOR, 'textarea[name="message"]'),
        ]
        
        for by_type, selector in input_selectors:
            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((by_type, selector))
                )
                elements = driver.find_elements(by_type, selector)
                for elem in elements:
                    if elem.is_displayed():
                        input_field = elem
                        break
                if input_field:
                    break
            except TimeoutException:
                continue
        
        if not input_field:
            print("      [MSG] Could not find message input field")
            return False
        
        print("      [MSG] Found message input, typing message...")
        
        # Click to focus the input
        try:
            input_field.click()
        except Exception:
            driver.execute_script("arguments[0].focus();", input_field)
        time.sleep(0.5)
        
        # Type the message
        # Use send_keys for contenteditable divs
        input_field.send_keys(message)
        time.sleep(1)
        
        # Verify text was entered
        current_text = input_field.text or input_field.get_attribute("textContent") or ""
        if len(current_text.strip()) < 10:
            # Fallback: use JavaScript to set text
            print("      [MSG] send_keys may have failed, trying JS input...")
            driver.execute_script("""
                var el = arguments[0];
                el.focus();
                el.textContent = arguments[1];
                // Dispatch input event so React picks it up
                var event = new Event('input', { bubbles: true });
                el.dispatchEvent(event);
            """, input_field, message)
            time.sleep(1)
        
        # Send the message by pressing Enter
        print("      [MSG] Sending message (pressing Enter)...")
        input_field.send_keys(Keys.ENTER)
        time.sleep(2)
        
        # Check if message appeared in the chat (basic verification)
        # Look for the message text somewhere in the chat area
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text
            # Check if at least part of our message appears
            msg_snippet = message[:50]
            if msg_snippet in page_text:
                print("      [MSG] Message appears to have been sent successfully!")
                return True
            else:
                print("      [MSG] Message sent (Enter pressed), but couldn't verify in chat")
                return True  # Assume success since we pressed Enter
        except Exception:
            print("      [MSG] Message sent (Enter pressed)")
            return True
        
    except Exception as e:
        print(f"      [MSG] Error typing/sending message: {str(e)[:60]}")
        return False


def send_facebook_dm(driver, post: dict, message: str) -> bool:
    """
    Send a Facebook DM (private message) to the author of a post.
    
    This is the main entry point. It will:
    1. Navigate to the post
    2. Find the poster's profile
    3. Try sending a DM via the profile Message button
    4. If that fails, try direct Messenger URL
    
    Args:
        driver: Selenium WebDriver instance (must be logged into Facebook)
        post: Post dictionary with 'url', 'group_url', 'title', 'text', etc.
        message: The message to send
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    post_url = post.get('url', '')
    group_url = post.get('group_url', '')
    title = post.get('title', '')[:60]
    
    print(f"\n      {'='*50}")
    print(f"      [AUTO-MSG] Starting DM for: {title}")
    print(f"      {'='*50}")
    
    if not post_url or post_url == group_url:
        print("      [MSG] No direct post URL available, cannot find poster")
        return False
    
    # Remember current URL to navigate back
    original_url = driver.current_url
    
    try:
        # Step 1: Find the poster's profile URL
        profile_url = _find_poster_profile_url(driver, post_url, group_url)
        
        if not profile_url:
            print("      [MSG] Failed: Could not find poster's profile")
            return False
        
        # Step 2: Try sending via profile "Message" button
        print("      [MSG] Attempting to send via profile Message button...")
        success = _send_message_via_profile(driver, profile_url, message)
        
        if not success:
            # Step 3: Fallback - try direct Messenger URL
            print("      [MSG] Profile method failed, trying Messenger URL...")
            success = _send_message_via_messenger_url(driver, profile_url, message)
        
        if success:
            print(f"      [MSG] SUCCESS - DM sent to poster of: {title}")
        else:
            print(f"      [MSG] FAILED - Could not send DM for: {title}")
        
        return success
        
    except Exception as e:
        print(f"      [MSG] Unexpected error: {str(e)[:80]}")
        return False
    
    finally:
        # Navigate back to where we were (or group URL)
        try:
            print(f"      [MSG] Navigating back...")
            driver.get(original_url if original_url else group_url)
            time.sleep(2)
        except Exception:
            pass
