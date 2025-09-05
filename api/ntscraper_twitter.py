#!/usr/bin/env python3
"""
Twitter scraper using ntscraper library
"""

try:
    from ntscraper import Nitter
    NTSCRAPER_AVAILABLE = True
except ImportError:
    NTSCRAPER_AVAILABLE = False

import time
import random
from typing import List, Dict, Optional
from datetime import datetime

class NTScraperTwitter:
    """
    Twitter scraper using ntscraper which rotates through working Nitter instances
    """
    
    def __init__(self):
        if NTSCRAPER_AVAILABLE:
            # Initialize with random instance selection
            self.scraper = Nitter(log_level=1, skip_instance_check=False)
            self.last_request_time = 0
            self.min_delay = 1.0  # Minimum delay between requests
        else:
            self.scraper = None
    
    def _rate_limit(self):
        """Add delay between requests to avoid rate limiting"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed + random.uniform(0.1, 0.5))
        self.last_request_time = time.time()
    
    def scrape_user_timeline(self, username: str, limit: int = 50) -> List[Dict]:
        """
        Scrape a user's timeline using ntscraper
        """
        if not NTSCRAPER_AVAILABLE:
            return [{'error': 'ntscraper not installed'}]
        
        username = username.lstrip('@').lower()
        
        try:
            self._rate_limit()
            
            # Get tweets from user
            tweets = self.scraper.get_tweets(username, mode='user', number=limit)
            
            if not tweets:
                return [{'error': f'No tweets found for @{username}'}]
            
            results = []
            for tweet in tweets:
                # Extract tweet data
                tweet_data = {
                    'id': tweet.get('link', '').split('/')[-1] if tweet.get('link') else None,
                    'text': tweet.get('text', ''),
                    'author': f'@{username}',
                    'author_name': tweet.get('name', username),
                    'created_at': tweet.get('date', ''),
                    'url': tweet.get('link', ''),
                    'likes': self._parse_stats(tweet.get('stats', {}).get('likes', 0)),
                    'retweets': self._parse_stats(tweet.get('stats', {}).get('retweets', 0)),
                    'replies': self._parse_stats(tweet.get('stats', {}).get('comments', 0)),
                    'quotes': self._parse_stats(tweet.get('stats', {}).get('quotes', 0)),
                    'is_retweet': tweet.get('is_retweet', False),
                    'is_pinned': tweet.get('is_pinned', False),
                    'has_media': bool(tweet.get('pictures', [])) or bool(tweet.get('videos', [])),
                    'media': self._extract_media(tweet),
                    'source': 'ntscraper'
                }
                results.append(tweet_data)
            
            return results
            
        except Exception as e:
            return [{'error': f'Failed to scrape timeline: {str(e)}'}]
    
    def search_tweets(self, query: str, limit: int = 50) -> List[Dict]:
        """
        Search for tweets using ntscraper
        """
        if not NTSCRAPER_AVAILABLE:
            return [{'error': 'ntscraper not installed'}]
        
        try:
            self._rate_limit()
            
            # Determine search mode
            if query.startswith('#'):
                mode = 'hashtag'
                search_term = query[1:]  # Remove #
            else:
                mode = 'term'
                search_term = query
            
            # Search tweets
            tweets = self.scraper.get_tweets(search_term, mode=mode, number=limit)
            
            if not tweets:
                return [{'error': f'No tweets found for query: {query}'}]
            
            results = []
            for tweet in tweets:
                tweet_data = {
                    'id': tweet.get('link', '').split('/')[-1] if tweet.get('link') else None,
                    'text': tweet.get('text', ''),
                    'author': tweet.get('username', ''),
                    'author_name': tweet.get('name', ''),
                    'created_at': tweet.get('date', ''),
                    'url': tweet.get('link', ''),
                    'likes': self._parse_stats(tweet.get('stats', {}).get('likes', 0)),
                    'retweets': self._parse_stats(tweet.get('stats', {}).get('retweets', 0)),
                    'replies': self._parse_stats(tweet.get('stats', {}).get('comments', 0)),
                    'quotes': self._parse_stats(tweet.get('stats', {}).get('quotes', 0)),
                    'search_query': query,
                    'has_media': bool(tweet.get('pictures', [])) or bool(tweet.get('videos', [])),
                    'media': self._extract_media(tweet),
                    'source': 'ntscraper_search'
                }
                results.append(tweet_data)
            
            return results
            
        except Exception as e:
            return [{'error': f'Search failed: {str(e)}'}]
    
    def get_tweet_with_replies(self, tweet_url: str) -> Optional[Dict]:
        """
        Get a single tweet with its replies
        """
        if not NTSCRAPER_AVAILABLE:
            return {'error': 'ntscraper not installed'}
        
        try:
            # Extract tweet ID from URL
            import re
            match = re.search(r'/status/(\d+)', tweet_url)
            if not match:
                return {'error': 'Invalid tweet URL'}
            
            tweet_id = match.group(1)
            
            self._rate_limit()
            
            # Get the tweet (ntscraper doesn't have direct reply fetching)
            # We'll get the tweet and note that replies aren't available
            tweet = self.scraper.get_tweet(tweet_id)
            
            if not tweet:
                return {'error': 'Tweet not found'}
            
            return {
                'id': tweet_id,
                'text': tweet.get('text', ''),
                'author': tweet.get('username', ''),
                'author_name': tweet.get('name', ''),
                'created_at': tweet.get('date', ''),
                'url': tweet_url,
                'likes': self._parse_stats(tweet.get('stats', {}).get('likes', 0)),
                'retweets': self._parse_stats(tweet.get('stats', {}).get('retweets', 0)),
                'replies_count': self._parse_stats(tweet.get('stats', {}).get('comments', 0)),
                'quotes': self._parse_stats(tweet.get('stats', {}).get('quotes', 0)),
                'media': self._extract_media(tweet),
                'replies': [],  # ntscraper doesn't fetch replies
                'note': 'Reply fetching not available through ntscraper',
                'source': 'ntscraper'
            }
            
        except Exception as e:
            return {'error': f'Failed to fetch tweet: {str(e)}'}
    
    def get_profile_info(self, username: str) -> Optional[Dict]:
        """
        Get profile information for a user
        """
        if not NTSCRAPER_AVAILABLE:
            return {'error': 'ntscraper not installed'}
        
        username = username.lstrip('@').lower()
        
        try:
            self._rate_limit()
            
            profile = self.scraper.get_profile_info(username)
            
            if not profile:
                return {'error': f'Profile not found for @{username}'}
            
            return {
                'username': f'@{username}',
                'name': profile.get('name', ''),
                'bio': profile.get('bio', ''),
                'location': profile.get('location', ''),
                'website': profile.get('website', ''),
                'joined': profile.get('joined', ''),
                'tweets_count': self._parse_stats(profile.get('stats', {}).get('tweets', 0)),
                'following': self._parse_stats(profile.get('stats', {}).get('following', 0)),
                'followers': self._parse_stats(profile.get('stats', {}).get('followers', 0)),
                'likes': self._parse_stats(profile.get('stats', {}).get('likes', 0)),
                'is_verified': profile.get('verified', False),
                'is_private': profile.get('protected', False),
                'profile_image': profile.get('image', ''),
                'banner_image': profile.get('banner', ''),
                'source': 'ntscraper_profile'
            }
            
        except Exception as e:
            return {'error': f'Failed to fetch profile: {str(e)}'}
    
    def _parse_stats(self, stat_value) -> int:
        """Parse stat values that might be strings like '1.2K' or '3M'"""
        if isinstance(stat_value, int):
            return stat_value
        
        if isinstance(stat_value, str):
            stat_value = stat_value.strip().replace(',', '')
            
            if 'K' in stat_value.upper():
                try:
                    return int(float(stat_value.upper().replace('K', '')) * 1000)
                except:
                    return 0
            elif 'M' in stat_value.upper():
                try:
                    return int(float(stat_value.upper().replace('M', '')) * 1000000)
                except:
                    return 0
            else:
                try:
                    return int(stat_value)
                except:
                    return 0
        
        return 0
    
    def _extract_media(self, tweet: Dict) -> List[Dict]:
        """Extract media information from tweet"""
        media = []
        
        # Extract pictures
        if tweet.get('pictures'):
            for pic_url in tweet['pictures']:
                media.append({
                    'type': 'image',
                    'url': pic_url
                })
        
        # Extract videos
        if tweet.get('videos'):
            for video_url in tweet['videos']:
                media.append({
                    'type': 'video',
                    'url': video_url
                })
        
        # Extract gifs
        if tweet.get('gifs'):
            for gif_url in tweet['gifs']:
                media.append({
                    'type': 'gif',
                    'url': gif_url
                })
        
        return media


# Test if run directly
if __name__ == "__main__":
    print(f"Testing ntscraper Twitter scraper (available: {NTSCRAPER_AVAILABLE})")
    
    if NTSCRAPER_AVAILABLE:
        scraper = NTScraperTwitter()
        
        # Test timeline
        print("\n1. Testing timeline for @nasa...")
        tweets = scraper.scrape_user_timeline("nasa", limit=3)
        if tweets and not any('error' in t for t in tweets):
            print(f"✅ Found {len(tweets)} tweets")
            for tweet in tweets[:2]:
                print(f"  - {tweet['text'][:80]}...")
                print(f"    Likes: {tweet['likes']} | Retweets: {tweet['retweets']}")
        else:
            print(f"❌ Failed: {tweets}")
        
        # Test search
        print("\n2. Testing search for 'AI'...")
        results = scraper.search_tweets("AI", limit=3)
        if results and not any('error' in r for r in results):
            print(f"✅ Found {len(results)} search results")
            for result in results[:2]:
                print(f"  - @{result['author']}: {result['text'][:60]}...")
        else:
            print(f"❌ Failed: {results}")
        
        # Test profile
        print("\n3. Testing profile info for @elonmusk...")
        profile = scraper.get_profile_info("elonmusk")
        if profile and 'error' not in profile:
            print(f"✅ Got profile: {profile['name']}")
            print(f"   Followers: {profile['followers']:,}")
            print(f"   Tweets: {profile['tweets_count']:,}")
        else:
            print(f"❌ Failed: {profile}")
    else:
        print("❌ ntscraper not installed")