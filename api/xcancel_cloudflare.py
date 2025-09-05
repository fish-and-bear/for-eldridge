#!/usr/bin/env python3
"""
xcancel Twitter Scraper with Cloudflare bypass
"""

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False
    import requests

import time
import random
import re
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup

class XCancelCloudflare:
    """
    xcancel scraper with Cloudflare bypass capabilities
    """
    
    def __init__(self):
        self.base_url = "https://xcancel.com"
        
        if CLOUDSCRAPER_AVAILABLE:
            # Use cloudscraper to bypass Cloudflare
            self.session = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'darwin',
                    'desktop': True
                }
            )
        else:
            # Fallback to regular requests
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
    
    def scrape_user_timeline(self, username: str, limit: int = 50) -> List[Dict]:
        """
        Scrape a user's timeline from xcancel
        """
        username = username.lstrip('@').lower()
        url = f"{self.base_url}/{username}"
        
        try:
            # Add delay to appear more human
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tweets = []
                
                # Find all timeline items
                timeline_items = soup.find_all('div', class_='timeline-item')
                
                if not timeline_items:
                    # Try alternative structure
                    timeline_items = soup.find_all('article', class_='timeline-item')
                
                for item in timeline_items[:limit]:
                    try:
                        tweet_data = self._extract_tweet_from_item(item, username)
                        if tweet_data:
                            tweets.append(tweet_data)
                    except Exception as e:
                        continue
                
                return tweets
            else:
                return [{'error': f'Failed to fetch timeline: HTTP {response.status_code}'}]
                
        except Exception as e:
            return [{'error': f'Error fetching timeline: {str(e)}'}]
    
    def search_tweets(self, query: str, limit: int = 50) -> List[Dict]:
        """
        Search for tweets on xcancel
        """
        url = f"{self.base_url}/search"
        params = {
            'f': 'tweets',
            'q': query
        }
        
        try:
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tweets = []
                
                # Find search results
                timeline_items = soup.find_all('div', class_='timeline-item')
                
                for item in timeline_items[:limit]:
                    try:
                        tweet_data = self._extract_tweet_from_item(item)
                        if tweet_data:
                            tweet_data['search_query'] = query
                            tweets.append(tweet_data)
                    except Exception:
                        continue
                
                return tweets
            else:
                return [{'error': f'Search failed: HTTP {response.status_code}'}]
                
        except Exception as e:
            return [{'error': f'Search error: {str(e)}'}]
    
    def get_tweet_with_replies(self, tweet_url: str) -> Optional[Dict]:
        """
        Get a tweet with all its replies
        """
        # Extract username and tweet ID
        match = re.search(r'(?:twitter|x|xcancel)\.com/([^/]+)/status/(\d+)', tweet_url)
        if not match:
            return {'error': 'Invalid tweet URL'}
        
        username = match.group(1)
        tweet_id = match.group(2)
        url = f"{self.base_url}/{username}/status/{tweet_id}"
        
        try:
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract main tweet
                main_tweet = soup.find('div', class_='main-tweet')
                if not main_tweet:
                    main_tweet = soup.find('article', class_='main-tweet')
                
                if main_tweet:
                    tweet_data = self._extract_tweet_from_item(main_tweet, username)
                    
                    # Extract replies
                    replies = []
                    reply_section = soup.find('div', class_='replies')
                    if not reply_section:
                        reply_section = soup.find('div', class_='thread')
                    
                    if reply_section:
                        reply_items = reply_section.find_all('div', class_='timeline-item')
                        
                        for reply in reply_items[:100]:  # Limit replies
                            try:
                                reply_data = self._extract_tweet_from_item(reply)
                                if reply_data:
                                    replies.append(reply_data)
                            except:
                                continue
                    
                    tweet_data['replies'] = replies
                    tweet_data['replies_count'] = len(replies)
                    
                    return tweet_data
                
            return {'error': f'Failed to fetch tweet: HTTP {response.status_code}'}
            
        except Exception as e:
            return {'error': f'Error fetching tweet: {str(e)}'}
    
    def _extract_tweet_from_item(self, item, default_username: str = None) -> Optional[Dict]:
        """
        Extract tweet data from a timeline item
        """
        try:
            # Extract tweet ID
            tweet_link = item.find('a', class_='tweet-link')
            if not tweet_link:
                tweet_link = item.find('a', href=re.compile(r'/status/\d+'))
            
            if not tweet_link:
                return None
            
            href = tweet_link.get('href', '')
            tweet_id_match = re.search(r'/status/(\d+)', href)
            tweet_id = tweet_id_match.group(1) if tweet_id_match else None
            
            # Extract username
            username_match = re.search(r'/([^/]+)/status/', href)
            username = username_match.group(1) if username_match else default_username
            
            # Extract text
            tweet_content = item.find('div', class_='tweet-content')
            if not tweet_content:
                tweet_content = item.find('div', class_='tweet-text')
            text = tweet_content.get_text(strip=True) if tweet_content else ''
            
            # Extract author info
            fullname = item.find('a', class_='fullname')
            username_elem = item.find('a', class_='username')
            author_name = fullname.get_text(strip=True) if fullname else username
            author_username = username_elem.get_text(strip=True) if username_elem else f'@{username}'
            
            # Extract timestamp
            tweet_date = item.find('span', class_='tweet-date')
            if tweet_date:
                date_link = tweet_date.find('a')
                timestamp = date_link.get('title', '') if date_link else ''
            else:
                timestamp = datetime.now().isoformat()
            
            # Extract engagement stats
            stats = self._extract_stats(item)
            
            # Extract media
            media_items = []
            attachments = item.find('div', class_='attachments')
            if attachments:
                images = attachments.find_all('img')
                for img in images:
                    src = img.get('src', '')
                    if src:
                        if not src.startswith('http'):
                            src = f"{self.base_url}{src}"
                        media_items.append({
                            'type': 'image',
                            'url': src
                        })
            
            return {
                'id': tweet_id,
                'text': text,
                'author': author_username,
                'author_name': author_name,
                'created_at': timestamp,
                'url': f"https://twitter.com/{username}/status/{tweet_id}" if tweet_id else '',
                'likes': stats.get('likes', 0),
                'retweets': stats.get('retweets', 0),
                'replies': stats.get('replies', 0),
                'quotes': stats.get('quotes', 0),
                'media': media_items,
                'source': 'xcancel_cloudflare'
            }
            
        except Exception as e:
            return None
    
    def _extract_stats(self, item) -> Dict:
        """
        Extract engagement statistics from a timeline item
        """
        stats = {}
        
        # Look for stat elements
        stat_elements = item.find_all('span', class_='tweet-stat')
        
        for stat in stat_elements:
            # Look for icon to identify stat type
            icon = stat.find('span', class_=re.compile(r'icon-'))
            if icon:
                icon_classes = icon.get('class', [])
                value_text = stat.get_text(strip=True)
                
                # Extract number
                value_match = re.search(r'[\d,]+[KM]?', value_text)
                if value_match:
                    value_str = value_match.group()
                    value = self._parse_count(value_str)
                else:
                    value = 0
                
                # Map icon to stat type
                if any('comment' in cls or 'reply' in cls for cls in icon_classes):
                    stats['replies'] = value
                elif any('retweet' in cls for cls in icon_classes):
                    stats['retweets'] = value
                elif any('heart' in cls or 'like' in cls for cls in icon_classes):
                    stats['likes'] = value
                elif any('quote' in cls for cls in icon_classes):
                    stats['quotes'] = value
        
        return stats
    
    def _parse_count(self, count_str: str) -> int:
        """
        Parse count strings like '1.2K' or '3M' to integers
        """
        if not count_str:
            return 0
        
        count_str = count_str.strip().replace(',', '')
        
        if 'K' in count_str:
            return int(float(count_str.replace('K', '')) * 1000)
        elif 'M' in count_str:
            return int(float(count_str.replace('M', '')) * 1000000)
        else:
            try:
                return int(count_str)
            except:
                return 0


# Test if run directly
if __name__ == "__main__":
    print(f"Testing xcancel scraper (cloudscraper available: {CLOUDSCRAPER_AVAILABLE})")
    
    scraper = XCancelCloudflare()
    
    # Test timeline
    print("\n1. Testing timeline for @nasa...")
    tweets = scraper.scrape_user_timeline("nasa", limit=3)
    if tweets and not any('error' in t for t in tweets):
        print(f"✅ Found {len(tweets)} tweets")
        for tweet in tweets[:2]:
            print(f"  - {tweet['text'][:80]}...")
    else:
        print(f"❌ Failed: {tweets}")
    
    # Test search
    print("\n2. Testing search for 'ai'...")
    results = scraper.search_tweets("ai", limit=3)
    if results and not any('error' in r for r in results):
        print(f"✅ Found {len(results)} search results")
        for result in results[:2]:
            print(f"  - {result['text'][:80]}...")
    else:
        print(f"❌ Failed: {results}")