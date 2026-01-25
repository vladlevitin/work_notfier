"""Facebook Work Notifier - Main entry point."""

from __future__ import annotations

from pathlib import Path

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

from browser_manager import get_edge_binary_path, prepare_browser_profile
from database_sqlalchemy import save_posts, get_posts, mark_as_notified, get_stats, init_database
from email_notifier import send_email_notification
from scraper import filter_posts_by_keywords, print_keywords, print_posts, scrape_facebook_group
from config import FACEBOOK_GROUPS, SCROLL_STEPS_PER_GROUP


def main() -> int:
    """Main function to run the Facebook work notifier."""
    # Initialize database
    init_database()
    
    # Display stats
    print("\n" + "="*80)
    print("FACEBOOK WORK NOTIFIER - Starting...")
    print("="*80)
    
    try:
        stats = get_stats()
        print(f"Current database stats:")
        print(f"  Total posts: {stats['total']}")
        print(f"  New posts (not notified): {stats['new']}")
        for group_stat in stats['by_group']:
            print(f"  {group_stat['group']}: {group_stat['count']}")
    except Exception as e:
        print(f"Could not load stats: {e}")
    
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
            
            # Save ALL posts to Supabase (regardless of keywords)
            new_count, skipped_count = save_posts(posts)
            print(f"📊 Supabase: {new_count} new posts added, {skipped_count} duplicates skipped")
            
            # Filter for relevant keywords
            relevant_posts = filter_posts_by_keywords(posts)
            print(f"🔍 Found {len(relevant_posts)} posts matching keywords")
            
            # Check which relevant posts are NEW (not yet notified)
            for post in relevant_posts:
                # Get from database to check notified status
                try:
                    db_posts = get_posts(limit=1, offset=0, group_url=None, search=None, only_new=True)
                    # Check if this specific post_id is in the new posts
                    if any(db_post["post_id"] == post["post_id"] for db_post in db_posts):
                        new_relevant_posts.append(post)
                except Exception as e:
                    print(f"Warning: Could not check notification status for post {post['post_id']}: {e}")
        
        # Display results
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Total posts scraped: {len(all_scraped_posts)}")
        print(f"New posts saved to Supabase: {sum(save_posts([p])[0] for p in all_scraped_posts)}")
        print(f"New relevant posts (matching keywords, not yet notified): {len(new_relevant_posts)}")
        
        print_keywords()
        
        if new_relevant_posts:
            print_posts(new_relevant_posts, "New relevant posts for notification")
            
            # Send email notification
            print(f"\n📧 Sending email notification with {len(new_relevant_posts)} matching posts...")
            send_email_notification(new_relevant_posts, FACEBOOK_GROUPS[0])
            print("✅ Email sent successfully!")
            
            # Mark posts as notified in Supabase
            post_ids = [p["post_id"] for p in new_relevant_posts if p["post_id"] != "unknown"]
            if post_ids:
                mark_as_notified(post_ids)
                print(f"✅ Marked {len(post_ids)} posts as notified in Supabase")
        else:
            print("\n✅ No new relevant posts to notify about")

        print("\nScraping finished. Press Enter to close.")
        input()

    finally:
        driver.quit()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
