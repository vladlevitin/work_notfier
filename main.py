"""Facebook Work Notifier - Main entry point."""

from __future__ import annotations

import os
import time
import signal
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from dotenv import load_dotenv
load_dotenv()

# Import from new structure
from src.scraper import scrape_facebook_group, filter_posts_by_keywords, print_posts
from monitor import create_driver
from src.database import save_posts, mark_as_notified, post_exists
from src.notifications import send_email_notification
from src.ai.ai_processor import is_service_request, is_driving_job, is_manual_labor_job, process_post_with_ai
from config.settings import load_facebook_groups, KEYWORDS


def close_scraper_edge_instances() -> None:
    """
    Close only Edge browser instances that are using THIS project's edge_profile folder.
    
    Uses the same approach as tinder_automation: PowerShell + Get-CimInstance to find
    Edge processes with matching --user-data-dir flag, then Stop-Process to close them.
    
    ONLY closes instances where --user-data-dir matches this project's edge_profile path.
    Leaves ALL other Edge browser windows open (personal browsing, other projects).
    """
    if sys.platform != "win32":
        return
    
    try:
        import re
        
        # Get the EXACT path to THIS project's edge_profile folder
        script_dir = Path(__file__).resolve().parent
        user_data_dir = str(script_dir / "edge_profile")
        
        # Escape for regex in PowerShell
        udd_pat = re.escape(user_data_dir)
        
        # PowerShell script to find and kill Edge processes with matching --user-data-dir
        # Same approach as tinder_automation's _force_close_edge_profile()
        ps_script = rf"""
$ErrorActionPreference = 'SilentlyContinue'
$procs = Get-CimInstance Win32_Process -Filter "Name='msedge.exe'"
$killed = 0
foreach ($p in $procs) {{
  $cmd = $p.CommandLine
  if ([string]::IsNullOrWhiteSpace($cmd)) {{ continue }}
  if ($cmd -match '--user-data-dir="?{udd_pat}"?') {{
    try {{
      Stop-Process -Id $p.ProcessId -Force
      $killed++
    }} catch {{ }}
  }}
}}
Write-Output $killed
"""
        
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # Parse killed count from output
        killed_str = (result.stdout or "").strip().splitlines()[-1] if (result.stdout or "").strip() else "0"
        try:
            killed_count = int(killed_str)
        except Exception:
            killed_count = 0
        
        # Also kill msedgedriver.exe processes (these are only from automation)
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", 
             "Get-Process msedgedriver -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if killed_count > 0:
            print(f"[CLEANUP] Closed {killed_count} scraper Edge instance(s)")
        else:
            print("[CLEANUP] No scraper Edge instances to close")
        
        # Small delay to ensure processes are fully terminated
        time.sleep(0.5)
        
    except Exception as e:
        print(f"[CLEANUP] Could not check Edge instances: {e}")


# =============================================================================
# CONFIGURATION TOGGLES
# =============================================================================
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "0"))  # Default: 0 = loop immediately
CLEAR_DATABASE_ON_START = True   # Set to False to keep existing posts
MAX_POST_AGE_HOURS = 24  # Only notify for posts within this many hours
PARALLEL_MODE = False  # False = one browser, loop through groups one by one
PERSISTENT_BROWSERS = False  # Not used in sequential mode
MAX_PARALLEL_BROWSERS = 9  # Not used in sequential mode
# =============================================================================

# Thread-safe print lock for parallel mode
print_lock = threading.Lock()

# Global persistent browser pool: {group_idx: driver}
persistent_drivers = {}

# Global reference to current sequential-mode driver (so cleanup can close it on exit/kill)
_current_driver = None


def is_post_recent(post: dict, max_hours: int = 24, log_skip: bool = True) -> bool:
    """
    Check if a post is within the specified time window.
    Returns True if the post is recent enough to process.
    
    Args:
        post: Post dictionary with timestamp field
        max_hours: Maximum age in hours (default 24 = 1 day)
        log_skip: Whether to print a message when skipping old posts
    """
    from src.scraper.timestamp_parser import parse_facebook_timestamp
    
    timestamp_str = post.get("timestamp", "")
    if not timestamp_str:
        return False
    
    try:
        post_time = parse_facebook_timestamp(timestamp_str)
        if not post_time:
            return False
        
        cutoff_time = datetime.now() - timedelta(hours=max_hours)
        is_recent = post_time >= cutoff_time
        
        if not is_recent and log_skip:
            # Log skipped old post
            age_hours = (datetime.now() - post_time).total_seconds() / 3600
            print(f"    [SKIP] Post too old ({age_hours:.0f}h): {post.get('title', '')[:40]}...")
        
        return is_recent
    except Exception:
        # If we can't parse the timestamp, skip it to be safe
        return False

# Global flag for graceful shutdown
shutdown_requested = False


def clear_database() -> int:
    """Clear all posts from the database. Returns count of deleted posts."""
    from src.database.supabase_db import supabase
    
    try:
        # Get count before deleting
        count_result = supabase.table("posts").select("*", count="exact", head=True).execute()
        count = count_result.count if count_result.count else 0
        
        if count > 0:
            # Delete all posts
            supabase.table("posts").delete().neq("post_id", "").execute()
            print(f"[DB] Cleared {count} posts from database")
        else:
            print("[DB] Database already empty")
        
        return count
    except Exception as e:
        print(f"[ERROR] Failed to clear database: {e}")
        return 0

def signal_handler(signum, frame):
    """Handle Ctrl+C and other signals: set flag and run cleanup so Edge closes."""
    global shutdown_requested
    shutdown_requested = True
    print("\n\n[!] Shutdown requested. Closing browser...")
    cleanup_on_exit()


