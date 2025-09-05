#!/usr/bin/env python3
"""
Advanced Social Media Scraper
Supports: Facebook, Twitter, Reddit with URL parsing and filtering
NOW WITH BREAKTHROUGH PUBLIC APIS!
"""

import re
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from urllib.parse import urlparse, parse_qs
import time

# Import breakthrough scrapers - handle import errors gracefully
try:
    from syndication_scraper import TwitterSyndicationScraper, InstagramPublicScraper
    BREAKTHROUGH_APIS = True
except ImportError:
    BREAKTHROUGH_APIS = False

class AdvancedScraper:
    """Universal social media scraper with URL detection and filtering"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        # Initialize breakthrough scrapers if available
        if BREAKTHROUGH_APIS:
            self.twitter_syndication = TwitterSyndicationScraper()
            self.instagram_public = InstagramPublicScraper()
        else:
            self.twitter_syndication = None
            self.instagram_public = None
        
        # URL patterns for different platforms
        self.url_patterns = {
            'facebook': {
                'post': r'facebook\.com/.+/posts/\d+',
                'page': r'facebook\.com/(?!groups)[^/]+/?$',
                'group': r'facebook\.com/groups/[^/]+',
                'profile': r'facebook\.com/profile\.php\?id=\d+'
            },
            'twitter': {
                'tweet': r'(twitter|x)\.com/\w+/status/\d+',
                'profile': r'(twitter|x)\.com/[^/]+/?$',
                'hashtag': r'(twitter|x)\.com/hashtag/\w+',
                'search': r'(twitter|x)\.com/search\?q='
            },
            'reddit': {
                'post': r'reddit\.com/r/\w+/comments/\w+',
                'subreddit': r'reddit\.com/r/\w+/?$',
                'user': r'reddit\.com/(u|user)/\w+',
                'search': r'reddit\.com/search/?\?q='
            }
        }
    
    def detect_platform_and_type(self, url: str) -> Dict:
        """Detect platform and content type from URL or identifier"""
        original_url = url
        url = url.lower().strip()
        
        # First check if it's a full URL
        if url.startswith(('http://', 'https://', 'www.')):
            # Normalize URL
            if url.startswith('www.'):
                url = 'https://' + url
            
            for platform, patterns in self.url_patterns.items():
                for content_type, pattern in patterns.items():
                    if re.search(pattern, url):
                        return {
                            'platform': platform,
                            'type': content_type,
                            'url': original_url,
                            'is_direct_link': True
                        }
        
        # Check for shorthand inputs
        if url.startswith('r/') or re.match(r'^/?r/\w+/?$', url):
            return {'platform': 'reddit', 'type': 'subreddit', 'url': original_url, 'is_direct_link': False}
        elif url.startswith('/r/'):
            return {'platform': 'reddit', 'type': 'subreddit', 'url': original_url.replace('/r/', 'r/'), 'is_direct_link': False}
        elif url.startswith('#'):
            return {'platform': 'twitter', 'type': 'hashtag', 'url': original_url, 'is_direct_link': False}
        elif url.startswith('@'):
            return {'platform': 'twitter', 'type': 'profile', 'url': original_url, 'is_direct_link': False}
        elif re.match(r'^[a-zA-Z0-9_]+$', url):
            # Plain text - could be subreddit or username
            return {'platform': 'auto', 'type': 'identifier', 'url': original_url, 'is_direct_link': False}
        
        return {'platform': 'unknown', 'type': 'unknown', 'url': original_url, 'is_direct_link': False}
    
    def scrape(self, 
               inputs: List[str], 
               filters: Optional[Dict] = None) -> List[Dict]:
        """
        Main scraping function with filtering
        
        Args:
            inputs: List of URLs or identifiers to scrape
            filters: Dictionary with filtering options:
                - date_from: Start date (datetime or string)
                - date_to: End date (datetime or string)
                - limit: Maximum number of results per source
                - content_type: Filter by type (post, comment, etc.)
                - min_engagement: Minimum engagement threshold
                - keywords: List of keywords to filter by
                - exclude_keywords: Keywords to exclude
        """
        
        results = []
        filters = filters or {}
        
        for input_str in inputs:
            # Detect platform and type
            source_info = self.detect_platform_and_type(input_str)
            
            # Route to appropriate scraper
            if source_info['platform'] == 'reddit':
                data = self.scrape_reddit(source_info, filters)
            elif source_info['platform'] == 'twitter':
                data = self.scrape_twitter(source_info, filters)
            elif source_info['platform'] == 'facebook':
                data = self.scrape_facebook(source_info, filters)
            else:
                print(f"Unknown platform for: {input_str}")
                continue
            
            # Apply filters
            filtered_data = self.apply_filters(data, filters)
            results.extend(filtered_data)
            
            # Rate limiting
            time.sleep(1)
        
        return results
    
    def scrape_reddit(self, source: Dict, filters: Dict) -> List[Dict]:
        """Scrape Reddit content using JSON API (no auth required)"""
        results = []
        url = source['url']
        
        # Add proper user agent for Reddit
        reddit_headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AdvancedScraper/1.0; +https://github.com/user/repo)'
        }
        
        try:
            # Handle different Reddit content types
            if source['type'] == 'subreddit':
                # Extract subreddit name
                subreddit = re.search(r'r/(\w+)', url)
                if subreddit:
                    subreddit_name = subreddit.group(1)
                else:
                    subreddit_name = url.replace('r/', '')
                
                # Get posts from subreddit - Reddit JSON API works great!
                api_url = f"https://www.reddit.com/r/{subreddit_name}/hot.json"
                params = {'limit': filters.get('limit', 25)}
                
                response = self.session.get(api_url, params=params, headers=reddit_headers)
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data['data']['children']:
                        post = item['data']
                        fetch_comments = filters.get('fetch_comments', True)
                        results.append(self.format_reddit_post(post, fetch_comments=fetch_comments))
            
            elif source['type'] == 'post':
                # Get specific post with comments
                if not url.endswith('.json'):
                    post_url = url + '.json'
                else:
                    post_url = url
                response = self.session.get(post_url, headers=reddit_headers)
                
                if response.status_code == 200:
                    data = response.json()
                    # First item is the post
                    if data and len(data) > 0:
                        post_data = data[0]['data']['children'][0]['data']
                        fetch_comments = filters.get('fetch_comments', True)
                        results.append(self.format_reddit_post(post_data, fetch_comments=fetch_comments))
                        
                        # Get comments if available
                        if len(data) > 1:
                            for comment in data[1]['data']['children'][:10]:
                                if comment['kind'] == 't1':  # Comment
                                    results.append(self.format_reddit_comment(comment['data']))
            
            elif source['type'] == 'user':
                # Get user posts
                username = re.search(r'(u|user)/(\w+)', url)
                if username:
                    username = username.group(2)
                    api_url = f"https://www.reddit.com/user/{username}/submitted.json"
                    params = {'limit': filters.get('limit', 25)}
                    
                    response = self.session.get(api_url, params=params, headers=reddit_headers)
                    if response.status_code == 200:
                        data = response.json()
                        for item in data['data']['children']:
                            post = item['data']
                            # Fetch comments for each post
                            fetch_comments = filters.get('fetch_comments', True)
                            results.append(self.format_reddit_post(post, fetch_comments=fetch_comments))
                            
        except Exception as e:
            print(f"Error scraping Reddit: {e}")
        
        return results
    
    def scrape_reddit_comments(self, post_url: str, max_depth: int = 10) -> List[Dict]:
        """
        Scrape ALL comments from a Reddit post recursively
        
        Args:
            post_url: URL of the Reddit post
            max_depth: Maximum depth for nested comments
        
        Returns:
            List of all comments with full details
        """
        comments = []
        
        try:
            # Convert URL to API endpoint
            if '.json' not in post_url:
                api_url = post_url.rstrip('/') + '.json'
            else:
                api_url = post_url
            
            response = self.session.get(api_url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                data = response.json()
                
                # The second item in the array contains comments
                if len(data) > 1 and 'data' in data[1]:
                    comment_data = data[1]['data']['children']
                    comments = self._parse_comments_recursive(comment_data, depth=0, max_depth=max_depth)
                    
        except Exception as e:
            print(f"Error scraping Reddit comments: {e}")
        
        return comments
    
    def _parse_comments_recursive(self, comment_list, depth=0, max_depth=10) -> List[Dict]:
        """Recursively parse all comments including nested replies (flattened)"""
        parsed_comments = []
        
        for item in comment_list:
            if item['kind'] == 't1':  # t1 = comment
                comment = item['data']
                
                # Parse comment even if deleted/removed (to show thread structure)
                parsed_comment = {
                    'id': comment.get('id'),
                    'author': comment.get('author', '[deleted]'),
                    'text': comment.get('body', '[deleted]'),
                    'score': comment.get('score', 0),
                    'created_at': datetime.fromtimestamp(comment.get('created_utc', 0)).isoformat(),
                    'edited': comment.get('edited', False),
                    'is_submitter': comment.get('is_submitter', False),
                    'distinguished': comment.get('distinguished'),  # mod/admin status
                    'awards': comment.get('total_awards_received', 0),
                    'controversiality': comment.get('controversiality', 0),
                    'depth': depth,
                    'permalink': f"https://reddit.com{comment.get('permalink', '')}",
                    'parent_id': comment.get('parent_id', '').replace('t1_', '').replace('t3_', ''),
                    'is_deleted': comment.get('body') in ['[deleted]', '[removed]']
                }
                
                # Add this comment to the flattened list
                parsed_comments.append(parsed_comment)
                
                # Parse nested replies and add them to the same flat list
                if depth < max_depth and comment.get('replies') and isinstance(comment['replies'], dict):
                    if 'data' in comment['replies'] and 'children' in comment['replies']['data']:
                        nested_comments = self._parse_comments_recursive(
                            comment['replies']['data']['children'],
                            depth=depth + 1,
                            max_depth=max_depth
                        )
                        # Add all nested comments to our flat list
                        parsed_comments.extend(nested_comments)
                
            elif item['kind'] == 'more':
                # Handle "load more comments" links
                more_data = item.get('data', {})
                if more_data.get('children') and more_data.get('count', 0) > 0:
                    # Add a placeholder to indicate more comments available
                    parsed_comments.append({
                        'type': 'more_comments',
                        'count': more_data.get('count', len(more_data['children'])),
                        'depth': depth,
                        'parent_id': more_data.get('parent_id', '').replace('t1_', '').replace('t3_', ''),
                        'comment_ids': more_data.get('children', [])
                    })
                
        return parsed_comments
    
    def format_reddit_post(self, post: Dict, fetch_comments: bool = True) -> Dict:
        """Format Reddit post data with optional comment fetching"""
        formatted_post = {
            'platform': 'reddit',
            'type': 'post',
            'id': post.get('id'),
            'author': post.get('author', '[deleted]'),
            'title': post.get('title', ''),
            'content': post.get('selftext', '')[:1000],
            'url': f"https://reddit.com{post.get('permalink', '')}",
            'created_at': datetime.fromtimestamp(post.get('created_utc', 0)).isoformat(),
            'subreddit': post.get('subreddit', ''),
            'engagement': {
                'score': post.get('score', 0),
                'comments': post.get('num_comments', 0),
                'upvote_ratio': post.get('upvote_ratio', 0)
            },
            'media': {
                'has_media': bool(post.get('media')),
                'thumbnail': post.get('thumbnail') if post.get('thumbnail') not in ['self', 'default'] else None
            },
            'flair': post.get('link_flair_text'),
            'awards': post.get('total_awards_received', 0)
        }
        
        # Fetch all comments if requested
        if fetch_comments and post.get('permalink'):
            post_url = f"https://reddit.com{post.get('permalink')}"
            formatted_post['comments'] = self.scrape_reddit_comments(post_url)
        
        return formatted_post
    
    def format_reddit_comment(self, comment: Dict) -> Dict:
        """Format Reddit comment data"""
        return {
            'platform': 'reddit',
            'type': 'comment',
            'id': comment.get('id'),
            'author': comment.get('author', '[deleted]'),
            'content': comment.get('body', '')[:500],
            'url': f"https://reddit.com{comment.get('permalink', '')}",
            'created_at': datetime.fromtimestamp(comment.get('created_utc', 0)).isoformat(),
            'engagement': {
                'score': comment.get('score', 0),
                'awards': comment.get('total_awards_received', 0)
            }
        }
    
    def scrape_twitter(self, source: Dict, filters: Dict) -> List[Dict]:
        """Scrape Twitter/X content using breakthrough Syndication API"""
        results = []
        
        # Use the breakthrough syndication API if available
        if self.twitter_syndication:
            if source['type'] == 'profile':
                username = source['url'].split('/')[-1].replace('@', '')
                
                # Use the syndication API - works without any authentication!
                try:
                    tweets = self.twitter_syndication.scrape_user_timeline(
                        username, 
                        limit=filters.get('limit', 20)
                    )
                    
                    for tweet in tweets:
                        results.append({
                            'platform': 'twitter',
                            'type': 'tweet',
                            'id': tweet.get('id'),
                            'username': username,
                            'content': tweet.get('text', ''),
                            'url': tweet.get('permalink'),
                            'created_at': tweet.get('created_at'),
                            'engagement': {
                                'likes': tweet.get('likes', 0),
                                'retweets': tweet.get('retweets', 0),
                                'replies': tweet.get('replies', 0),
                                'quotes': tweet.get('quotes', 0)
                            },
                            'media': tweet.get('media', []),
                            'lang': tweet.get('lang'),
                            'possibly_sensitive': tweet.get('possibly_sensitive', False),
                            'source': 'syndication_api'
                        })
                    
                    if not tweets:
                        results.append({
                            'platform': 'twitter',
                            'type': 'error',
                            'username': username,
                            'error': 'No tweets found',
                            'note': 'User may be private or have no recent tweets'
                        })
                        
                except Exception as e:
                    results.append({
                        'platform': 'twitter',
                        'type': 'error',
                        'username': username,
                        'error': str(e),
                        'note': 'Syndication API error'
                    })
            
            elif source['type'] == 'tweet':
                # Try to scrape specific tweet
                tweet = self.twitter_syndication.scrape_tweet(source['url'])
                if tweet:
                    results.append({
                        'platform': 'twitter',
                        'type': 'tweet',
                        'id': tweet.get('id'),
                        'content': tweet.get('text', ''),
                        'url': tweet.get('permalink'),
                        'created_at': tweet.get('created_at'),
                        'engagement': {
                            'likes': tweet.get('likes', 0),
                            'retweets': tweet.get('retweets', 0),
                            'replies': tweet.get('replies', 0),
                            'quotes': tweet.get('quotes', 0)
                        },
                        'media': tweet.get('media', []),
                        'source': 'syndication_api'
                    })
                    
        else:
            # Fallback if syndication API not available
            results.append({
                'platform': 'twitter',
                'type': 'error',
                'url': source['url'],
                'error': 'Syndication API not available',
                'note': 'Please ensure syndication_scraper.py is in the same directory'
            })
        
        return results
    
    def scrape_facebook(self, source: Dict, filters: Dict) -> List[Dict]:
        """Scrape Facebook content with fallback methods"""
        results = []
        
        # Try CloudScraper for better success
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
        except ImportError:
            scraper = self.session
        
        # Try mbasic Facebook (mobile basic version)
        if source['type'] == 'page':
            page_name = source['url'].split('/')[-1]
            
            try:
                # Try mbasic version
                mbasic_url = f"https://mbasic.facebook.com/{page_name}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36'
                }
                
                response = scraper.get(mbasic_url, headers=headers, timeout=10, allow_redirects=True)
                
                if response.status_code == 200 and 'login' not in response.url.lower():
                    results.append({
                        'platform': 'facebook',
                        'type': 'page_info',
                        'page': page_name,
                        'url': source['url'],
                        'note': 'Limited access - Facebook requires login for full content',
                        'created_at': datetime.now().isoformat()
                    })
                else:
                    results.append({
                        'platform': 'facebook',
                        'type': source['type'],
                        'url': source['url'],
                        'error': 'Login required',
                        'note': 'Facebook requires authentication',
                        'alternatives': [
                            'Use Facebook Graph API with access token',
                            'Use official Facebook data export',
                            'Consider browser automation with login'
                        ],
                        'created_at': datetime.now().isoformat()
                    })
            except Exception as e:
                results.append({
                    'platform': 'facebook',
                    'type': 'error',
                    'url': source['url'],
                    'error': str(e),
                    'created_at': datetime.now().isoformat()
                })
        else:
            results.append({
                'platform': 'facebook',
                'type': source['type'],
                'url': source['url'],
                'note': 'Facebook scraping requires authentication',
                'created_at': datetime.now().isoformat()
            })
        
        return results
    
    def apply_filters(self, data: List[Dict], filters: Dict) -> List[Dict]:
        """Apply filtering to scraped data"""
        if not filters:
            return data
        
        filtered = data
        
        # Date filtering
        if 'date_from' in filters or 'date_to' in filters:
            date_from = self.parse_date(filters.get('date_from'))
            date_to = self.parse_date(filters.get('date_to'))
            
            filtered = [
                item for item in filtered
                if self.is_within_date_range(item.get('created_at'), date_from, date_to)
            ]
        
        # Engagement filtering
        if 'min_engagement' in filters and filters['min_engagement'] is not None:
            min_eng = filters['min_engagement']
            filtered = [
                item for item in filtered
                if self.get_total_engagement(item) >= min_eng
            ]
        
        # Keyword filtering
        if 'keywords' in filters:
            keywords = filters['keywords']
            filtered = [
                item for item in filtered
                if self.contains_keywords(item, keywords)
            ]
        
        # Exclude keywords
        if 'exclude_keywords' in filters:
            exclude = filters['exclude_keywords']
            filtered = [
                item for item in filtered
                if not self.contains_keywords(item, exclude)
            ]
        
        # Content type filtering
        if 'content_type' in filters:
            content_type = filters['content_type']
            filtered = [
                item for item in filtered
                if item.get('type') == content_type
            ]
        
        # Limit results
        if 'limit' in filters:
            filtered = filtered[:filters['limit']]
        
        return filtered
    
    def parse_date(self, date_input: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse various date formats with robust handling"""
        if not date_input:
            return None
        
        if isinstance(date_input, datetime):
            return date_input
        
        # Try parsing string dates
        if isinstance(date_input, str):
            date_input = date_input.strip()
            
            # Handle relative dates
            now = datetime.now()
            if date_input.lower() == 'today':
                return now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif date_input.lower() == 'yesterday':
                return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif date_input.lower() == 'tomorrow':
                return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Handle "last X" format
            if date_input.lower().startswith('last'):
                parts = date_input.lower().split()
                if len(parts) >= 2:
                    time_map = {
                        'hour': timedelta(hours=1),
                        'day': timedelta(days=1),
                        'week': timedelta(weeks=1),
                        'month': timedelta(days=30),
                        'year': timedelta(days=365)
                    }
                    
                    # Handle "last 7 days" format
                    if len(parts) == 3 and parts[1].isdigit():
                        num = int(parts[1])
                        unit = parts[2].rstrip('s')  # Remove plural 's'
                        if unit in time_map:
                            return now - (time_map[unit] * num)
                    
                    # Handle "last week/month/year" format
                    elif len(parts) == 2:
                        unit = parts[1]
                        if unit in time_map:
                            return now - time_map[unit]
            
            # Try parsing ISO format and variants
            for fmt in [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%m-%d-%Y',
                '%d-%m-%Y',
                '%Y/%m/%d',
                '%B %d, %Y',  # January 1, 2024
                '%b %d, %Y',  # Jan 1, 2024
                '%d %B %Y',   # 1 January 2024
                '%d %b %Y'    # 1 Jan 2024
            ]:
                try:
                    return datetime.strptime(date_input, fmt)
                except:
                    pass
            
            # Try parsing with dateutil if available
            try:
                from dateutil import parser
                return parser.parse(date_input)
            except:
                pass
        
        return None
    
    def is_within_date_range(self, date_str: str, date_from: Optional[datetime], date_to: Optional[datetime]) -> bool:
        """Check if date is within range"""
        if not date_str:
            return True
        
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            if date_from and date < date_from:
                return False
            if date_to and date > date_to:
                return False
            
            return True
        except:
            return True
    
    def get_total_engagement(self, item: Dict) -> int:
        """Calculate total engagement for an item"""
        engagement = item.get('engagement', {})
        total = 0
        
        for key, value in engagement.items():
            if isinstance(value, (int, float)):
                total += value
        
        return total
    
    def contains_keywords(self, item: Dict, keywords: List[str]) -> bool:
        """Check if item contains any of the keywords"""
        if not keywords:
            return True
        
        # Combine searchable text
        searchable = ' '.join([
            str(item.get('title', '')),
            str(item.get('content', '')),
            str(item.get('author', ''))
        ]).lower()
        
        return any(keyword.lower() in searchable for keyword in keywords)
    
    def export_results(self, results: List[Dict], format: str = 'json', filename: str = None):
        """Export results to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"scrape_results_{timestamp}.{format}"
        
        if format == 'json':
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        elif format == 'csv':
            import csv
            
            if not results:
                return filename
            
            # Get all unique keys
            keys = set()
            for item in results:
                keys.update(self.flatten_dict(item).keys())
            keys = sorted(list(keys))
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                
                for item in results:
                    flat_item = self.flatten_dict(item)
                    writer.writerow(flat_item)
        
        print(f"Results exported to {filename}")
        return filename
    
    def flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten nested dictionary for CSV export"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
        return dict(items)


# Example usage
def example_usage():
    scraper = AdvancedScraper()
    
    print("\n📊 Testing Advanced Scraper with working methods...\n")
    
    # Focus on what actually works: Reddit
    inputs = [
        'https://reddit.com/r/technology',
        'https://reddit.com/r/worldnews',
        'r/science',  # Shorthand
        # Twitter and Facebook have limited functionality without auth
        # '@elonmusk',  # Twitter - limited without API
        # 'https://facebook.com/Meta'  # Facebook - requires login
    ]
    
    filters = {
        'limit': 10,
        'date_from': 'last_week',
        'min_engagement': 100,
        'keywords': ['AI', 'technology', 'innovation'],
        'exclude_keywords': ['spam', 'ad'],
        'content_type': 'post'
    }
    
    results = scraper.scrape(inputs, filters)
    
    # Export results
    scraper.export_results(results, format='json')
    scraper.export_results(results, format='csv')
    
    return results


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     ADVANCED SOCIAL MEDIA SCRAPER                       ║
    ║     Supports: URLs, Filtering, Multiple Platforms       ║
    ║                                                          ║
    ║     ✓ Reddit: Full support via JSON API (no auth)       ║
    ║     ⚠ Twitter: Limited without API keys                 ║
    ║     ⚠ Facebook: Requires authentication                 ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    print("\n💡 TIP: Reddit works best without authentication!")
    print("   For Twitter/Facebook, consider using official APIs.\n")
    
    results = example_usage()
    print(f"\nScraped {len(results)} items")
    
    for result in results[:3]:
        print(f"\n{result['platform']} - {result['type']}")
        print(f"  Author: {result.get('author', 'N/A')}")
        print(f"  Content: {str(result.get('content', result.get('title', '')))[:100]}...")