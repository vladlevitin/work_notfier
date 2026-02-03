"""Facebook Work Notifier - Main entry point."""

from __future__ import annotations

import os
import time
import signal
import sys
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
from src.ai.ai_processor import is_service_request, is_driving_job, process_post_with_ai
from config.settings import load_facebook_groups, KEYWORDS

# =============================================================================
# CONFIGURATION TOGGLES
# =============================================================================
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "0"))  # Default: 0 = loop immediately
CLEAR_DATABASE_ON_START = True   # Set to False to keep existing posts
MAX_POST_AGE_HOURS = 24  # Only notify for posts within this many hours
PARALLEL_SCRAPE_WORKERS = int(os.getenv("PARALLEL_SCRAPE_WORKERS", "3"))  # Number of parallel browser instances
# =============================================================================

# Thread-safe print lock
print_lock = threading.Lock()


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
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    print("\n\n[!] Shutdown requested. Finishing current cycle...")
    shutdown_requested = True


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
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'OK' if you can read this."}],
            max_tokens=5
        )
        
        if response.choices and response.choices[0].message.content:
            print("[OK] OpenAI API key verified - connection successful!")
            return True
        else:
            print("[WARNING] OpenAI API returned empty response")
            return False
            
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
    Used for parallel scraping.
    Returns stats about this group's scrape.
    """
    from selenium.common.exceptions import InvalidSessionIdException
    
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
        # Create browser for this thread
        driver = create_driver()
        
        with print_lock:
            print(f"\n[{group_idx}/{total_groups}] {group_name[:50]}")
            print(f"    Scraping...", end=" ", flush=True)
        
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
            print(f"found {result['scraped']}", end="")
            if unknown_count > 0 or existing_count > 0:
                print(f" (skip: {unknown_count} unknown, {existing_count} in DB)", end="")
            print(f" -> {len(posts)} new")
        
        # Check for moving/transport jobs and send immediate emails
        notified_count = 0
        if posts and openai_ok:
            with print_lock:
                print(f"    [{group_name[:20]}] Checking for transport jobs...")
            
            for post in posts:
                if not is_post_recent(post, MAX_POST_AGE_HOURS, log_skip=False):
                    continue
                
                title = post.get('title', '')
                text = post.get('text', '')
                
                if is_driving_job(title, text):
                    post["category"] = "Transport / Moving"
                    with print_lock:
                        print(f"    [{group_name[:20]}] TRANSPORT JOB! Sending email...")
                    send_email_notification([post], group_url)
                    mark_as_notified([post["post_id"]])
                    notified_count += 1
        
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
                print(f"    [{group_name[:20]}] Saved {new_count} posts")
        
    except InvalidSessionIdException as e:
        result["error"] = "browser_crashed"
        with print_lock:
            print(f"    [{group_name[:20]}] Browser crashed!")
    except Exception as e:
        result["error"] = str(e)[:100]
        with print_lock:
            print(f"    [{group_name[:20]}] Error: {str(e)[:50]}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    return result


def run_scrape_cycle_parallel(facebook_groups: list, openai_ok: bool, cycle_num: int) -> dict:
    """
    Run a scrape cycle with parallel browser instances (one per group).
    Returns stats about the cycle.
    """
    cycle_start = datetime.now()
    workers = min(PARALLEL_SCRAPE_WORKERS, len(facebook_groups))
    
    print(f"\n{'='*80}")
    print(f"CYCLE {cycle_num} | {cycle_start.strftime('%H:%M:%S')} | {len(facebook_groups)} groups | {workers} parallel workers")
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
    
    # Submit all groups to thread pool
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for idx, group_config in enumerate(facebook_groups, 1):
            if shutdown_requested:
                break
            future = executor.submit(
                scrape_single_group,
                group_config,
                idx,
                len(facebook_groups),
                openai_ok
            )
            futures[future] = group_config['name']
        
        # Collect results as they complete
        for future in as_completed(futures):
            if shutdown_requested:
                break
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
                    print(f"    [ERROR] {futures[future]}: {str(e)[:50]}")
    
    # Display cycle results
    cycle_duration = (datetime.now() - cycle_start).total_seconds()
    print(f"\n{'='*80}")
    print(f"CYCLE {cycle_num} COMPLETE | {cycle_duration:.0f}s | {workers} parallel workers")
    print(f"{'='*80}")
    print(f"  Scraped: {total_stats['scraped']:>4} posts from {len(facebook_groups)} groups")
    print(f"  Skipped: {total_stats['skipped_unknown']:>4} unknown ID | {total_stats['skipped_existing']:>4} already in DB | {total_stats['skipped_offers']:>4} service offers")
    print(f"  Saved:   {total_stats['new_saved']:>4} new posts to database")
    if total_stats['notified']:
        print(f"  Emails:  {total_stats['notified']:>4} notifications sent")
    if total_stats['errors']:
        print(f"  Errors:  {total_stats['errors']:>4} groups failed")
    
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
        # IMMEDIATE EMAIL CHECK - Before any other processing!
        # Check each new post for moving/transport and email RIGHT AWAY
        # ==========================================================================
        if posts and openai_ok:
            print(f"    Checking {len(posts)} posts for moving/transport jobs...")
            for post in posts:
                # Only check recent posts
                if not is_post_recent(post, MAX_POST_AGE_HOURS, log_skip=False):
                    print(f"    [SKIP] Too old: {post.get('title', '')[:40]}...")
                    continue
                
                # Check if it's a moving/transport job
                title = post.get('title', '')
                text = post.get('text', '')
                print(f"    [CHECK] {title[:50]}...", end=" ", flush=True)
                
                if is_driving_job(title, text):
                    print(f"-> YES! TRANSPORT JOB DETECTED!")
                    # Set category before sending email
                    post["category"] = "Transport / Moving"
                    print(f"    [EMAIL] To: vladislavlevitin1999@gmail.com")
                    print(f"    [EMAIL] Subject: Transport / Moving | {post.get('timestamp', 'Unknown')} | {title[:40]}...")
                    send_email_notification([post], group_url)
                    mark_as_notified([post["post_id"]])
                    new_relevant_posts.append(post)
                    print(f"    [EMAIL] Sent successfully!")
                else:
                    print(f"-> No (not moving/transport)")
        # ==========================================================================
        
        # Only run AI filtering on new posts
        offers_count = 0
        if openai_ok and posts:
            print(f"    AI filtering...", end=" ", flush=True)
            filtered_posts = []
            
            for post in posts:
                if is_service_request(post.get('title', ''), post.get('text', '')):
                    filtered_posts.append(post)
                else:
                    offers_count += 1
            
            skipped_offers += offers_count
            posts = filtered_posts
            print(f"kept {len(posts)} requests, removed {offers_count} offers")
        
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


def main() -> int:
    """Main function to run the Facebook work notifier in continuous loop."""
    global shutdown_requested
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Display start info
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*80)
    print("FACEBOOK WORK NOTIFIER - CONTINUOUS MONITORING MODE")
    print(f"Started: {timestamp}")
    print(f"Scrape interval: {SCRAPE_INTERVAL_MINUTES} minutes")
    print(f"Parallel workers: {PARALLEL_SCRAPE_WORKERS}")
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
    parallel_mode = PARALLEL_SCRAPE_WORKERS > 1
    
    driver = None
    if not parallel_mode:
        # Create single browser driver for sequential mode
        print("\n[*] Starting browser (sequential mode)...")
        driver = create_driver()
    else:
        print(f"\n[*] Parallel mode enabled - {PARALLEL_SCRAPE_WORKERS} browsers per cycle")
    
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
            
            if parallel_mode:
                # Run parallel scrape cycle (creates its own browser instances)
                stats = run_scrape_cycle_parallel(facebook_groups, openai_ok, cycle_num)
            else:
                # Run sequential scrape cycle with single browser
                stats = run_scrape_cycle(driver, facebook_groups, openai_ok, cycle_num)
                
                # Check if browser crashed and needs restart
                if stats.get("browser_crashed"):
                    print("[*] Restarting browser...")
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = create_driver()
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
        if driver:
            print("\n[*] Closing browser...")
            driver.quit()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
        sys.exit(0)