def check_openai_api_key() -> bool:
    """Check if OpenAI API key is configured and working."""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("[WARNING] OPENAI_API_KEY not found in environment variables")
        print("         AI-powered categorization will be disabled")
        return False
    
    # Mask the key for display (show first 8 and last 4 chars)
    masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
    print(f"[OK] OpenAI API Key configured: {masked_key}")
    
    # Try a simple API call to verify the key works
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Make a minimal API call to verify the key
        response = client.chat.completions.create(
            model="gpt-5.2-chat-latest",
            messages=[{"role": "user", "content": "Say OK"}],
            max_completion_tokens=10
        )
        
        if response.choices and response.choices[0].message.content:
            print("[OK] OpenAI API key verified - connection successful!")
            return True
        else:
            # Even if empty response, key is valid - just proceed
            print("[OK] OpenAI API key accepted (no content in test response)")
            return True
            
    except Exception as e:
        print(f"[ERROR] OpenAI API key verification failed: {str(e)}")
        return False


def print_scrape_metadata(facebook_groups: list) -> None:
    """Print compact metadata about the scraping configuration."""
    total_groups = len(facebook_groups)
    total_scroll_steps = sum(g.get('scroll_steps', 5) for g in facebook_groups)
    
    print(f"\n[CONFIG] {total_groups} groups | {total_scroll_steps} total scrolls | {len(KEYWORDS)} keywords")
    print(f"[KEYWORDS] {', '.join(KEYWORDS[:8])}{'...' if len(KEYWORDS) > 8 else ''}")


