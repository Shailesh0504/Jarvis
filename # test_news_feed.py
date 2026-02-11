# test_news_feed.py
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from skills.news import get_latest_news

if __name__ == "__main__":
    headlines = get_latest_news()
    if headlines:
        print("Successfully fetched headlines:")
        for i, headline in enumerate(headlines):
            print(f"{i+1}: {headline}")
    else:
        print("Failed to fetch headlines or no headlines found.")
