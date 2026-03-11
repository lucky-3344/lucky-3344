from agent_reach.channels.reddit import RedditChannel
from agent_reach.config import Config
import json

config = Config()
reddit = RedditChannel(config)

print("Testing Reddit...")
try:
    result = reddit.fetch("AI", max_results=10)
    print("Success!")
    print(json.dumps(result[:3], indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