def scrape_single_group(group_config: dict, group_idx: int, total_groups: int, openai_ok: bool) -> dict:
    """
    Scrape a single Facebook group with its own browser instance.
    Runs in a separate thread for parallel scraping.
    Returns stats about this group's scrape.
    """
    group_name = group_config['name']
    group_url = group_config['url']
    scroll_steps = group_config.get('scroll_steps', 5)
    
    result = {
        "group_name": group_name,
        "scraped": 0,
        "new_saved": 0,
        "skipped_existing": 0,
        "skipped_unknown": 0,
        "skipped_offers": 0,
        "notified": 0,
        "error": None
    }
    
    driver = None
    try:
        # Create browser for this thread with unique instance ID
        driver = create_driver(instance_id=group_idx)
        
        with print_lock:
            print(f"[{group_idx}/{total_groups}] {group_name[:40]} - Starting...")
        
        # Scrape the group
        posts = scrape_facebook_group(driver, group_url, scroll_steps=scroll_steps)
        result["scraped"] = len(posts)
        
        # Filter out posts with unknown IDs
        unknown_count = sum(1 for p in posts if p.get('post_id') == 'unknown')
        if unknown_count > 0:
            posts = [p for p in posts if p.get('post_id') != 'unknown']
            result["skipped_unknown"] = unknown_count
        
        # Filter out existing posts
        existing_count = 0
        if posts:
            new_posts_only = []
            for post in posts:
                post_id = post.get('post_id')
                if post_id and post_exists(post_id):
                    existing_count += 1
                else:
                    new_posts_only.append(post)
            result["skipped_existing"] = existing_count
            posts = new_posts_only
        
        with print_lock:
            print(f"[{group_idx}/{total_groups}] {group_name[:40]} - Found {result['scraped']} -> {len(posts)} new")
        
        # Check for moving/transport jobs and send immediate emails
        # This works with keyword matching even if OpenAI is not available
        notified_count = 0
        if posts:
            for post in posts:
                if not is_post_recent(post, MAX_POST_AGE_HOURS, log_skip=False):
                    continue
                
                title = post.get('title', '')
                text = post.get('text', '')
                
                # is_driving_job uses keyword matching first, then AI as fallback
                if is_driving_job(title, text):
                    post["category"] = "Transport / Moving"
                    with print_lock:
                        print(f"[EMAIL] TRANSPORT JOB detected - sending notification...")
                    try:
                        send_email_notification([post], group_url)
                        mark_as_notified([post["post_id"]])
                        notified_count += 1
                        with print_lock:
                            print(f"[EMAIL] Notification sent successfully")
                    except Exception as e:
                        with print_lock:
                            print(f"[EMAIL] Failed to send: {str(e)[:50]}")
        
        result["notified"] = notified_count
        
        # AI filtering for service requests
        offers_count = 0
        if openai_ok and posts:
            filtered_posts = []
            for post in posts:
                if is_service_request(post.get('title', ''), post.get('text', '')):
                    filtered_posts.append(post)
                else:
                    offers_count += 1
            result["skipped_offers"] = offers_count
            posts = filtered_posts
        
        # Filter old posts
        if posts:
            posts = [p for p in posts if is_post_recent(p, MAX_POST_AGE_HOURS, log_skip=False)]
        
        # Categorize with AI
        if openai_ok and posts:
            for post in posts:
                if not post.get("category"):
                    try:
                        ai_result = process_post_with_ai(
                            post.get('title', ''),
                            post.get('text', ''),
                            post.get('post_id', '')
                        )
                        post["category"] = ai_result.get("category", "General")
                        if ai_result.get("location"):
                            post["location"] = ai_result.get("location")
                    except Exception:
                        post["category"] = "General"
        
        # Save to database
        if posts:
            new_count, _ = save_posts(posts)
            result["new_saved"] = new_count
        
        with print_lock:
            print(f"[{group_idx}/{total_groups}] {group_name[:40]} - DONE (saved {result['new_saved']})")
        
    except Exception as e:
        result["error"] = str(e)[:100]
        with print_lock:
            print(f"[{group_idx}/{total_groups}] {group_name[:40]} - ERROR: {str(e)[:40]}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    return result


def prepare_browser_profiles(num_instances: int) -> None:
    """Pre-create browser profile copies for parallel mode."""
    import shutil
    from pathlib import Path
    
    main_profile = Path(__file__).resolve().parent / "edge_profile"
    script_dir = Path(__file__).resolve().parent
    
    # Copy profile to each numbered folder (edge_profile_1, edge_profile_2, etc.)
    def copy_profile(idx):
        instance_dir = script_dir / f"edge_profile_{idx}"
        if instance_dir.exists():
            try:
                shutil.rmtree(instance_dir)
            except:
                pass
        try:
            shutil.copytree(main_profile, instance_dir, dirs_exist_ok=True)
        except:
            instance_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all profiles in parallel
    with ThreadPoolExecutor(max_workers=num_instances) as executor:
        list(executor.map(copy_profile, range(1, num_instances + 1)))


def create_persistent_browsers(facebook_groups: list) -> dict:
    """
    Create persistent browser instances for all groups at startup.
    Returns a dictionary mapping group_idx to driver.
    """
    global persistent_drivers
    
    num_groups = len(facebook_groups)
    print(f"\n[*] Creating {num_groups} persistent browser windows...")
    
    # Prepare profiles first
    prepare_browser_profiles(num_groups)
    
    # Create browsers in parallel
    def create_browser(idx):
        try:
            driver = create_driver(instance_id=idx)
            with print_lock:
                print(f"    [BROWSER {idx}/{num_groups}] Created")
            return (idx, driver)
        except Exception as e:
            with print_lock:
                print(f"    [BROWSER {idx}/{num_groups}] Failed: {str(e)[:30]}")
            return (idx, None)
    
    with ThreadPoolExecutor(max_workers=num_groups) as executor:
        results = list(executor.map(create_browser, range(1, num_groups + 1)))
    
    # Store in global dict
    persistent_drivers = {idx: driver for idx, driver in results if driver is not None}
    
    success_count = len(persistent_drivers)
    print(f"[*] Successfully created {success_count}/{num_groups} browsers")
    
    return persistent_drivers


def close_persistent_browsers() -> None:
    """Close all persistent browser instances."""
    global persistent_drivers
    
    if not persistent_drivers:
        return
    
    print("\n[*] Closing persistent browsers...")
    closed_count = 0
    for idx, driver in persistent_drivers.items():
        try:
            driver.quit()
            closed_count += 1
        except:
            pass
    
    persistent_drivers = {}
    print(f"[*] Closed {closed_count} browser(s)")
    
    # Force-kill any remaining scraper Edge instances
    close_scraper_edge_instances()


def scrape_group_with_persistent_driver(driver, group_config: dict, group_idx: int, total_groups: int, openai_ok: bool, retry_count: int = 0) -> dict:
    """
    Scrape a single Facebook group using an existing persistent browser.
    The driver is NOT closed after scraping.
    Includes retry logic for timeout errors.
    """
    MAX_RETRIES = 2
    group_name = group_config['name']
    group_url = group_config['url']
    scroll_steps = group_config.get('scroll_steps', 5)
    
    result = {
        "group_name": group_name,
        "scraped": 0,
        "new_saved": 0,
        "skipped_existing": 0,
        "skipped_unknown": 0,
        "skipped_offers": 0,
        "notified": 0,
        "error": None
    }
    
    # Small stagger delay based on group index to avoid all hitting at once
    if retry_count == 0:
        stagger_delay = (group_idx - 1) * 0.5  # 0.5 second stagger between groups
        time.sleep(stagger_delay)
    
    try:
        with print_lock:
            retry_msg = f" (retry {retry_count})" if retry_count > 0 else ""
            print(f"[{group_idx}/{total_groups}] {group_name[:40]} - Scraping...{retry_msg}")
        
        # Scrape the group (driver already exists, just navigate)
        posts = scrape_facebook_group(driver, group_url, scroll_steps=scroll_steps)
        result["scraped"] = len(posts)
        
        # Filter out posts with unknown IDs
        unknown_count = sum(1 for p in posts if p.get('post_id') == 'unknown')
        if unknown_count > 0:
            posts = [p for p in posts if p.get('post_id') != 'unknown']
            result["skipped_unknown"] = unknown_count
        
        # Filter out existing posts
        existing_count = 0
        if posts:
            new_posts_only = []
            for post in posts:
                post_id = post.get('post_id')
                if post_id and post_exists(post_id):
                    existing_count += 1
                else:
                    new_posts_only.append(post)
            result["skipped_existing"] = existing_count
            posts = new_posts_only
        
        with print_lock:
            print(f"[{group_idx}/{total_groups}] {group_name[:40]} - Found {result['scraped']} -> {len(posts)} new")
        
        # Check for moving/transport jobs and send immediate emails
        notified_count = 0
        if posts:
            for post in posts:
                if not is_post_recent(post, MAX_POST_AGE_HOURS, log_skip=False):
                    continue
                
                title = post.get('title', '')
                text = post.get('text', '')
                
                if is_driving_job(title, text):
                    post["category"] = "Transport / Moving"
                    with print_lock:
                        print(f"[EMAIL] TRANSPORT JOB detected - sending notification...")
                    try:
                        send_email_notification([post], group_url)
                        mark_as_notified([post["post_id"]])
                        notified_count += 1
                        with print_lock:
                            print(f"[EMAIL] Notification sent successfully")
                    except Exception as e:
                        with print_lock:
                            print(f"[EMAIL] Failed to send: {str(e)[:50]}")
        
        result["notified"] = notified_count
        
        # AI filtering for service requests
        offers_count = 0
        if openai_ok and posts:
            filtered_posts = []
            for post in posts:
                if is_service_request(post.get('title', ''), post.get('text', '')):
                    filtered_posts.append(post)
                else:
                    offers_count += 1
            result["skipped_offers"] = offers_count
            posts = filtered_posts
        
        # Filter old posts
        if posts:
            posts = [p for p in posts if is_post_recent(p, MAX_POST_AGE_HOURS, log_skip=False)]
        
        # Categorize with AI
        if openai_ok and posts:
            for post in posts:
                if not post.get("category"):
                    try:
                        ai_result = process_post_with_ai(
                            post.get('title', ''),
                            post.get('text', ''),
                            post.get('post_id', '')
                        )
                        post["category"] = ai_result.get("category", "General")
                        if ai_result.get("location"):
                            post["location"] = ai_result.get("location")
                    except Exception:
                        post["category"] = "General"
        
        # Save to database
        if posts:
            new_count, _ = save_posts(posts)
            result["new_saved"] = new_count
        
        with print_lock:
            print(f"[{group_idx}/{total_groups}] {group_name[:40]} - DONE (saved {result['new_saved']})")
        
    except Exception as e:
        error_msg = str(e)[:100]
        
        # Check if it's a timeout error and we haven't exceeded retries
        is_timeout = "timeout" in error_msg.lower() or "timed out" in error_msg.lower()
        
        if is_timeout and retry_count < MAX_RETRIES:
            with print_lock:
                print(f"[{group_idx}/{total_groups}] {group_name[:40]} - Timeout, retrying...")
            # Wait a bit before retry
            time.sleep(2)
            # Retry with incremented counter
            return scrape_group_with_persistent_driver(driver, group_config, group_idx, total_groups, openai_ok, retry_count + 1)
        
        result["error"] = error_msg
        with print_lock:
            print(f"[{group_idx}/{total_groups}] {group_name[:40]} - ERROR: {error_msg[:40]}")
    
    # NOTE: Driver is NOT closed here - it stays open for next cycle
    return result


def run_scrape_cycle_persistent(facebook_groups: list, openai_ok: bool, cycle_num: int) -> dict:
    """
    Run a scrape cycle using persistent browsers.
    All groups are scraped simultaneously using their assigned browsers.
    """
    global persistent_drivers
    
    cycle_start = datetime.now()
    num_groups = len(facebook_groups)
    
    print(f"\n{'='*80}")
    print(f"CYCLE {cycle_num} | {cycle_start.strftime('%H:%M:%S')} | {num_groups} groups | PERSISTENT BROWSERS")
    print(f"{'='*80}")
    
    total_stats = {
        "scraped": 0,
        "skipped_existing": 0,
        "skipped_unknown": 0,
        "skipped_offers": 0,
        "new_saved": 0,
        "notified": 0,
        "errors": 0
    }
    
    # Scrape all groups simultaneously using their persistent drivers
    def scrape_with_driver(args):
        idx, group_config = args
        driver = persistent_drivers.get(idx)
        if driver is None:
            return {"error": "No driver available", "group_name": group_config['name']}
        return scrape_group_with_persistent_driver(driver, group_config, idx, num_groups, openai_ok)
    
    # Run all scrapes in parallel
    with ThreadPoolExecutor(max_workers=num_groups) as executor:
        args_list = [(idx, group) for idx, group in enumerate(facebook_groups, 1)]
        results = list(executor.map(scrape_with_driver, args_list))
    
    # Aggregate stats
    for result in results:
        total_stats["scraped"] += result.get("scraped", 0)
        total_stats["skipped_existing"] += result.get("skipped_existing", 0)
        total_stats["skipped_unknown"] += result.get("skipped_unknown", 0)
        total_stats["skipped_offers"] += result.get("skipped_offers", 0)
        total_stats["new_saved"] += result.get("new_saved", 0)
        total_stats["notified"] += result.get("notified", 0)
        if result.get("error"):
            total_stats["errors"] += 1
    
    # Print cycle summary
    cycle_duration = (datetime.now() - cycle_start).seconds
    print(f"\n{'='*80}")
    print(f"CYCLE {cycle_num} COMPLETE | {cycle_duration}s | {num_groups} groups simultaneously")
    print(f"{'='*80}")
    print(f"  Scraped: {total_stats['scraped']:>4} posts from {num_groups} groups")
    print(f"  Skipped: {total_stats['skipped_unknown']:>4} unknown | {total_stats['skipped_existing']:>4} in DB | {total_stats['skipped_offers']:>4} offers")
    print(f"  Saved:   {total_stats['new_saved']:>4} new posts")
    if total_stats["errors"] > 0:
        print(f"  Errors:  {total_stats['errors']:>4} groups failed")
    
    return total_stats


def run_scrape_cycle_parallel(facebook_groups: list, openai_ok: bool, cycle_num: int) -> dict:
    """
    Run a scrape cycle with ALL groups scraped simultaneously.
    Each group gets its own browser window running in a separate thread.
    Returns stats about the cycle.
    """
    cycle_start = datetime.now()
    num_groups = len(facebook_groups)
    
    actual_workers = min(MAX_PARALLEL_BROWSERS, num_groups)
    
    print(f"\n{'='*80}")
    print(f"CYCLE {cycle_num} | {cycle_start.strftime('%H:%M:%S')} | {num_groups} groups | {actual_workers} parallel browsers")
    print(f"{'='*80}")
    
    # Pre-create browser profiles for concurrent instances
    print(f"\n[*] Preparing {actual_workers} browser profiles...")
    prepare_browser_profiles(actual_workers)
    
    print(f"[*] Scraping {num_groups} groups with {actual_workers} concurrent browsers...")
    
    total_stats = {
        "scraped": 0,
        "skipped_existing": 0,
        "skipped_unknown": 0,
        "skipped_offers": 0,
        "new_saved": 0,
        "notified": 0,
        "errors": 0
    }
    
    # Submit groups to thread pool with limited concurrent browsers
    with ThreadPoolExecutor(max_workers=actual_workers) as executor:
        futures = {}
        for idx, group_config in enumerate(facebook_groups, 1):
            if shutdown_requested:
                break
            future = executor.submit(
                scrape_single_group,
                group_config,
                idx,
                num_groups,
                openai_ok
            )
            futures[future] = group_config['name']
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(futures):
            if shutdown_requested:
                break
            completed += 1
            try:
                result = future.result()
                total_stats["scraped"] += result.get("scraped", 0)
                total_stats["skipped_existing"] += result.get("skipped_existing", 0)
                total_stats["skipped_unknown"] += result.get("skipped_unknown", 0)
                total_stats["skipped_offers"] += result.get("skipped_offers", 0)
                total_stats["new_saved"] += result.get("new_saved", 0)
                total_stats["notified"] += result.get("notified", 0)
                if result.get("error"):
                    total_stats["errors"] += 1
            except Exception as e:
                total_stats["errors"] += 1
                with print_lock:
                    print(f"[ERROR] {futures[future]}: {str(e)[:50]}")
    
    # Display cycle results
    cycle_duration = (datetime.now() - cycle_start).total_seconds()
    print(f"\n{'='*80}")
    print(f"CYCLE {cycle_num} COMPLETE | {cycle_duration:.0f}s | {num_groups} groups in parallel")
    print(f"{'='*80}")
    print(f"  Scraped: {total_stats['scraped']:>4} posts from {num_groups} groups")
    print(f"  Skipped: {total_stats['skipped_unknown']:>4} unknown | {total_stats['skipped_existing']:>4} in DB | {total_stats['skipped_offers']:>4} offers")
    print(f"  Saved:   {total_stats['new_saved']:>4} new posts")
    if total_stats['notified']:
        print(f"  Emails:  {total_stats['notified']:>4} notifications sent")
    if total_stats['errors']:
        print(f"  Errors:  {total_stats['errors']:>4} groups failed")
    
    total_stats["duration"] = cycle_duration
    return total_stats


def run_scrape_cycle_multitab(driver, facebook_groups: list, openai_ok: bool, cycle_num: int) -> dict:
    """
    Run a scrape cycle using multiple tabs in a single browser window.
    All pages load in parallel (in separate tabs), then we process each tab sequentially.
    Returns stats about the cycle.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    cycle_start = datetime.now()
    
    print(f"\n{'='*80}")
    print(f"CYCLE {cycle_num} | {cycle_start.strftime('%H:%M:%S')} | {len(facebook_groups)} groups | multi-tab mode")
    print(f"{'='*80}")
    
    total_stats = {
        "scraped": 0,
        "skipped_existing": 0,
        "skipped_unknown": 0,
        "skipped_offers": 0,
        "new_saved": 0,
        "notified": 0,
        "errors": 0
    }
    
    # Store tab handles with their corresponding group configs
    tab_handles = []
    original_handle = driver.current_window_handle
    
    print(f"\n[*] Opening {len(facebook_groups)} tabs...")
    
    # Open all groups in separate tabs
    for idx, group_config in enumerate(facebook_groups):
        if shutdown_requested:
            break
        
        group_url = group_config['url']
        group_name = group_config['name']
        
        try:
            if idx == 0:
                # Use the first (original) tab
                driver.get(group_url)
                tab_handles.append((original_handle, group_config))
            else:
                # Open new tab and navigate
                driver.execute_script(f"window.open('{group_url}', '_blank');")
                # Get the new tab handle (it's the last one)
                new_handle = driver.window_handles[-1]
                tab_handles.append((new_handle, group_config))
            
            print(f"    Tab {idx + 1}: {group_name[:40]}...")
        except Exception as e:
            print(f"    Tab {idx + 1}: FAILED - {str(e)[:30]}")
            total_stats["errors"] += 1
    
    # Wait for pages to load (give them time to load in parallel)
    print(f"\n[*] Waiting for {len(tab_handles)} pages to load...")
    time.sleep(3)  # Initial wait for parallel loading
    
    # Now process each tab
    print(f"\n[*] Processing tabs...")
    
    for idx, (handle, group_config) in enumerate(tab_handles, 1):
        if shutdown_requested:
            break
        
        group_name = group_config['name']
        group_url = group_config['url']
        scroll_steps = group_config.get('scroll_steps', 5)
        
        print(f"\n[{idx}/{len(tab_handles)}] {group_name[:50]}")
        
        try:
            # Switch to this tab
            driver.switch_to.window(handle)
            
            # Wait for feed to be present
            try:
                wait = WebDriverWait(driver, 60)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[role='feed']")))
            except:
                print(f"    [TIMEOUT] Page not loaded, skipping...")
                total_stats["errors"] += 1
                continue
            
            # Import scraper functions for in-tab scraping
            from src.scraper.scraper import sort_by_new_posts, expand_all_see_more
            
            # Sort by new posts
            sort_by_new_posts(driver)
            
            # Get group name from page
            actual_group_name = driver.title.split("|")[0].strip() if "|" in driver.title else group_name
            
            print(f"    Scraping...", end=" ", flush=True)
            
            # Use existing scrape function (it will work on current page)
            posts = scrape_facebook_group(driver, group_url, scroll_steps=scroll_steps)
            scraped_count = len(posts)
            total_stats["scraped"] += scraped_count
            
            # Filter out unknown IDs
            unknown_count = sum(1 for p in posts if p.get('post_id') == 'unknown')
            if unknown_count > 0:
                posts = [p for p in posts if p.get('post_id') != 'unknown']
                total_stats["skipped_unknown"] += unknown_count
            
            # Filter out existing posts
            existing_count = 0
            if posts:
                new_posts_only = []
                for post in posts:
                    post_id = post.get('post_id')
                    if post_id and post_exists(post_id):
                        existing_count += 1
                    else:
                        new_posts_only.append(post)
                total_stats["skipped_existing"] += existing_count
                posts = new_posts_only
            
            print(f"found {scraped_count}", end="")
            if unknown_count > 0 or existing_count > 0:
                print(f" (skip: {unknown_count} unknown, {existing_count} in DB)", end="")
            print(f" -> {len(posts)} new")
            
            # Check for transport jobs and send immediate emails
            if posts and openai_ok:
                for post in posts:
                    if not is_post_recent(post, MAX_POST_AGE_HOURS, log_skip=False):
                        continue
                    
                    title = post.get('title', '')
                    text = post.get('text', '')
                    
                    if is_driving_job(title, text):
                        post["category"] = "Transport / Moving"
                        print(f"    [EMAIL] TRANSPORT JOB! Sending notification...")
                        send_email_notification([post], group_url)
                        mark_as_notified([post["post_id"]])
                        total_stats["notified"] += 1
            
            # AI filtering
            if openai_ok and posts:
                filtered_posts = []
                for post in posts:
                    if is_service_request(post.get('title', ''), post.get('text', '')):
                        filtered_posts.append(post)
                    else:
                        total_stats["skipped_offers"] += 1
                posts = filtered_posts
            
            # Filter old posts
            if posts:
                posts = [p for p in posts if is_post_recent(p, MAX_POST_AGE_HOURS, log_skip=False)]
            
            # Categorize with AI
            if openai_ok and posts:
                for post in posts:
                    if not post.get("category"):
                        try:
                            ai_result = process_post_with_ai(
                                post.get('title', ''),
                                post.get('text', ''),
                                post.get('post_id', '')
                            )
                            post["category"] = ai_result.get("category", "General")
                            if ai_result.get("location"):
                                post["location"] = ai_result.get("location")
                        except Exception:
                            post["category"] = "General"
            
            # Save to database
            if posts:
                new_count, _ = save_posts(posts)
                total_stats["new_saved"] += new_count
                print(f"    Saved {new_count} posts")
            
        except Exception as e:
            print(f"    [ERROR] {str(e)[:50]}")
            total_stats["errors"] += 1
    
    # Close all tabs except the first one
    print(f"\n[*] Closing extra tabs...")
    for handle, _ in tab_handles[1:]:
        try:
            driver.switch_to.window(handle)
            driver.close()
        except:
            pass
    
    # Switch back to the original tab
    try:
        driver.switch_to.window(original_handle)
    except:
        pass
    
    # Display cycle results
    cycle_duration = (datetime.now() - cycle_start).total_seconds()
    print(f"\n{'='*80}")
    print(f"CYCLE {cycle_num} COMPLETE | {cycle_duration:.0f}s | multi-tab mode")
    print(f"{'='*80}")
    print(f"  Scraped: {total_stats['scraped']:>4} posts from {len(facebook_groups)} groups")
    print(f"  Skipped: {total_stats['skipped_unknown']:>4} unknown ID | {total_stats['skipped_existing']:>4} already in DB | {total_stats['skipped_offers']:>4} service offers")
    print(f"  Saved:   {total_stats['new_saved']:>4} new posts to database")
    if total_stats['notified']:
        print(f"  Emails:  {total_stats['notified']:>4} notifications sent")
    if total_stats['errors']:
        print(f"  Errors:  {total_stats['errors']:>4} groups with issues")
    
    total_stats["duration"] = cycle_duration
    return total_stats


def run_scrape_cycle(driver, facebook_groups: list, openai_ok: bool, cycle_num: int) -> dict:
    """
    Run a single scrape cycle through all Facebook groups (sequential mode).
    Returns stats about the cycle.
    """
    cycle_start = datetime.now()
    print(f"\n{'='*80}")
    print(f"CYCLE {cycle_num} | {cycle_start.strftime('%H:%M:%S')} | {len(facebook_groups)} groups | sequential mode")
    print(f"{'='*80}")
    
    all_scraped_posts = []
    all_new_posts = []
    all_relevant_posts = []
    new_relevant_posts = []
    skipped_existing = 0
    skipped_unknown = 0
    skipped_offers = 0

    # Loop through all Facebook groups from config
    for idx, group_config in enumerate(facebook_groups, 1):
        if shutdown_requested:
            print("\n[!] Shutdown requested...")
            break
            
        group_name = group_config['name']
        group_url = group_config['url']
        scroll_steps = group_config.get('scroll_steps', 5)
        
        # Extract group ID for shorter display
        group_id = group_url.split('/groups/')[-1].rstrip('/')
        
        print(f"\n[{idx}/{len(facebook_groups)}] {group_name[:50]}")
        print(f"    Scraping...", end=" ", flush=True)
        
        # Scrape Facebook group - get ALL posts
        try:
            posts = scrape_facebook_group(driver, group_url, scroll_steps=scroll_steps)
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid session" in error_msg or "no such window" in error_msg or "target window" in error_msg:
                print(f"BROWSER CRASHED - restarting...")
                # Return special signal to restart browser
                return {"browser_crashed": True}
            else:
                print(f"ERROR: {str(e)[:50]}")
                continue
        
        scraped_count = len(posts)
        all_scraped_posts.extend(posts)
        
        # Filter out posts with unknown IDs (can't be properly tracked)
        unknown_count = sum(1 for p in posts if p.get('post_id') == 'unknown')
        if unknown_count > 0:
            posts = [p for p in posts if p.get('post_id') != 'unknown']
            skipped_unknown += unknown_count
        
        # EARLY CHECK: Filter out posts that already exist in database
        existing_count = 0
        if posts:
            new_posts_only = []
            for post in posts:
                post_id = post.get('post_id')
                if post_id and post_exists(post_id):
                    existing_count += 1
                else:
                    new_posts_only.append(post)
            skipped_existing += existing_count
            posts = new_posts_only
        
        print(f"found {scraped_count}", end="")
        if unknown_count > 0 or existing_count > 0:
            print(f" (skip: {unknown_count} unknown, {existing_count} in DB)", end="")
        print(f" -> {len(posts)} new")
        
        # ==========================================================================
        # STEP 1: Filter out SERVICE OFFERS first (keep only requests)
        # ==========================================================================
        offers_count = 0
        if openai_ok and posts:
            print(f"    Filtering offers...", end=" ", flush=True)
            filtered_posts = []
            
            for post in posts:
                if is_service_request(post.get('title', ''), post.get('text', '')):
                    filtered_posts.append(post)
                else:
                    offers_count += 1
            
            skipped_offers += offers_count
            posts = filtered_posts
            print(f"kept {len(posts)} requests, removed {offers_count} offers")
        
        # ==========================================================================
        # STEP 2: Check for DRIVING and MANUAL LABOR jobs (email immediately)
        # Only check posts that passed the offer filter
        # ==========================================================================
        if posts and openai_ok:
            print(f"    Checking {len(posts)} posts for jobs...")
            for post in posts:
                # Only check recent posts
                if not is_post_recent(post, MAX_POST_AGE_HOURS, log_skip=False):
                    continue
                
                title = post.get('title', '')
                text = post.get('text', '')
                print(f"    [CHECK] {title[:45]}...", end=" ", flush=True)
                
                # Check for DRIVING job (primary category)
                if is_driving_job(title, text):
                    print(f"-> DRIVING JOB!")
                    post["category"] = "Transport / Moving"
                    print(f"    [EMAIL] Driving job: {title[:50]}...")
                    try:
                        send_email_notification([post], group_url)
                        mark_as_notified([post["post_id"]])
                        new_relevant_posts.append(post)
                        print(f"    [EMAIL] Sent!")
                    except Exception as e:
                        print(f"    [EMAIL] Failed: {str(e)[:30]}")
                
                # Check for MANUAL LABOR job (secondary category)
                elif is_manual_labor_job(title, text):
                    print(f"-> MANUAL LABOR!")
                    post["category"] = "Manual Labor"
                    print(f"    [EMAIL] Manual labor: {title[:50]}...")
                    try:
                        send_email_notification([post], group_url)
                        mark_as_notified([post["post_id"]])
                        new_relevant_posts.append(post)
                        print(f"    [EMAIL] Sent!")
                    except Exception as e:
                        print(f"    [EMAIL] Failed: {str(e)[:30]}")
                else:
                    print(f"-> Other job type")
        # ==========================================================================
        
        # Filter out old posts BEFORE saving (don't save posts older than MAX_POST_AGE_HOURS)
        if posts:
            recent_posts_to_save = []
            old_count = 0
            for post in posts:
                if is_post_recent(post, MAX_POST_AGE_HOURS, log_skip=False):
                    recent_posts_to_save.append(post)
                else:
                    old_count += 1
            
            if old_count > 0:
                print(f"    Filtered {old_count} posts older than {MAX_POST_AGE_HOURS}h")
            posts = recent_posts_to_save
        
        # Categorize all posts with AI before saving (if not already categorized)
        if openai_ok and posts:
            print(f"    Categorizing {len(posts)} posts...", end=" ", flush=True)
            for post in posts:
                if not post.get("category"):  # Only if not already set (e.g., by is_driving_job)
                    try:
                        ai_result = process_post_with_ai(
                            post.get('title', ''),
                            post.get('text', ''),
                            post.get('post_id', '')
                        )
                        post["category"] = ai_result.get("category", "General")
                        if ai_result.get("location"):
                            post["location"] = ai_result.get("location")
                    except Exception:
                        post["category"] = "General"
            print("done")
        
        # Save filtered posts to database IMMEDIATELY
        saved_count = 0
        if posts:
            print(f"    Saving...", end=" ", flush=True)
            new_count, db_skipped_count = save_posts(posts)
            saved_count = new_count
            print(f"saved {new_count} posts")
            
            if new_count > 0:
                all_new_posts.extend(posts[:new_count])
        
        # Note: Email notifications for moving jobs are sent IMMEDIATELY above
        # before any filtering. This section just tracks keyword matches for stats.
        relevant_posts = filter_posts_by_keywords(posts)
        all_relevant_posts.extend(relevant_posts)
        
        # Group summary line
        print(f"    Summary: scraped={scraped_count} | new={len(posts)} | saved={saved_count} | matches={len(relevant_posts)}")
    
    # Display cycle results
    cycle_duration = (datetime.now() - cycle_start).total_seconds()
    print(f"\n{'='*80}")
    print(f"CYCLE {cycle_num} COMPLETE | {cycle_duration:.0f}s")
    print(f"{'='*80}")
    print(f"  Scraped: {len(all_scraped_posts):>4} posts from {len(facebook_groups)} groups")
    print(f"  Skipped: {skipped_unknown:>4} unknown ID | {skipped_existing:>4} already in DB | {skipped_offers:>4} service offers")
    print(f"  Saved:   {len(all_new_posts):>4} new posts to database")
    print(f"  Matches: {len(all_relevant_posts):>4} posts match keywords")
    if new_relevant_posts:
        print(f"  Emails:  {len(new_relevant_posts):>4} notifications sent")
    
    return {
        "scraped": len(all_scraped_posts),
        "skipped_existing": skipped_existing,
        "skipped_unknown": skipped_unknown,
        "skipped_offers": skipped_offers,
        "new_saved": len(all_new_posts),
        "relevant": len(all_relevant_posts),
        "notified": len(new_relevant_posts),
        "duration": cycle_duration
    }


# Global reference to Windows console handler (must not be garbage collected)
_WINDOWS_CONSOLE_HANDLER = None


def _windows_console_handler(ctrl_type: int) -> bool:
    """Windows console control handler: run cleanup when user closes terminal window."""
    # CTRL_C_EVENT=0, CTRL_CLOSE_EVENT=2, CTRL_BREAK_EVENT=1, CTRL_LOGOFF_EVENT=5, CTRL_SHUTDOWN_EVENT=6
    if ctrl_type in (0, 1, 2, 5, 6):
        cleanup_on_exit()
    return False  # Let default handler run (process will exit)


def main() -> int:
    """Main function to run the Facebook work notifier in continuous loop."""
    global shutdown_requested
    
    # Set up signal handler for graceful shutdown (Ctrl+C, etc.)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # On Windows: also run cleanup when user closes the terminal window
    # Same approach as tinder_automation for handling terminal close
    if sys.platform == "win32":
        try:
            global _WINDOWS_CONSOLE_HANDLER
            import ctypes
            kernel32 = ctypes.windll.kernel32  # type: ignore
            # Handler must have signature: BOOL WINAPI HandlerRoutine(DWORD dwCtrlType)
            # Store in global to prevent garbage collection (required for callback to work)
            _WINDOWS_CONSOLE_HANDLER = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)(_windows_console_handler)
            kernel32.SetConsoleCtrlHandler(_WINDOWS_CONSOLE_HANDLER, True)
        except Exception:
            pass
    
    # Close any existing scraper Edge instances to prevent profile lock conflicts
    close_scraper_edge_instances()
    
    # Display start info
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*80)
    print("FACEBOOK WORK NOTIFIER - CONTINUOUS MONITORING MODE")
    print(f"Started: {timestamp}")
    print(f"Scrape interval: {SCRAPE_INTERVAL_MINUTES} minutes")
    if PERSISTENT_BROWSERS and PARALLEL_MODE:
        print("Mode: PERSISTENT (browsers stay open, all groups simultaneously)")
    elif PARALLEL_MODE:
        print("Mode: PARALLEL (browsers open/close each cycle)")
    else:
        print("Mode: Sequential")
    print("Press Ctrl+C to stop gracefully")
    print("="*80)
    
    # Clear database FIRST if toggle is enabled
    if CLEAR_DATABASE_ON_START:
        print("\n" + "="*80)
        print("CLEARING DATABASE - CLEAR_DATABASE_ON_START = True")
        print("="*80)
        clear_database()
    else:
        print("\n[CONFIG] CLEAR_DATABASE_ON_START = False (keeping existing posts)")
    
    # Check OpenAI API key
    print("\n[CONFIG] Checking API keys...")
    openai_ok = check_openai_api_key()
    
    # Load Facebook groups from config
    facebook_groups = load_facebook_groups()
    
    if not facebook_groups:
        print("No enabled Facebook groups found in config/groups.json")
        return 1
    
    # Print detailed metadata before scraping
    print_scrape_metadata(facebook_groups)
    
    # Determine scraping mode
    use_parallel = PARALLEL_MODE
    use_persistent = PERSISTENT_BROWSERS and use_parallel
    
    global _current_driver
    driver = None
    if use_persistent:
        # Create persistent browsers for all groups (stay open between cycles)
        print(f"\n[*] Persistent mode: Creating {len(facebook_groups)} browser windows...")
        create_persistent_browsers(facebook_groups)
    elif use_parallel:
        print(f"\n[*] Parallel mode: {len(facebook_groups)} browser windows will launch per cycle")
    else:
        print("\n[*] Starting browser (sequential mode)...")
        driver = create_driver()
        _current_driver = driver  # So cleanup_on_exit can close it when terminal is killed
    
    cycle_num = 0
    total_stats = {
        "cycles": 0,
        "total_scraped": 0,
        "total_skipped": 0,
        "total_new": 0,
        "total_notified": 0
    }

    try:
        while not shutdown_requested:
            cycle_num += 1
            
            if use_persistent:
                # Run with persistent browsers (all groups simultaneously, browsers stay open)
                stats = run_scrape_cycle_persistent(facebook_groups, openai_ok, cycle_num)
            elif use_parallel:
                # Run parallel scrape cycle (all groups simultaneously in separate windows)
                stats = run_scrape_cycle_parallel(facebook_groups, openai_ok, cycle_num)
            else:
                # Run sequential scrape cycle with single browser
                stats = run_scrape_cycle(driver, facebook_groups, openai_ok, cycle_num)
                
                # Check if browser crashed and needs restart (only in sequential mode)
                if stats.get("browser_crashed"):
                    print("[*] Restarting browser...")
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    _current_driver = None
                    driver = create_driver()
                    _current_driver = driver
                    print("[OK] Browser restarted, continuing...")
                    continue
            
            # Update total stats
            total_stats["cycles"] += 1
            total_stats["total_scraped"] += stats.get("scraped", 0)
            total_stats["total_skipped"] += stats.get("skipped_existing", 0)
            total_stats["total_new"] += stats.get("new_saved", 0)
            total_stats["total_notified"] += stats.get("notified", 0)
            
            if shutdown_requested:
                break
            
            # Wait for next cycle
            next_run = datetime.now().strftime("%H:%M:%S")
            wait_seconds = SCRAPE_INTERVAL_MINUTES * 60
            print(f"\n[WAIT] Next scrape in {SCRAPE_INTERVAL_MINUTES} minutes...")
            print(f"       Current time: {next_run}")
            print(f"       Press Ctrl+C to stop")
            
            # Sleep in small intervals to allow for graceful shutdown
            for _ in range(wait_seconds):
                if shutdown_requested:
                    break
                time.sleep(1)
        
        # Final summary
        print(f"\n{'='*80}")
        print("FINAL SESSION SUMMARY")
        print(f"{'='*80}")
        print(f"  Total cycles completed: {total_stats['cycles']}")
        print(f"  Total posts scraped: {total_stats['total_scraped']}")
        print(f"  Total skipped (already in DB): {total_stats['total_skipped']}")
        print(f"  Total new posts saved: {total_stats['total_new']}")
        print(f"  Total notifications sent: {total_stats['total_notified']}")
        print(f"\n[OK] Graceful shutdown complete.")

    finally:
        # Close browser and scraper Edge instances (idempotent; may already be done by signal/handler)
        if driver is not None:
            try:
                print("\n[*] Closing browser...")
                driver.quit()
            except Exception:
                pass
        _current_driver = None
        cleanup_on_exit()

    return 0


def cleanup_on_exit():
    """Cleanup function called on script exit, Ctrl+C, or terminal close. Closes Edge."""
    global persistent_drivers, _current_driver
    # Close sequential-mode browser if open
    if _current_driver is not None:
        try:
            _current_driver.quit()
        except Exception:
            pass
        _current_driver = None
    # Close persistent browsers if used
    if persistent_drivers:
        close_persistent_browsers()
    # Kill any remaining scraper Edge instances (profile-specific)
    close_scraper_edge_instances()


if __name__ == "__main__":
    import atexit
    atexit.register(cleanup_on_exit)
    
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
        # Clean up persistent browsers on interrupt
        if persistent_drivers:
            close_persistent_browsers()
        # Kill any remaining scraper Edge instances
        close_scraper_edge_instances()
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Unexpected error: {e}")
        # Ensure cleanup on any error
        close_scraper_edge_instances()
        sys.exit(1)
