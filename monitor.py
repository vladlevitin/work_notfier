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
from src.scraper import scrape_facebook_group
from src.database import save_post, post_exists
from config.settings import load_facebook_groups

# Configuration
CHECK_INTERVAL_MINUTES = 5  # Wait between cycles
SCROLL_STEPS_FOR_MONITORING = 1  # Just check recent posts (top of feed)


def create_driver():
    """Create and return Edge WebDriver instance."""
    driver_path = Path(__file__).resolve().parent / "edgedriver" / "msedgedriver.exe"
    user_data_dir = Path(__file__).resolve().parent / "edge_profile"
    
    options = Options()
    options.use_chromium = True
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=0")
    
    service = Service(executable_path=str(driver_path))
    return webdriver.Edge(service=service, options=options)


def monitor_groups():
    """
    Continuously monitor Facebook groups for new posts.
    Runs in an infinite loop, checking each group in cycles.
    """
    print("\n" + "="*80)
    print("🔄 FACEBOOK WORK NOTIFIER - CONTINUOUS MONITORING")
    print("="*80)
    
    # Load enabled groups
    facebook_groups = load_facebook_groups()
    
    if not facebook_groups:
        print("❌ No enabled groups found in config/groups.json")
        return
    
    print(f"\n📋 Monitoring {len(facebook_groups)} enabled groups:")
    for idx, group in enumerate(facebook_groups, 1):
        print(f"  {idx}. {group['name']}")
    
    print(f"\n⏱️  Check interval: {CHECK_INTERVAL_MINUTES} minutes")
    print(f"📜 Scrolls per check: {SCROLL_STEPS_FOR_MONITORING} (recent posts only)")
    print("\n" + "="*80)
    print("🚀 Starting monitoring loop... (Press Ctrl+C to stop)")
    print("="*80)
    
    # Create browser driver once (reuse across cycles)
    print("\n🌐 Starting browser...")
    driver = create_driver()
    
    cycle_number = 0
    
    try:
        while True:
            cycle_number += 1
            cycle_start = datetime.now()
            
            print(f"\n{'='*80}")
            print(f"🔄 CYCLE #{cycle_number} - {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")
            
            total_scraped = 0
            total_new = 0
            total_existing = 0
            
            # Check each enabled group
            for group_idx, group_config in enumerate(facebook_groups, 1):
                group_name = group_config['name']
                group_url = group_config['url']
                
                print(f"\n[{group_idx}/{len(facebook_groups)}] 🔍 Checking: {group_name}")
                
                try:
                    # Scrape recent posts (minimal scrolling)
                    posts = scrape_facebook_group(
                        driver, 
                        group_url, 
                        scroll_steps=SCROLL_STEPS_FOR_MONITORING
                    )
                    
                    total_scraped += len(posts)
                    print(f"   📊 Found {len(posts)} posts")
                    
                    # Check and save only new posts
                    new_count = 0
                    existing_count = 0
                    
                    for post in posts:
                        if post_exists(post["post_id"]):
                            existing_count += 1
                        else:
                            # New post! Save it with AI processing
                            if save_post(post, use_ai=True):
                                new_count += 1
                                print(f"   ✨ NEW: {post['title'][:50]}...")
                    
                    total_new += new_count
                    total_existing += existing_count
                    
                    if new_count > 0:
                        print(f"   ✅ Saved {new_count} new posts")
                    else:
                        print(f"   ⏭️  No new posts (all {existing_count} already in DB)")
                
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    continue
            
            # Cycle summary
            cycle_end = datetime.now()
            cycle_duration = (cycle_end - cycle_start).total_seconds()
            
            print(f"\n{'='*80}")
            print(f"📊 CYCLE #{cycle_number} SUMMARY")
            print(f"{'='*80}")
            print(f"   Posts scraped: {total_scraped}")
            print(f"   ✨ New posts saved: {total_new}")
            print(f"   ⏭️  Already in DB: {total_existing}")
            print(f"   ⏱️  Duration: {cycle_duration:.1f}s")
            
            # Wait before next cycle
            print(f"\n⏳ Waiting {CHECK_INTERVAL_MINUTES} minutes until next cycle...")
            print(f"   Next check at: {datetime.now().replace(second=0, microsecond=0)}")
            print(f"   Press Ctrl+C to stop monitoring")
            
            time.sleep(CHECK_INTERVAL_MINUTES * 60)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
        print(f"   Total cycles completed: {cycle_number}")
    
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
    
    finally:
        print("\n🔒 Closing browser...")
        driver.quit()
        print("✅ Monitoring session ended")


if __name__ == "__main__":
    monitor_groups()
