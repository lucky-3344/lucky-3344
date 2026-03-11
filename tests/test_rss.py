from agent_reach.channels.rss import RSSChannel
import json

rss = RSSChannel()

# Test fetching some popular RSS feeds
feeds = [
    'https://news.ycombinator.com/rss',
    'https://techcrunch.com/feed/',
    'https://www.theverge.com/rss/index.xml'
]

for url in feeds:
    print(f"Testing: {url}")
    try:
        result = rss.fetch(url, max_items=5)
        print(f"  Success! Got {len(result)} items")
        if result:
            title = result[0].get("title", "N/A")
            print(f"  First item: {title[:60]}")
    except Exception as e:
        print(f"  Error: {str(e)[:60]}")
    print()
