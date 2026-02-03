"""
Continuous monitoring script for Facebook Work Notifier.
Checks groups in cycles and only saves new posts.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

# Import from new structure
from src.scraper import scrape_facebook_group, filter_posts_by_keywords
from src.database import save_post, post_exists, mark_as_notified
from src.notifications import send_email_notification
from config.settings import load_facebook_groups, KEYWORDS

# Configuration
CHECK_INTERVAL_MINUTES = 10  # Wait between cycles (10 minutes recommended for full scrape)
INSTANT_EMAIL_NOTIFICATIONS = True  # Send email for matching new posts immediately


def create_driver(instance_id: int = 0):
    """
    Create and return Edge WebDriver instance with robust Windows configuration.
    
    Args:
        instance_id: Unique ID for this browser instance (used for parallel mode).
                     Each instance gets a copy of the main profile to preserve login.
    """
    import logging
    import os
    import shutil
    
    # Suppress Selenium and WebDriver logging
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    driver_path = Path(__file__).resolve().parent / "edgedriver" / "msedgedriver.exe"
    main_profile = Path(__file__).resolve().parent / "edge_profile"
    
    # Create main profile directory if it doesn't exist
    main_profile.mkdir(parents=True, exist_ok=True)
    
    if instance_id > 0:
        # Parallel mode: use pre-copied profile (prepared by prepare_browser_profiles)
        instance_dir = Path(__file__).resolve().parent / "edge_profiles" / f"instance_{instance_id}"
        
        # Create if not exists (fallback if pre-copy didn't run)
        if not instance_dir.exists():
            instance_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copytree(main_profile, instance_dir, dirs_exist_ok=True)
            except:
                pass
        
        user_data_dir = instance_dir
    else:
        # Sequential mode: use the standard profile directly
        user_data_dir = main_profile
    
    options = Options()
    options.use_chromium = True
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Critical Windows stability flags
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--start-maximized")
    
    # Use unique debugging port for each instance (or skip for parallel to avoid conflicts)
    if instance_id == 0:
        options.add_argument("--remote-debugging-port=9222")
    else:
        # Use dynamic port based on instance ID to avoid conflicts
        debug_port = 9222 + instance_id
        options.add_argument(f"--remote-debugging-port={debug_port}")
    
    # Suppress browser logging/errors
    options.add_argument("--log-level=3")  # Only fatal errors
    options.add_argument("--silent")
    options.add_argument("--disable-logging")
    options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Suppress WebDriver service output
    service = Service(
        executable_path=str(driver_path),
        log_output=os.devnull  # Suppress msedgedriver logs
    )
    
    try:
        driver = webdriver.Edge(service=service, options=options)
        driver.set_page_load_timeout(60)  # Increased timeout for parallel mode
        return driver
    except Exception as e:
        print(f"[ERROR] Failed to start browser: {e}")
        print("[TIP] Make sure Microsoft Edge is installed and up to date")
        raise


def monitor_groups():
    """
    Continuously monitor Facebook groups for new posts.
    Runs in an infinite loop, checking each group in cycles.
    """
    print("\n" + "="*80)
    print("FACEBOOK WORK NOTIFIER - CONTINUOUS MONITORING")
    print("="*80)
    
    # Load enabled groups
    facebook_groups = load_facebook_groups()
    
    if not facebook_groups:
        print("❌ No enabled groups found in config/groups.json")
        return
    
    print(f"\n[*] Monitoring {len(facebook_groups)} enabled groups:")
    for idx, group in enumerate(facebook_groups, 1):
        print(f"  {idx}. {group['name']}")
    
    print(f"\n[*] Check interval: {CHECK_INTERVAL_MINUTES} minutes")
    print(f"[*] Scraping mode: FULL (all posts from each group)")
    print(f"[*] Instant notifications: {'ENABLED' if INSTANT_EMAIL_NOTIFICATIONS else 'DISABLED'}")
    print(f"[*] Monitoring keywords: {', '.join(KEYWORDS[:8])}{'...' if len(KEYWORDS) > 8 else ''}")
    print("\n" + "="*80)
    print("[*] Starting monitoring loop... (Press Ctrl+C to stop)")
    print("="*80)
    
    # Create browser driver once (reuse across cycles)
    print("\n[*] Starting browser...")
    driver = create_driver()
    
    cycle_number = 0
    
    try:
        while True:
            cycle_number += 1
            cycle_start = datetime.now()
            
            print(f"\n{'='*80}")
            print(f"CYCLE #{cycle_number} - {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")
            
            total_scraped = 0
            total_new = 0
            total_existing = 0
            total_notified = 0  # Track instant notifications sent
            
            # Check each enabled group
            for group_idx, group_config in enumerate(facebook_groups, 1):
                group_name = group_config['name']
                group_url = group_config['url']
                scroll_steps = group_config.get('scroll_steps', 5)  # Use config value
                
                print(f"\n[{group_idx}/{len(facebook_groups)}] Scraping: {group_name}")
                print(f"   Scrolls: {scroll_steps}")
                
                try:
                    # Scrape ALL posts from the group (full scrape)
                    posts = scrape_facebook_group(
                        driver, 
                        group_url, 
                        scroll_steps=scroll_steps
                    )
                    
                    total_scraped += len(posts)
                    print(f"   [*] Scraped {len(posts)} posts")
                    
                    # Check and save only NEW posts
                    new_count = 0
                    existing_count = 0
                    notified_count = 0
                    new_posts_to_notify = []  # Collect matching posts for notification
                    
                    for post in posts:
                        # Check if post already exists in database
                        if post_exists(post["post_id"]):
                            existing_count += 1
                        else:
                            # New post! Save it (with AI processing for category/location)
                            if save_post(post, use_ai=True):
                                new_count += 1
                                print(f"   [NEW] {post['title'][:60]}...")
                                
                                # Check if post matches notification criteria (keywords)
                                if INSTANT_EMAIL_NOTIFICATIONS:
                                    matching_posts = filter_posts_by_keywords([post], KEYWORDS)
                                    if matching_posts:
                                        new_posts_to_notify.append(post)
                                        print(f"      [EMAIL] MATCHES CRITERIA - Will notify!")
                    
                    # Send instant email notification for matching posts
                    if INSTANT_EMAIL_NOTIFICATIONS and new_posts_to_notify:
                        try:
                            print(f"\n   [EMAIL] Sending instant notification for {len(new_posts_to_notify)} matching posts...")
                            send_email_notification(new_posts_to_notify, group_url)
                            
                            # Mark as notified
                            post_ids = [p["post_id"] for p in new_posts_to_notify]
                            mark_as_notified(post_ids)
                            
                            notified_count = len(new_posts_to_notify)
                            print(f"   [OK] Email sent successfully!")
                        except Exception as e:
                            print(f"   [WARNING] Email notification failed: {e}")
                    
                    total_new += new_count
                    total_existing += existing_count
                    total_notified += notified_count
                    
                    if new_count > 0:
                        print(f"   [OK] Saved {new_count} new posts to database")
                    else:
                        print(f"   [SKIP] No new posts (all {existing_count} already in DB)")
                
                except Exception as e:
                    print(f"   [ERROR] Scraping failed: {e}")
                    continue
            
            # Cycle summary
            cycle_end = datetime.now()
            cycle_duration = (cycle_end - cycle_start).total_seconds()
            
            print(f"\n{'='*80}")
            print(f"CYCLE #{cycle_number} SUMMARY")
            print(f"{'='*80}")
            print(f"   Posts scraped: {total_scraped}")
            print(f"   New posts saved: {total_new}")
            print(f"   Email notifications sent: {total_notified}")
            print(f"   Already in DB: {total_existing}")
            print(f"   Duration: {cycle_duration:.1f}s")
            
            # Wait before next cycle
            print(f"\n[*] Waiting {CHECK_INTERVAL_MINUTES} minutes until next cycle...")
            print(f"   Next check at: {datetime.now().replace(second=0, microsecond=0)}")
            print(f"   Press Ctrl+C to stop monitoring")
            
            time.sleep(CHECK_INTERVAL_MINUTES * 60)
    
    except KeyboardInterrupt:
        print("\n\n[STOP] Monitoring stopped by user")
        print(f"   Total cycles completed: {cycle_number}")
    
    except Exception as e:
        print(f"\n\n[ERROR] Fatal error: {e}")
    
    finally:
        print("\n[*] Closing browser...")
        driver.quit()
        print("[OK] Monitoring session ended")


if __name__ == "__main__":
    monitor_groups()
