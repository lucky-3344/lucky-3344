import requests
try:
    r = requests.get('https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US', timeout=10)
    print(r.text[:4000])
except Exception as e:
    print(f"Error: {e}")
