"""Facebook Work Notifier - Main entry point."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

# Import from new structure
from src.scraper import create_driver, scrape_facebook_group, filter_posts_by_keywords, print_posts
from src.database import save_posts, mark_as_notified
from src.notifications import send_email_notification
from config.settings import load_facebook_groups, KEYWORDS


def main() -> int:
    """Main function to run the Facebook work notifier."""
    # Display start info
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*80)
    print("🚗 FACEBOOK WORK NOTIFIER")
    print(f"📅 Started: {timestamp}")
    print("="*80)
    
    # Load Facebook groups from config
    facebook_groups = load_facebook_groups()
    
    if not facebook_groups:
        print("❌ No enabled Facebook groups found in config/groups.json")
        return 1
    
    print(f"\n📋 Loaded {len(facebook_groups)} enabled groups from config:")
    for idx, group in enumerate(facebook_groups, 1):
        print(f"  {idx}. {group['name']}")
    
    # Create browser driver
    print("\n🌐 Starting browser...")
    driver = create_driver()

    all_scraped_posts = []
    all_new_posts = []
    all_relevant_posts = []
    new_relevant_posts = []

    try:
        # Loop through all Facebook groups from config
        for idx, group_config in enumerate(facebook_groups, 1):
            group_name = group_config['name']
            group_url = group_config['url']
            scroll_steps = group_config.get('scroll_steps', 5)
            
            print(f"\n{'='*80}")
            print(f"[{idx}/{len(facebook_groups)}] Scraping: {group_name}")
            print(f"📍 URL: {group_url}")
            print(f"📜 Scrolls: {scroll_steps}")
            print(f"{'='*80}")
            
            # Scrape Facebook group - get ALL posts
            posts = scrape_facebook_group(driver, group_url, scroll_steps=scroll_steps)
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
        print(f"📊 Total posts scraped: {len(all_scraped_posts)}")
        print(f"✨ New posts saved to database: {len(all_new_posts)}")
        print(f"🔍 Posts matching keywords: {len(all_relevant_posts)}")
        print(f"📧 NEW relevant posts for notification: {len(new_relevant_posts)}")
        
        print(f"\n🔑 Keywords: {', '.join(KEYWORDS[:10])}{'...' if len(KEYWORDS) > 10 else ''}")
        
        if new_relevant_posts:
            print_posts(new_relevant_posts, "New relevant posts for notification")
            
            # Send email notification
            print(f"\n📧 Sending email notification with {len(new_relevant_posts)} new matching posts...")
            send_email_notification(new_relevant_posts, facebook_groups[0]['url'])
            
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
