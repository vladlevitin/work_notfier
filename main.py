"""Facebook Work Notifier - Main entry point."""

from __future__ import annotations

from pathlib import Path

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

from browser_manager import get_edge_binary_path, prepare_browser_profile
from supabase_db import save_posts, mark_as_notified
from email_notifier import send_email_notification
from scraper import filter_posts_by_keywords, print_keywords, print_posts, scrape_facebook_group
from config import FACEBOOK_GROUPS, SCROLL_STEPS_PER_GROUP
from datetime import datetime


def main() -> int:
    """Main function to run the Facebook work notifier."""
    # Display start info
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*80)
    print("FACEBOOK WORK NOTIFIER - Starting...")
    print(f"Timestamp: {timestamp}")
    print("="*80)
    
    # Setup browser profile
    user_data_dir = Path(__file__).resolve().parent / "edge_profile"
    if not prepare_browser_profile(user_data_dir):
        return 1

    # Check driver exists
    driver_path = Path(__file__).resolve().parent / "edgedriver" / "msedgedriver.exe"
    if not driver_path.exists():
        print("Edge driver not found:", driver_path)
        return 1

    # Configure Edge browser
    edge_binary = get_edge_binary_path()
    options = Options()
    options.use_chromium = True
    options.binary_location = str(edge_binary)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=0")

    service = Service(executable_path=str(driver_path))
    driver = webdriver.Edge(service=service, options=options)

    all_scraped_posts = []
    all_new_posts = []
    all_relevant_posts = []
    new_relevant_posts = []

    try:
        # Loop through all Facebook groups from config
        print(f"\nWill scrape {len(FACEBOOK_GROUPS)} Facebook groups ({SCROLL_STEPS_PER_GROUP} scrolls each)")
        
        for idx, group_url in enumerate(FACEBOOK_GROUPS, 1):
            print(f"\n{'='*80}")
            print(f"[{idx}/{len(FACEBOOK_GROUPS)}] Scraping group: {group_url}")
            print(f"{'='*80}")
            
            # Scrape Facebook group - get ALL posts
            posts = scrape_facebook_group(driver, group_url, scroll_steps=SCROLL_STEPS_PER_GROUP)
            all_scraped_posts.extend(posts)
            
            print(f"\n✅ Scraped {len(posts)} posts from this group")
            
            # Save ALL posts to database
            if posts:
                print(f"💾 Saving to database...")
                new_count, skipped_count = save_posts(posts)
                print(f"   ✅ New posts saved: {new_count}")
                print(f"   ⏭️  Duplicates skipped: {skipped_count}")
                
                # Track which posts were new
                if new_count > 0:
                    # Get the newly saved posts
                    new_posts = [p for p in posts if not skipped_count or posts.index(p) < new_count]
                    all_new_posts.extend(new_posts)
            
            # Filter for relevant keywords
            relevant_posts = filter_posts_by_keywords(posts)
            all_relevant_posts.extend(relevant_posts)
            print(f"🔍 Found {len(relevant_posts)} posts matching keywords")
            
            # Only notify about NEW posts that match keywords
            new_and_relevant = [p for p in relevant_posts if p in all_new_posts]
            new_relevant_posts.extend(new_and_relevant)
            
            if new_and_relevant:
                print(f"📧 {len(new_and_relevant)} new posts match keywords and will trigger email")
        
        # Display results
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Total posts scraped: {len(all_scraped_posts)}")
        print(f"New posts saved to database: {len(all_new_posts)}")
        print(f"Posts matching keywords: {len(all_relevant_posts)}")
        print(f"NEW relevant posts for notification: {len(new_relevant_posts)}")
        
        print_keywords()
        
        if new_relevant_posts:
            print_posts(new_relevant_posts, "New relevant posts for notification")
            
            # Send email notification
            print(f"\n📧 Sending email notification with {len(new_relevant_posts)} new matching posts...")
            send_email_notification(new_relevant_posts, FACEBOOK_GROUPS[0])
            
            # Mark posts as notified
            post_ids = [p["post_id"] for p in new_relevant_posts]
            mark_as_notified(post_ids)
            
            print("✅ Email sent and posts marked as notified!")
        else:
            print("\n✅ No new relevant posts to notify about")

        print("\nScraping finished. Press Enter to close.")
        input()

    finally:
        driver.quit()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
