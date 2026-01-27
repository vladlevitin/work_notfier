# 📝 How to Add Facebook Groups

## Quick Guide

### ⭐ TL;DR
1. Open `config/groups.json`
2. Copy an existing group entry
3. Change `name` and `url`
4. Save file
5. Run `python main.py`

---

## Step-by-Step Instructions

### Step 1: Find the Facebook Group URL

1. Go to the Facebook group you want to scrape
2. Copy the URL from your browser
   - Example: `https://www.facebook.com/groups/123456789`

### Step 2: Open the Configuration File

Open: **`config/groups.json`**

You'll see something like this:

```json
{
  "facebook_groups": [
    {
      "name": "Småjobber utføres og ønskes i Oslo og Viken",
      "url": "https://www.facebook.com/groups/346441192214130",
      "enabled": true,
      "scroll_steps": 5,
      "description": "Main group for small jobs in Oslo and Viken region"
    },
    {
      "name": "Småjobber i Oslo Akershus (snekker tjenester. Hagearbeid. Husvask)",
      "url": "https://www.facebook.com/groups/352567911457793",
      "enabled": true,
      "scroll_steps": 5,
      "description": "Carpentry, garden work, and house cleaning jobs in Oslo/Akershus"
    }
  ]
}
```

### Step 3: Add Your New Group

Add a comma after the last group, then copy this template:

```json
{
  "name": "Your Group Name Here",
  "url": "https://www.facebook.com/groups/YOUR_GROUP_ID",
  "enabled": true,
  "scroll_steps": 5,
  "description": "Optional description of what this group is for"
}
```

**Example:**

```json
{
  "facebook_groups": [
    {
      "name": "Småjobber utføres og ønskes i Oslo og Viken",
      "url": "https://www.facebook.com/groups/346441192214130",
      "enabled": true,
      "scroll_steps": 5,
      "description": "Main group for small jobs in Oslo and Viken region"
    },
    {
      "name": "Småjobber i Oslo Akershus (snekker tjenester. Hagearbeid. Husvask)",
      "url": "https://www.facebook.com/groups/352567911457793",
      "enabled": true,
      "scroll_steps": 5,
      "description": "Carpentry, garden work, and house cleaning jobs in Oslo/Akershus"
    },
    {
      "name": "Byggejobber Oslo",
      "url": "https://www.facebook.com/groups/987654321",
      "enabled": true,
      "scroll_steps": 5,
      "description": "Construction jobs in Oslo"
    }
  ]
}
```

### Step 4: Save the File

Make sure your JSON is valid:
- ✅ Commas between groups (but not after the last one)
- ✅ All strings in quotes
- ✅ No trailing commas

### Step 5: Test the Configuration

```bash
python config/settings.py
```

You should see your new group listed:

```
=== Facebook Work Notifier Configuration ===

Loaded 3 enabled groups:

1. Småjobber utføres og ønskes i Oslo og Viken
   URL: https://www.facebook.com/groups/346441192214130
   Scroll steps: 5

2. Småjobber i Oslo Akershus (snekker tjenester. Hagearbeid. Husvask)
   URL: https://www.facebook.com/groups/352567911457793
   Scroll steps: 5

3. Byggejobber Oslo
   URL: https://www.facebook.com/groups/987654321
   Scroll steps: 5
```

### Step 6: Run the Scraper

```bash
python main.py
```

The scraper will now include your new group!

---

## Configuration Options

### Required Fields

- **`name`** - Display name for the group (can be anything you want)
- **`url`** - Full Facebook group URL
- **`enabled`** - `true` to scrape, `false` to skip

### Optional Fields

- **`scroll_steps`** - How many times to scroll down (default: 5)
  - More scrolls = more posts scraped
  - Recommended: 3-10
- **`description`** - Optional notes about the group

---

## Examples

### Minimal Configuration (Required Fields Only)

```json
{
  "name": "My Group",
  "url": "https://www.facebook.com/groups/123456",
  "enabled": true
}
```

### Full Configuration (All Fields)

```json
{
  "name": "Complete Example Group",
  "url": "https://www.facebook.com/groups/123456",
  "enabled": true,
  "scroll_steps": 7,
  "description": "This group posts electrician jobs in Bergen"
}
```

### Temporarily Disable a Group

```json
{
  "name": "Group I Don't Want Right Now",
  "url": "https://www.facebook.com/groups/123456",
  "enabled": false,
  "description": "Temporarily disabled - too many posts"
}
```

---

## Tips

### How Many Groups Can I Add?
- **Unlimited!** Add as many as you want
- The scraper processes them one by one
- More groups = longer scraping time

### How to Find More Groups?
1. Search Facebook: "småjobber oslo"
2. Look at "Suggested Groups" in existing groups
3. Ask friends for recommendations

### Scroll Steps Recommendations
- **3-5 scrolls** - Quick scrape, recent posts only
- **5-7 scrolls** - Balanced (recommended)
- **10+ scrolls** - Deep scrape, older posts

### Performance Tips
- Start with fewer groups and add more later
- Use 5 scroll_steps initially
- Disable inactive groups (set `enabled: false`)

---

## Troubleshooting

### JSON Syntax Error

```
❌ Error: Expecting ',' delimiter
```

**Fix:** Make sure you have commas between groups:

```json
{
  "facebook_groups": [
    { "name": "Group 1", ... },   ← comma here
    { "name": "Group 2", ... },   ← comma here
    { "name": "Group 3", ... }    ← NO comma on last one
  ]
}
```

### Group Not Being Scraped

1. Check `enabled: true`
2. Verify URL is correct
3. Make sure you're logged into Facebook in the Edge browser

### Posts Not Appearing

- Increase `scroll_steps` (try 7 or 10)
- Check if group requires membership
- Verify you have access to the group

---

## Quick Reference

```json
{
  "facebook_groups": [
    {
      "name": "Group Name",
      "url": "https://www.facebook.com/groups/123456",
      "enabled": true,
      "scroll_steps": 5,
      "description": "Optional notes"
    }
  ]
}
```

**File Location:** `config/groups.json`  
**Test Config:** `python config/settings.py`  
**Run Scraper:** `python main.py`

---

## Need Help?

- 📖 [Project Structure](PROJECT_STRUCTURE.md)
- 🚀 [Main README](../README.md)
- 🐛 [Report Issue](https://github.com/vladlevitin/work_notfier/issues)

Happy scraping! 🚀
