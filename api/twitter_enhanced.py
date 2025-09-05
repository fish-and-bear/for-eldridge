#!/usr/bin/env python3
"""
Enhanced Twitter Scraper with search and comment capabilities
"""

import requests
import json
import re
from typing import List, Dict, Optional
from datetime import datetime

class EnhancedTwitterScraper:
    """
    Enhanced Twitter scraper using multiple strategies
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.syndication_base = "https://syndication.twitter.com"
        
    def scrape_user_timeline(self, username: str, limit: int = 50) -> List[Dict]:
        """
        Scrape user timeline with enhanced data extraction
        """
        username = username.lstrip('@').lower()
        
        # Try Twitter Syndication API with more tweets
        url = f"{self.syndication_base}/srv/timeline-profile/screen-name/{username}"
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                html_content = response.text
                tweets = []
                
                # Extract tweet data from HTML
                tweet_pattern = r'data-tweet-id="(\d+)".*?data-rendered-tweet-id="(\d+)".*?<div class="timeline-Tweet-text.*?">(.*?)</div>'
                matches = re.finditer(tweet_pattern, html_content, re.DOTALL)
                
                for match in matches[:limit]:
                    tweet_id = match.group(1)
                    tweet_html = match.group(3)
                    
                    # Clean HTML to extract text
                    text = re.sub(r'<[^>]+>', ' ', tweet_html)
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    # Extract metrics
                    likes_match = re.search(rf'data-tweet-id="{tweet_id}".*?TweetAction--heart.*?<span class="TweetAction-stat".*?>(\d+[KM]?)', html_content, re.DOTALL)
                    retweets_match = re.search(rf'data-tweet-id="{tweet_id}".*?TweetAction--retweet.*?<span class="TweetAction-stat".*?>(\d+[KM]?)', html_content, re.DOTALL)
                    
                    likes = self._parse_count(likes_match.group(1) if likes_match else "0")
                    retweets = self._parse_count(retweets_match.group(1) if retweets_match else "0")
                    
                    # Extract relative time if available (e.g., "2h", "1d")
                    time_str = ''
                    time_match = re.search(rf'data-tweet-id="{tweet_id}".*?class="timeline-Tweet-timestamp.*?>(.*?)<', html_content, re.DOTALL)
                    if time_match:
                        time_str = time_match.group(1).strip()
                    
                    # If no time found, use current time as fallback
                    if not time_str:
                        time_str = datetime.now().isoformat()
                    
                    tweets.append({
                        'id': tweet_id,
                        'text': text,
                        'author': f'@{username}',
                        'url': f'https://twitter.com/{username}/status/{tweet_id}',
                        'likes': likes,
                        'retweets': retweets,
                        'created_at': time_str,  # Add date field
                        'source': 'syndication_enhanced'
                    })
                
                return tweets
            
        except Exception as e:
            return [{'error': f'Failed to fetch timeline: {str(e)}'}]
        
        return []
    
    def search_tweets(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search tweets using Twitter's web search
        """
        # Use Twitter's mobile web search which is less restricted
        search_url = f"https://mobile.twitter.com/search?q={query}"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
            }
            
            response = self.session.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Extract tweet data from mobile HTML
                tweets = []
                
                # Pattern for mobile tweet extraction
                tweet_blocks = re.findall(r'<div class="tweet-text"[^>]*>(.*?)</div>', response.text, re.DOTALL)
                
                for block in tweet_blocks[:limit]:
                    text = re.sub(r'<[^>]+>', ' ', block)
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    if text:
                        tweets.append({
                            'text': text,
                            'search_query': query,
                            'source': 'mobile_search'
                        })
                
                if tweets:
                    return tweets
            
        except Exception as e:
            pass
        
        # Fallback: Return informative message
        return [{
            'info': f'Twitter search for "{query}" requires authentication. For advanced search, consider using Twitter\'s official API or authenticated tools.',
            'query': query,
            'alternatives': [
                'Use Twitter\'s advanced search at https://twitter.com/search-advanced',
                'Use social media monitoring tools like TweetDeck',
                'Consider Twitter\'s official API for programmatic access'
            ]
        }]
    
    def get_tweet_with_replies(self, tweet_url: str) -> Optional[Dict]:
        """
        Get a tweet with its replies/comments
        """
        # Extract tweet ID from URL
        match = re.search(r'/status/(\d+)', tweet_url)
        if not match:
            return {'error': 'Invalid tweet URL'}
        
        tweet_id = match.group(1)
        username_match = re.search(r'twitter\.com/([^/]+)/status/', tweet_url)
        username = username_match.group(1) if username_match else 'unknown'
        
        # Try to get tweet data via syndication
        try:
            # Syndication API can provide tweet embeds
            embed_url = f"https://publish.twitter.com/oembed?url={tweet_url}"
            response = self.session.get(embed_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                html_content = data.get('html', '')
                
                # Extract text from embed HTML
                text_match = re.search(r'<p[^>]*>(.*?)</p>', html_content)
                text = re.sub(r'<[^>]+>', ' ', text_match.group(1)) if text_match else ''
                text = re.sub(r'\s+', ' ', text).strip()
                
                return {
                    'id': tweet_id,
                    'text': text,
                    'author': f'@{username}',
                    'url': tweet_url,
                    'author_name': data.get('author_name', ''),
                    'source': 'oembed_api',
                    'note': 'Replies require authentication to fetch. Use Twitter web or app to view full conversation.'
                }
            
        except Exception as e:
            return {'error': f'Failed to fetch tweet: {str(e)}'}
        
        return None
    
    def _parse_count(self, count_str: str) -> int:
        """Parse count strings like '1.2K' or '3M' to integers"""
        if not count_str:
            return 0
        
        count_str = count_str.strip()
        
        if 'K' in count_str:
            return int(float(count_str.replace('K', '')) * 1000)
        elif 'M' in count_str:
            return int(float(count_str.replace('M', '')) * 1000000)
        else:
            try:
                return int(count_str)
            except:
                return 0


# Test module
if __name__ == "__main__":
    print("Testing Enhanced Twitter Scraper...")
    scraper = EnhancedTwitterScraper()
    
    # Test timeline
    print("\n1. Testing timeline scraping for @nasa...")
    tweets = scraper.scrape_user_timeline("nasa", limit=3)
    for tweet in tweets:
        if 'error' not in tweet:
            print(f"   - {tweet['text'][:80]}...")
    
    # Test search
    print("\n2. Testing search for 'AI'...")
    results = scraper.search_tweets("AI", limit=3)
    for result in results:
        if 'text' in result:
            print(f"   - {result['text'][:80]}...")
        elif 'info' in result:
            print(f"   - Info: {result['info']}")
    
    # Test tweet with replies
    print("\n3. Testing single tweet fetch...")
    tweet_data = scraper.get_tweet_with_replies("https://twitter.com/nasa/status/1234567890")
    if tweet_data:
        print(f"   - Got tweet: {tweet_data.get('text', 'N/A')[:80]}...")