import tweepy
import schedule
import time
import os
from groq import Groq
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

# Load environment variables from .env file
load_dotenv()

# --- Your Twitter API Credentials from .env ---
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET_KEY = os.getenv("TWITTER_API_SECRET_KEY")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# --- Your Groq API Key from .env ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def scrape_website_content(url="https://addplus.org/"):
    """Scrapes the main text content from a given URL."""
    print(f"Scraping website: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        # Extract text from main content areas, focusing on articles or body
        paragraphs = soup.find_all('p', limit=5) # Limit to first 5 paragraphs
        headings = soup.find_all(['h1', 'h2'], limit=3) # Limit to first 3 headings
        
        content = " ".join([h.get_text(strip=True) for h in headings])
        content += " " + " ".join([p.get_text(strip=True) for p in paragraphs])
        
        print("Website scraping successful.")
        # Return a summary of the content, limited to a reasonable size for the AI context
        return content[:1500]
    except requests.RequestException as e:
        print(f"Error scraping website: {e}")
        return "Could not fetch website content."

def get_recent_tweets(client, username="add_infofi"):
    """Fetches the most recent tweets from a given Twitter user."""
    print(f"Fetching recent tweets for @{username}")
    try:
        user = client.get_user(username=username)
        if not user.data:
            print(f"Could not find user @{username}")
            return "Could not fetch recent tweets."
            
        user_id = user.data.id
        # Fetch the 3 most recent tweets, excluding retweets and replies
        tweets = client.get_users_tweets(id=user_id, max_results=3, exclude=["retweets", "replies"])
        
        if not tweets.data:
            print(f"No recent tweets found for @{username}.")
            return "No recent tweets available."
            
        tweet_texts = " ".join([tweet.text for tweet in tweets.data])
        print("Recent tweets fetched successfully.")
        return tweet_texts[:1000] # Limit context size
    except tweepy.errors.TweepyException as e:
        print(f"Error fetching tweets: {e}")
        return "Could not fetch recent tweets due to an API error."

def generate_viral_tweet(website_content, recent_tweets):
    """
    Generates an engaging, influencer-style tweet using the Groq API and scraped context.
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)
        print("Generating AI tweet with Groq using fresh content...")

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a top-tier social media influencer specializing in AI and Technology. "
                        "Your task is to craft a short, punchy, and viral tweet based on the provided context. "
                        "The tweet MUST mention @add_infofi. "
                        "Use the 'LATEST CONTENT' to create a timely and relevant message that hypes up their work. "
                        "Focus on innovation, future tech, and AI breakthroughs mentioned in the context. "
                        "Use an energetic and inspiring tone. Include 2-3 relevant, trending hashtags. "
                        "The tweet must end with the phrase 'Join me here:' followed by this exact URL: https://addplus.org/boost/abelbk007. "
                        "The output must be ONLY the tweet text."
                    )
                },
                {
                    "role": "user",
                    "content": f"""
                    LATEST CONTENT:
                    - From addplus.org: "{website_content}"
                    - Recent Tweets from @add_infofi: "{recent_tweets}"

                    Based on this latest content, create a viral tweet.
                    """,
                },
            ],
            model="llama3-8b-8192",
            temperature=0.8, # Slightly increased for more creative outputs
            max_tokens=280,
        )
        
        tweet_text = chat_completion.choices[0].message.content.strip()
        print(f"Generated Tweet: {tweet_text}")
        return tweet_text

    except Exception as e:
        print(f"Error generating tweet with Groq: {e}")
        return None

def post_tweet(tweet_text):
    """
    This function authenticates with the Twitter API and posts a tweet.
    """
    if not all([API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        print("Error: Twitter API credentials are not set. Check your .env file.")
        return

    try:
        client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        print("Posting tweet...")
        response = client.create_tweet(text=tweet_text)
        print("Tweet posted successfully!")
        print(f"Tweet ID: {response.data['id']}")

    except tweepy.errors.TweepyException as e:
        print(f"Error posting tweet: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def job():
    """The job to be scheduled."""
    print("\n--- Running daily tweet job ---")
    
    # Authenticate with Twitter once for scraping and posting
    try:
        twitter_client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
    except Exception as e:
        print(f"Failed to create Twitter client: {e}")
        return

    # Get fresh content
    website_content = scrape_website_content()
    recent_tweets = get_recent_tweets(twitter_client)

    # Generate a tweet with the fresh content
    ai_tweet = generate_viral_tweet(website_content, recent_tweets)
    
    if ai_tweet:
        post_tweet(ai_tweet)
    else:
        print("Skipping post due to generation error.")

if __name__ == "__main__":
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY not found. Please add it to your .env file.")
    else:
        schedule.every().day.at("09:00").do(job)

        print("Scheduler started. Waiting for the scheduled time (9:00 AM)...")
        print("Keep this script running. Press Ctrl+C to exit.")
        
        # Run the job once immediately for testing
        job() 

        while True:
            schedule.run_pending()
            time.sleep(60) # Check every minute