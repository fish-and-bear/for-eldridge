#!/usr/bin/env python3
"""
xcancel Twitter Scraper - Smart scraping with anti-bot measures
"""

import requests
import time
import random
import re
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup

class XCancelTwitterScraper:
    """
    Smart Twitter scraper using xcancel (nitter fork) with anti-bot measures
    """
    
    def __init__(self):
        self.base_url = "https://xcancel.com"
        self.session = requests.Session()
        
        # Rotate user agents to avoid detection
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0'
        ]
        
    def _get_headers(self):
        """Generate realistic browser headers with random user agent"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Pragma': 'no-cache'
        }
    
    def _random_delay(self):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(0.5, 2.5)
        time.sleep(delay)
    
    def scrape_user_timeline(self, username: str, limit: int = 20) -> List[Dict]:
        """
        Scrape a user's timeline from xcancel with anti-bot measures
        
        Returns complete timeline data including:
        - Full text
        - Engagement metrics (likes, retweets, replies)
        - Media URLs
        - Timestamps
        """
        
        # Clean username
        username = username.lstrip('@').lower()
        url = f"{self.base_url}/{username}"
        
        try:
            # Add random delay before request
            self._random_delay()
            
            # Make request with browser-like headers
            response = self.session.get(url, headers=self._get_headers(), timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tweets = []
                
                # Find all timeline items
                timeline_items = soup.find_all('div', class_='timeline-item')
                
                for item in timeline_items[:limit]:
                    try:
                        # Extract tweet link for ID
                        tweet_link = item.find('a', class_='tweet-link')
                        if not tweet_link:
                            continue
                            
                        href = tweet_link.get('href', '')
                        tweet_id_match = re.search(r'/status/(\d+)', href)
                        tweet_id = tweet_id_match.group(1) if tweet_id_match else None
                        
                        # Extract tweet content
                        tweet_content = item.find('div', class_='tweet-content')
                        text = tweet_content.get_text(strip=True) if tweet_content else ''
                        
                        # Extract author info
                        fullname = item.find('a', class_='fullname')
                        username_elem = item.find('a', class_='username')
                        author_name = fullname.get_text(strip=True) if fullname else username
                        author_username = username_elem.get_text(strip=True) if username_elem else f'@{username}'
                        
                        # Extract timestamp
                        tweet_date = item.find('span', class_='tweet-date')
                        date_link = tweet_date.find('a') if tweet_date else None
                        timestamp = date_link.get('title') if date_link else ''
                        
                        # Extract engagement stats using the helper method
                        stats = self._extract_stats(item)
                        
                        # Check if it's a retweet
                        retweet_header = item.find('div', class_='retweet-header')
                        is_retweet = retweet_header is not None
                        
                        # Extract media if present
                        media_items = []
                        attachments = item.find('div', class_='attachments')
                        if attachments:
                            images = attachments.find_all('img')
                            for img in images:
                                src = img.get('src', '')
                                if src:
                                    media_items.append({
                                        'type': 'image',
                                        'url': src if src.startswith('http') else f"{self.base_url}{src}"
                                    })
                        
                        tweet_data = {
                            'id': tweet_id,
                            'text': text,
                            'author': author_username,
                            'author_name': author_name,
                            'created_at': timestamp,
                            'likes': stats.get('likes', 0),
                            'retweets': stats.get('retweets', 0),
                            'replies': stats.get('replies', 0),
                            'quotes': stats.get('quotes', 0),
                            'url': f"https://twitter.com/{username}/status/{tweet_id}" if tweet_id else '',
                            'is_retweet': is_retweet,
                            'media': media_items,
                            'source': 'xcancel'
                        }
                        
                        tweets.append(tweet_data)
                        
                    except Exception as e:
                        # Continue on individual tweet parsing errors
                        continue
                
                return tweets
            
            elif response.status_code == 429:
                # Rate limited
                return [{
                    'error': 'Rate limited by xcancel. Please wait before trying again.',
                    'status_code': 429
                }]
            else:
                return [{
                    'error': f'Failed to fetch from xcancel: HTTP {response.status_code}',
                    'status_code': response.status_code
                }]
                
        except requests.RequestException as e:
            return [{
                'error': f'Network error accessing xcancel: {str(e)}'
            }]
        except Exception as e:
            return [{
                'error': f'Unexpected error: {str(e)}'
            }]
    
    def search_tweets(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for tweets by keyword or hashtag
        
        Args:
            query: Search term (e.g., "ai", "#technology", "from:elonmusk")
            limit: Maximum number of tweets to return
        
        Returns:
            List of tweet dictionaries with search results
        """
        
        # Build search URL
        url = f"{self.base_url}/search"
        params = {
            'f': 'tweets',  # Filter to tweets only
            'q': query
        }
        
        try:
            self._random_delay()
            
            # Make request with params
            response = self.session.get(url, headers=self._get_headers(), params=params, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tweets = []
                
                # Find all timeline items (same structure as user timeline)
                timeline_items = soup.find_all('div', class_='timeline-item')
                
                for item in timeline_items[:limit]:
                    try:
                        # Extract tweet similar to timeline parsing
                        tweet_link = item.find('a', class_='tweet-link')
                        if not tweet_link:
                            continue
                            
                        href = tweet_link.get('href', '')
                        tweet_id_match = re.search(r'/status/(\d+)', href)
                        tweet_id = tweet_id_match.group(1) if tweet_id_match else None
                        
                        # Extract username from tweet link
                        username_match = re.search(r'/([^/]+)/status/', href)
                        username = username_match.group(1) if username_match else 'unknown'
                        
                        # Extract tweet content
                        tweet_content = item.find('div', class_='tweet-content')
                        text = tweet_content.get_text(strip=True) if tweet_content else ''
                        
                        # Extract author info
                        fullname = item.find('a', class_='fullname')
                        username_elem = item.find('a', class_='username')
                        author_name = fullname.get_text(strip=True) if fullname else username
                        author_username = username_elem.get_text(strip=True) if username_elem else f'@{username}'
                        
                        # Extract timestamp
                        tweet_date = item.find('span', class_='tweet-date')
                        date_link = tweet_date.find('a') if tweet_date else None
                        timestamp = date_link.get('title') if date_link else ''
                        
                        # Extract engagement stats
                        stats = self._extract_stats(item)
                        
                        tweet_data = {
                            'id': tweet_id,
                            'text': text,
                            'author': author_username,
                            'author_name': author_name,
                            'created_at': timestamp,
                            'likes': stats.get('likes', 0),
                            'retweets': stats.get('retweets', 0),
                            'replies': stats.get('replies', 0),
                            'quotes': stats.get('quotes', 0),
                            'url': f"https://twitter.com/{username}/status/{tweet_id}" if tweet_id else '',
                            'search_query': query,
                            'source': 'xcancel_search'
                        }
                        
                        tweets.append(tweet_data)
                        
                    except Exception as e:
                        continue
                
                return tweets
                
            else:
                return [{
                    'error': f'Search failed with status {response.status_code}',
                    'query': query
                }]
                
        except Exception as e:
            return [{
                'error': f'Search error: {str(e)}',
                'query': query
            }]
    
    def _extract_stats(self, item):
        """Extract engagement statistics from a timeline item"""
        stats = {}
        stat_elements = item.find_all('span', class_='tweet-stat')
        for stat in stat_elements:
            icon = stat.find('span', class_=re.compile('icon-'))
            if icon:
                icon_class = icon.get('class', [])
                value_text = stat.get_text(strip=True)
                # Extract number from text
                value_match = re.search(r'[\d,]+', value_text)
                value = int(value_match.group().replace(',', '')) if value_match else 0
                
                if 'icon-comment' in icon_class:
                    stats['replies'] = value
                elif 'icon-retweet' in icon_class:
                    stats['retweets'] = value
                elif 'icon-heart' in icon_class:
                    stats['likes'] = value
                elif 'icon-quote' in icon_class:
                    stats['quotes'] = value
        return stats
    
    def scrape_tweet_with_replies(self, tweet_url: str) -> Optional[Dict]:
        """
        Scrape a specific tweet with its replies/comments
        
        Args:
            tweet_url: URL of the tweet
        
        Returns:
            Dictionary with tweet data and replies
        """
        # Extract username and tweet ID from URL
        match = re.search(r'(?:twitter|x|xcancel)\.com/([^/]+)/status/(\d+)', tweet_url)
        
        if not match:
            return {'error': 'Invalid tweet URL'}
        
        username = match.group(1)
        tweet_id = match.group(2)
        
        # Use xcancel direct tweet URL
        url = f"{self.base_url}/{username}/status/{tweet_id}"
        
        try:
            self._random_delay()
            response = self.session.get(url, headers=self._get_headers(), timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract main tweet
                main_tweet = soup.find('div', class_='main-tweet')
                if not main_tweet:
                    return {'error': 'Could not find main tweet'}
                
                # Extract main tweet content
                tweet_content = main_tweet.find('div', class_='tweet-content')
                text = tweet_content.get_text(strip=True) if tweet_content else ''
                
                # Extract stats
                stats = self._extract_stats(main_tweet)
                
                # Extract replies - they appear as timeline-items after the main tweet
                replies = []
                reply_section = soup.find('div', class_='replies')
                if reply_section:
                    reply_items = reply_section.find_all('div', class_='timeline-item')
                    
                    for reply in reply_items[:50]:  # Limit to 50 replies
                        try:
                            reply_content = reply.find('div', class_='tweet-content')
                            reply_text = reply_content.get_text(strip=True) if reply_content else ''
                            
                            reply_author = reply.find('a', class_='username')
                            reply_username = reply_author.get_text(strip=True) if reply_author else 'unknown'
                            
                            reply_stats = self._extract_stats(reply)
                            
                            replies.append({
                                'text': reply_text,
                                'author': reply_username,
                                'likes': reply_stats.get('likes', 0),
                                'created_at': '',  # Would need more parsing for timestamp
                            })
                        except:
                            continue
                
                return {
                    'id': tweet_id,
                    'text': text,
                    'author': f'@{username}',
                    'url': tweet_url,
                    'likes': stats.get('likes', 0),
                    'retweets': stats.get('retweets', 0),
                    'replies_count': stats.get('replies', 0),
                    'replies': replies,
                    'source': 'xcancel'
                }
                
        except Exception as e:
            return {'error': str(e)}
        
        return None
    
    def scrape_tweet(self, tweet_url: str) -> Optional[Dict]:
        """
        Scrape a specific tweet by URL
        """
        # Extract username and tweet ID from URL
        match = re.search(r'twitter\.com/([^/]+)/status/(\d+)', tweet_url)
        if not match:
            # Try xcancel URL format
            match = re.search(r'xcancel\.com/([^/]+)/status/(\d+)', tweet_url)
        
        if match:
            username = match.group(1)
            tweet_id = match.group(2)
            
            # Use xcancel direct tweet URL
            url = f"{self.base_url}/{username}/status/{tweet_id}"
            
            try:
                self._random_delay()
                response = self.session.get(url, headers=self._get_headers(), timeout=15)
                
                if response.status_code == 200:
                    # Parse the single tweet page
                    soup = BeautifulSoup(response.text, 'html.parser')
                    main_tweet = soup.find('div', class_='main-tweet')
                    
                    if main_tweet:
                        # Extract tweet data similar to timeline parsing
                        # ... (similar extraction logic)
                        pass
                        
            except Exception as e:
                return {'error': str(e)}
        
        return None


# Test if this module is run directly
if __name__ == "__main__":
    print("Testing xcancel Twitter Scraper...")
    scraper = XCancelTwitterScraper()
    
    # Test with a username
    print("\nFetching tweets from @elonmusk...")
    tweets = scraper.scrape_user_timeline("elonmusk", limit=5)
    
    for i, tweet in enumerate(tweets, 1):
        if 'error' in tweet:
            print(f"Error: {tweet['error']}")
        else:
            print(f"\n{i}. {tweet['text'][:100]}...")
            print(f"   Likes: {tweet['likes']:,} | Retweets: {tweet['retweets']:,}")