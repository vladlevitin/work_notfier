"""Facebook Work Notifier - Main entry point."""

from __future__ import annotations

from pathlib import Path

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

from browser_manager import get_edge_binary_path, prepare_browser_profile
from storage_manager import upload_posts_to_storage, get_timestamp_folder
from email_notifier import send_email_notification
from scraper import filter_posts_by_keywords, print_keywords, print_posts, scrape_facebook_group
from config import FACEBOOK_GROUPS, SCROLL_STEPS_PER_GROUP


def main() -> int:
    """Main function to run the Facebook work notifier."""
    # Display start info
    print("\n" + "="*80)
    print("FACEBOOK WORK NOTIFIER - Starting...")
    print(f"Timestamp: {get_timestamp_folder()}")
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
    new_relevant_posts = []
    groups_posts = {}  # Store posts by group for storage upload

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
            
            # Store posts by group for storage upload
            if posts:
                group_name = posts[0]["group_name"]
                groups_posts[group_name] = posts
            
            print(f"\n✅ Scraped {len(posts)} posts from this group")
            
            # Filter for relevant keywords
            relevant_posts = filter_posts_by_keywords(posts)
            print(f"🔍 Found {len(relevant_posts)} posts matching keywords")
            
            # All relevant posts are "new" since we're using file storage
            new_relevant_posts.extend(relevant_posts)
        
        # Upload ALL posts to Supabase Storage (in timestamped folders)
        print(f"\n{'='*80}")
        print(f"UPLOADING TO STORAGE")
        print(f"{'='*80}")
        
        for group_name, posts in groups_posts.items():
            folder_path, count = upload_posts_to_storage(posts, group_name)
            if folder_path:
                print(f"✅ Uploaded {count} posts from '{group_name}' to {folder_path}")
        
        # Display results
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Total posts scraped: {len(all_scraped_posts)}")
        print(f"Relevant posts (matching keywords): {len(new_relevant_posts)}")
        print(f"Groups processed: {len(groups_posts)}")
        
        print_keywords()
        
        if new_relevant_posts:
            print_posts(new_relevant_posts, "Relevant posts for notification")
            
            # Send email notification
            print(f"\n📧 Sending email notification with {len(new_relevant_posts)} matching posts...")
            send_email_notification(new_relevant_posts, FACEBOOK_GROUPS[0])
            print("✅ Email sent successfully!")
        else:
            print("\n✅ No relevant posts to notify about")

        print("\nScraping finished. Press Enter to close.")
        input()

    finally:
        driver.quit()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
