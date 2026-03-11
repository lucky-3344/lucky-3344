import requests

# Get HN front page
r = requests.get('https://r.jina.ai/https://news.ycombinator.com', timeout=25)
text = r.text

# Look for story titles with points
lines = text.split('\n')
in_story = False
story_buffer = []
ai_keywords = ['AI', 'GPT', 'Claude', 'OpenAI', 'Anthropic', 'Google', 'model', 'LLM', 'machine learning', 'neural', 'agent', 'Gemini', 'DeepSeek']

print('AI Related Posts on Hacker News:')
print('='*60)

count = 0
for line in lines:
    # Check if line has points (like "146 points")
    if 'points' in line.lower():
        story_buffer = [line]
        in_story = True
    elif in_story:
        story_buffer.append(line)
        # If we have enough, check for AI
        if len(story_buffer) >= 2:
            full_story = ' '.join(story_buffer)
            if any(k.lower() in full_story.lower() for k in ai_keywords):
                # Extract title
                title_lines = [l for l in story_buffer if '[' in l and '](' in l]
                if title_lines:
                    import re
                    titles = re.findall(r'\[([^\]]+)\]', title_lines[0])
                    urls = re.findall(r'\(([^)]+)\)', title_lines[0])
                    if titles:
                        count += 1
                        points_match = re.search(r'(\d+)\s*points', full_story, re.IGNORECASE)
                        points = points_match.group(1) if points_match else '?'
                        print(f"{count}. [{points} pts] {titles[0][:55]}")
                        if count >= 15:
                            break
            in_story = False
            story_buffer = []

print()
print(f"Found {count} AI-related posts!")
