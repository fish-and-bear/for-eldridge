import json
import os
import sys
from datetime import datetime

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import scraper modules with fallback
try:
    from social_scraper import AdvancedScraper
    from syndication_scraper import TwitterSyndicationScraper, InstagramPublicScraper
    SCRAPERS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    SCRAPERS_AVAILABLE = False

class UnifiedScraper:
    def __init__(self):
        if SCRAPERS_AVAILABLE:
            self.advanced_scraper = AdvancedScraper()
            self.twitter_scraper = TwitterSyndicationScraper()
            self.instagram_scraper = InstagramPublicScraper()
        else:
            self.advanced_scraper = None
            self.twitter_scraper = None
            self.instagram_scraper = None
    
    def scrape_twitter(self, sources, bearer_token, cookies):
        if not self.twitter_scraper:
            return [{"error": "Twitter scraper not available"}]
        
        results = []
        for source in sources:
            username = source.strip().replace('@', '')
            try:
                tweets = self.twitter_scraper.scrape_user_timeline(username, limit=20)
                for tweet in tweets:
                    results.append({
                        'platform': 'twitter',
                        'username': f'@{username}',
                        'text': tweet.get('text', ''),
                        'created_at': tweet.get('created_at', ''),
                        'likes': tweet.get('likes', 0),
                        'retweets': tweet.get('retweets', 0),
                        'url': tweet.get('permalink', '')
                    })
                if not tweets:
                    results.append({
                        'platform': 'twitter',
                        'username': f'@{username}',
                        'error': 'No tweets found'
                    })
            except Exception as e:
                results.append({
                    'platform': 'twitter',
                    'username': f'@{username}',
                    'error': str(e)
                })
        return results
    
    def scrape_instagram(self, sources, options):
        import requests
        from datetime import datetime
        
        results = []
        for source in sources:
            username = source.strip().replace('@', '')
            
            try:
                # Use Instagram's public web profile info API
                url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'X-IG-App-ID': '936619743392459'  # Instagram web app ID (public)
                }
                
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'data' in data and 'user' in data['data']:
                        user = data['data']['user']
                        
                        # Extract user info
                        profile = {
                            'platform': 'instagram',
                            'username': f'@{username}',
                            'full_name': user.get('full_name', ''),
                            'bio': user.get('biography', ''),
                            'followers': user.get('edge_followed_by', {}).get('count', 0),
                            'following': user.get('edge_follow', {}).get('count', 0),
                            'posts_count': user.get('edge_owner_to_timeline_media', {}).get('count', 0),
                            'is_verified': user.get('is_verified', False),
                            'is_private': user.get('is_private', False),
                            'profile_pic': user.get('profile_pic_url_hd'),
                            'external_url': user.get('external_url'),
                            'posts': []
                        }
                        
                        # Get recent posts
                        media = user.get('edge_owner_to_timeline_media', {})
                        edges = media.get('edges', [])
                        
                        for edge in edges[:8]:  # Get up to 8 recent posts
                            node = edge.get('node', {})
                            
                            post = {
                                'id': node.get('id'),
                                'shortcode': node.get('shortcode'),
                                'url': f"https://www.instagram.com/p/{node.get('shortcode')}/",
                                'caption': '',
                                'timestamp': node.get('taken_at_timestamp'),
                                'created_at': datetime.fromtimestamp(node.get('taken_at_timestamp', 0)).isoformat() if node.get('taken_at_timestamp') else '',
                                'likes': node.get('edge_liked_by', {}).get('count', 0),
                                'comments': node.get('edge_media_to_comment', {}).get('count', 0),
                                'is_video': node.get('is_video', False),
                                'thumbnail': node.get('thumbnail_src'),
                                'display_url': node.get('display_url'),
                                'dimensions': {
                                    'width': node.get('dimensions', {}).get('width', 0),
                                    'height': node.get('dimensions', {}).get('height', 0)
                                }
                            }
                            
                            # Get caption if available
                            caption_edges = node.get('edge_media_to_caption', {}).get('edges', [])
                            if caption_edges:
                                post['caption'] = caption_edges[0].get('node', {}).get('text', '')[:200]  # Limit caption length
                            
                            profile['posts'].append(post)
                        
                        results.append(profile)
                    else:
                        results.append({
                            'platform': 'instagram',
                            'username': f'@{username}',
                            'error': 'Profile not found or private'
                        })
                else:
                    results.append({
                        'platform': 'instagram',
                        'username': f'@{username}',
                        'error': f'HTTP {response.status_code}: Could not access profile'
                    })
                    
            except Exception as e:
                results.append({
                    'platform': 'instagram',
                    'username': f'@{username}',
                    'error': str(e)
                })
        return results
    
    def scrape_reddit(self, sources, options):
        import requests
        from datetime import datetime
        import time
        import random
        
        results = []
        print(f"Reddit scraping started with sources: {sources}")
        
        for source in sources:
            try:
                # Clean subreddit name
                subreddit = source.strip().replace('r/', '').replace('/', '')
                success = False
                
                # Multiple fallback strategies for Reddit - optimized for serverless
                strategies = [
                    # Strategy 1: Old Reddit - most reliable for serverless
                    {
                        'url': f"https://old.reddit.com/r/{subreddit}/hot.json?limit=10",
                        'headers': {
                            'User-Agent': 'Mozilla/5.0 (compatible; RedditScraper/1.0; +https://example.com)',
                            'Accept': 'application/json',
                            'Accept-Charset': 'utf-8',
                            'Cache-Control': 'no-cache'
                        }
                    },
                    # Strategy 2: Simple API call
                    {
                        'url': f"https://www.reddit.com/r/{subreddit}/.json?limit=10",
                        'headers': {
                            'User-Agent': 'python-requests/2.28.1 (RedditAPI)',
                            'Accept': 'application/json'
                        }
                    },
                    # Strategy 3: Raw JSON parameter
                    {
                        'url': f"https://www.reddit.com/r/{subreddit}.json?raw_json=1&limit=10",
                        'headers': {
                            'User-Agent': 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)',
                            'Accept': 'application/json, text/javascript, */*'
                        }
                    },
                    # Strategy 4: Mobile user agent
                    {
                        'url': f"https://www.reddit.com/r/{subreddit}/hot/.json?limit=10",
                        'headers': {
                            'User-Agent': 'RedditIsiOS/2021.45.0',
                            'Accept': 'application/json'
                        }
                    },
                    # Strategy 5: Curl-based approach
                    {
                        'url': f"https://old.reddit.com/r/{subreddit}/.json?sort=hot&limit=10",
                        'headers': {
                            'User-Agent': 'curl/7.84.0',
                            'Accept': 'application/json',
                            'Host': 'old.reddit.com'
                        }
                    }
                ]
                
                for i, strategy in enumerate(strategies):
                    if success:
                        break
                        
                    try:
                        print(f"Trying Reddit strategy {i+1} for r/{subreddit}")
                        
                        # Add small random delay to avoid rate limiting
                        time.sleep(random.uniform(0.1, 0.3))
                        
                        response = requests.get(
                            strategy['url'], 
                            headers=strategy['headers'], 
                            timeout=15,
                            allow_redirects=True
                        )
                        
                        print(f"Strategy {i+1} returned status: {response.status_code}")
                        
                        if response.status_code == 200:
                            try:
                                data = response.json()
                                posts = data.get('data', {}).get('children', [])
                                
                                if posts:
                                    print(f"Strategy {i+1} success: Found {len(posts)} posts")
                                    subreddit_posts = []
                                    
                                    for post_item in posts[:10]:
                                        post = post_item.get('data', {})
                                        
                                        subreddit_posts.append({
                                            'platform': 'reddit',
                                            'subreddit': f'r/{subreddit}',
                                            'title': post.get('title', ''),
                                            'text': post.get('selftext', '')[:500],
                                            'author': post.get('author', 'Unknown'),
                                            'score': post.get('score', 0),
                                            'comments': post.get('num_comments', 0),
                                            'url': f"https://reddit.com{post.get('permalink', '')}",
                                            'created_at': datetime.fromtimestamp(post.get('created_utc', 0)).isoformat() if post.get('created_utc') else '',
                                            'upvote_ratio': post.get('upvote_ratio', 0),
                                            'awards': post.get('total_awards_received', 0),
                                            'flair': post.get('link_flair_text'),
                                            'is_video': post.get('is_video', False),
                                            'thumbnail': post.get('thumbnail') if post.get('thumbnail') not in ['self', 'default'] else None,
                                            'strategy_used': f'strategy_{i+1}'
                                        })
                                    
                                    results.extend(subreddit_posts)
                                    success = True
                                    break
                            except (ValueError, KeyError) as json_error:
                                print(f"Strategy {i+1} JSON error: {json_error}")
                                continue
                                
                    except requests.RequestException as req_error:
                        print(f"Strategy {i+1} request error: {req_error}")
                        continue
                
                # If all strategies failed
                if not success:
                    results.append({
                        'platform': 'reddit',
                        'subreddit': f'r/{subreddit}',
                        'error': 'All Reddit access strategies blocked or failed',
                        'note': 'Reddit may be blocking serverless requests. Try again later.'
                    })
                    
            except Exception as e:
                results.append({
                    'platform': 'reddit',
                    'subreddit': source,
                    'error': f'Unexpected error: {str(e)}'
                })
        
        print(f"Reddit scraping completed. Total results: {len(results)}")
        return results
    
    def scrape_facebook(self, sources, cookies, options):
        """Scrape Facebook with cookies/token support"""
        import requests
        from datetime import datetime
        
        results = []
        
        for source in sources:
            try:
                # Clean page name
                page_name = source.strip().replace('facebook.com/', '').replace('https://', '').replace('http://', '').strip('/')
                
                if cookies:
                    # Try mobile Facebook with cookies
                    url = f"https://m.facebook.com/{page_name}"
                    
                    # Parse cookies string into dict
                    cookie_dict = {}
                    if isinstance(cookies, str):
                        for cookie in cookies.split(';'):
                            if '=' in cookie:
                                key, value = cookie.strip().split('=', 1)
                                cookie_dict[key] = value
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-us',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive'
                    }
                    
                    response = requests.get(url, headers=headers, cookies=cookie_dict, timeout=15)
                    
                    if response.status_code == 200 and 'login' not in response.url.lower():
                        # Parse basic page info from mobile site
                        content = response.text
                        
                        # Extract basic info using simple parsing
                        import re
                        
                        # Try to find page title
                        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content)
                        page_title = title_match.group(1) if title_match else page_name
                        
                        # Try to find posts (basic extraction)
                        posts = []
                        
                        # Look for story containers in mobile Facebook
                        story_matches = re.findall(r'<div[^>]*story[^>]*>(.*?)</div>', content, re.DOTALL | re.IGNORECASE)
                        
                        for i, story in enumerate(story_matches[:5]):  # Limit to 5 posts
                            # Extract text content (very basic)
                            text_content = re.sub(r'<[^>]+>', ' ', story)
                            text_content = ' '.join(text_content.split())[:300]  # Clean and limit
                            
                            if len(text_content.strip()) > 20:  # Only include substantial content
                                posts.append({
                                    'id': f'{page_name}_post_{i}',
                                    'text': text_content,
                                    'created_at': datetime.now().isoformat(),
                                    'url': f'https://facebook.com/{page_name}',
                                    'likes': 0,
                                    'comments': 0,
                                    'shares': 0
                                })
                        
                        results.append({
                            'platform': 'facebook',
                            'page_name': page_name,
                            'page_title': page_title,
                            'url': f'https://facebook.com/{page_name}',
                            'posts': posts,
                            'posts_count': len(posts),
                            'scraped_with': 'cookies',
                            'note': 'Basic content extracted using mobile Facebook with cookies'
                        })
                    
                    elif 'login' in response.url.lower():
                        results.append({
                            'platform': 'facebook',
                            'page_name': page_name,
                            'error': 'Authentication failed - cookies may be expired',
                            'note': 'Redirected to login page, please update cookies'
                        })
                    
                    else:
                        results.append({
                            'platform': 'facebook',
                            'page_name': page_name,
                            'error': f'HTTP {response.status_code}: Could not access page',
                            'note': 'Page may be private or cookies insufficient'
                        })
                
                else:
                    # No cookies provided - try basic public access
                    url = f"https://m.facebook.com/{page_name}"
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
                    }
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 200 and 'login' not in response.url.lower():
                        results.append({
                            'platform': 'facebook',
                            'page_name': page_name,
                            'url': f'https://facebook.com/{page_name}',
                            'note': 'Page exists but limited access without authentication',
                            'scraped_with': 'no_auth',
                            'posts': []
                        })
                    else:
                        results.append({
                            'platform': 'facebook',
                            'page_name': page_name,
                            'error': 'Page requires authentication or does not exist',
                            'note': 'Provide cookies for better access to Facebook content',
                            'alternatives': [
                                'Use Facebook Graph API with access token',
                                'Provide browser cookies from logged-in session',
                                'Use official Facebook data export tools'
                            ]
                        })
                
            except Exception as e:
                results.append({
                    'platform': 'facebook',
                    'page_name': source,
                    'error': str(e),
                    'note': 'Facebook scraping error - try updating cookies or using Graph API'
                })
        
        return results

scraper = UnifiedScraper()

from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            platform = data.get('platform')
            sources = data.get('sources', [])
            
            if not platform or not sources:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {'error': 'Platform and sources required'}
                self.wfile.write(json.dumps(error_response).encode())
                return
            
            # Route to appropriate scraper
            print(f"Routing to platform: {platform} with sources: {sources}")
            if platform == 'twitter':
                results = scraper.scrape_twitter(sources, '', '')
            elif platform == 'instagram':
                results = scraper.scrape_instagram(sources, {})
            elif platform == 'reddit':
                results = scraper.scrape_reddit(sources, {})
            elif platform == 'facebook':
                cookies = data.get('cookies', '')
                results = scraper.scrape_facebook(sources, cookies, {})
            else:
                results = [{'error': f'Unsupported platform: {platform}'}]
            
            print(f"Scraping completed. Results count: {len(results)}")
            if results:
                print(f"First result: {results[0]}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'status': 'success',
                'platform': platform,
                'results': results,
                'count': len(results),
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = {
                'status': 'error',
                'error': str(e)
            }
            self.wfile.write(json.dumps(error_response).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        return