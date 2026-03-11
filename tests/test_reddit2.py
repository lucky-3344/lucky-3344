from agent_reach.channels.reddit import RedditChannel
import json

reddit = RedditChannel()

print("Testing Reddit...")
try:
    result = reddit.fetch("AI", max_results=10)
    print("Success!")
    print(json.dumps(result[:3], indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
