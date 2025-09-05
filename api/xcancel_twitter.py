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
                        
                        # Extract engagement stats
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