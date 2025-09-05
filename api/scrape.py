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
    SCRAPERS_AVAILABLE = False

try:
    from xcancel_twitter import XCancelTwitterScraper
    XCANCEL_AVAILABLE = True
except ImportError:
    XCANCEL_AVAILABLE = False

try:
    from twitter_enhanced import EnhancedTwitterScraper
    ENHANCED_TWITTER_AVAILABLE = True
except ImportError:
    ENHANCED_TWITTER_AVAILABLE = False

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
        
        # Initialize xcancel scraper if available
        if XCANCEL_AVAILABLE:
            self.xcancel_scraper = XCancelTwitterScraper()
        else:
            self.xcancel_scraper = None
        
        # Initialize enhanced twitter scraper if available
        if ENHANCED_TWITTER_AVAILABLE:
            self.enhanced_twitter = EnhancedTwitterScraper()
        else:
            self.enhanced_twitter = None
    
    def scrape_twitter(self, sources, bearer_token, cookies, options=None):
        results = []
        options = options or {}
        
        for source in sources:
            # Check if source is a search query
            if source.startswith('search:'):
                query = source.replace('search:', '').strip()
                
                # Try search functionality
                if self.enhanced_twitter:
                    try:
                        search_results = self.enhanced_twitter.search_tweets(query, limit=20)
                        for result in search_results:
                            results.append({
                                'platform': 'twitter',
                                'search_query': query,
                                'text': result.get('text', result.get('info', '')),
                                'source': 'search',
                                **result
                            })
                    except Exception as e:
                        results.append({
                            'platform': 'twitter',
                            'search_query': query,
                            'error': f'Search failed: {str(e)}'
                        })
                continue
            
            # Check if source is a tweet URL for fetching with replies
            if '/status/' in source:
                if self.enhanced_twitter:
                    try:
                        tweet_data = self.enhanced_twitter.get_tweet_with_replies(source)
                        if tweet_data:
                            results.append({
                                'platform': 'twitter',
                                'tweet_url': source,
                                **tweet_data
                            })
                    except Exception as e:
                        results.append({
                            'platform': 'twitter',
                            'tweet_url': source,
                            'error': f'Failed to fetch tweet: {str(e)}'
                        })
                continue
            
            # Regular username timeline scraping
            username = source.strip().replace('@', '')
            tweets_found = False
            
            # Strategy 1: Try enhanced scraper first for more complete timeline
            if self.enhanced_twitter:
                try:
                    tweets = self.enhanced_twitter.scrape_user_timeline(username, limit=50)
                    if tweets and not any('error' in tweet for tweet in tweets):
                        for tweet in tweets:
                            results.append({
                                'platform': 'twitter',
                                'username': f'@{username}',
                                'text': tweet.get('text', ''),
                                'created_at': tweet.get('created_at', ''),
                                'likes': tweet.get('likes', 0),
                                'retweets': tweet.get('retweets', 0),
                                'replies': tweet.get('replies', 0),
                                'url': tweet.get('url', ''),
                                'media': tweet.get('media', []),
                                'source': 'syndication_enhanced'
                            })
                        tweets_found = True
                except Exception:
                    pass
            
            # Strategy 2: Try xcancel if available
            if not tweets_found and self.xcancel_scraper:
                try:
                    tweets = self.xcancel_scraper.scrape_user_timeline(username, limit=30)
                    if tweets and not any('error' in tweet for tweet in tweets):
                        # xcancel succeeded
                        for tweet in tweets:
                            results.append({
                                'platform': 'twitter',
                                'username': f'@{username}',
                                'text': tweet.get('text', ''),
                                'created_at': tweet.get('created_at', ''),
                                'likes': tweet.get('likes', 0),
                                'retweets': tweet.get('retweets', 0),
                                'replies': tweet.get('replies', 0),
                                'url': tweet.get('url', ''),
                                'media': tweet.get('media', []),
                                'is_retweet': tweet.get('is_retweet', False),
                                'source': 'xcancel_complete_timeline'
                            })
                        tweets_found = True
                except Exception:
                    pass  # Fallback to syndication API
            
            # Strategy 3: Fallback to basic Twitter Syndication API
            if not tweets_found and self.twitter_scraper:
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
                            'url': tweet.get('permalink', ''),
                            'source': 'syndication_api_popular'
                        })
                    if tweets:
                        tweets_found = True
                except Exception:
                    pass
            
            # If neither strategy worked, return error
            if not tweets_found:
                results.append({
                    'platform': 'twitter',
                    'username': f'@{username}',
                    'error': 'Could not fetch tweets from any available source'
                })
        return results
    
    def scrape_instagram(self, sources, options):
        import requests
        from datetime import datetime
        
        results = []
        for source in sources:
            username = source.strip().replace('@', '')
            
            try:
                # Use Instagram's public web profile info API with enhanced headers
                url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
                
                # Try multiple user agents for better success rate
                user_agents = [
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Instagram 292.0.0.32.108 Android (31/12; 420dpi; 1080x2400; samsung; SM-G991B; o1s; exynos2100; en_US; 492781143)'
                ]
                
                headers = {
                    'User-Agent': user_agents[0],
                    'X-IG-App-ID': '936619743392459',  # Instagram web app ID (public)
                    'X-ASBD-ID': '129477',
                    'X-IG-WWW-Claim': '0',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Origin': 'https://www.instagram.com',
                    'Referer': f'https://www.instagram.com/{username}/',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin'
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
        
        for source in sources:
            try:
                # Clean subreddit name
                subreddit = source.strip().replace('r/', '').replace('/', '')
                success = False
                
                # Strategy 1: Arctic Shift API (Best for serverless) - PRIORITY
                try:
                    
                    arctic_url = "https://arctic-shift.photon-reddit.com/api/posts/search"
                    params = {
                        'subreddit': subreddit,
                        'limit': 10
                    }
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (compatible; SocialScraper/1.0; +https://example.com)',
                        'Accept': 'application/json',
                        'Connection': 'keep-alive'
                    }
                    
                    response = requests.get(arctic_url, params=params, headers=headers, timeout=20)
                    
                    if response.status_code == 200:
                        data = response.json()
                        posts = data.get('data', [])
                        
                        if posts:
                            
                            for post in posts[:10]:
                                post_data = {
                                    'platform': 'reddit',
                                    'subreddit': f'r/{subreddit}',
                                    'title': post.get('title', ''),
                                    'text': post.get('selftext', '')[:500] if post.get('selftext') else '',
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
                                    'strategy_used': 'arctic_shift_api',
                                    'post_id': post.get('id')
                                }
                                
                                # Fetch comments if requested
                                if options.get('fetch_comments', False):
                                    try:
                                        post_id = post.get('id')
                                        if post_id:
                                            comments_url = "https://arctic-shift.photon-reddit.com/api/comments/search"
                                            comments_params = {
                                                'link_id': f't3_{post_id}',
                                                'limit': 50
                                            }
                                            comments_response = requests.get(comments_url, params=comments_params, headers=headers, timeout=15)
                                            
                                            if comments_response.status_code == 200:
                                                comments_data = comments_response.json()
                                                comment_list = []
                                                
                                                for comment in comments_data.get('data', []):
                                                    if comment.get('body') and comment.get('body') not in ['[removed]', '[deleted]']:
                                                        comment_list.append({
                                                            'author': comment.get('author', 'Unknown'),
                                                            'body': comment.get('body', ''),
                                                            'score': comment.get('score', 0),
                                                            'created_at': datetime.fromtimestamp(comment.get('created_utc', 0)).isoformat() if comment.get('created_utc') else '',
                                                            'permalink': f"https://reddit.com{comment.get('permalink', '')}"
                                                        })
                                                
                                                post_data['comments'] = comment_list
                                                post_data['comments_fetched'] = len(comment_list)
                                            else:
                                                pass  # Comments fetch failed
                                    except Exception as comment_error:
                                        post_data['comment_fetch_error'] = str(comment_error)
                                
                                results.append(post_data)
                            
                            success = True
                            
                except Exception as arctic_error:
                    pass  # Arctic Shift API failed
                
                # Strategy 2: RSS Feed Fallback (More reliable for serverless)
                if not success:
                    try:
                        
                        rss_url = f"https://www.reddit.com/r/{subreddit}.rss"
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (compatible; RedditRSSReader/1.0)',
                            'Accept': 'application/rss+xml, application/xml, text/xml'
                        }
                        
                        response = requests.get(rss_url, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            import xml.etree.ElementTree as ET
                            
                            # Parse RSS feed
                            root = ET.fromstring(response.content)
                            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
                            
                            if entries:
                                
                                for entry in entries[:10]:
                                    title_elem = entry.find('.//{http://www.w3.org/2005/Atom}title')
                                    author_elem = entry.find('.//{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name')
                                    link_elem = entry.find('.//{http://www.w3.org/2005/Atom}link')
                                    published_elem = entry.find('.//{http://www.w3.org/2005/Atom}published')
                                    
                                    title = title_elem.text if title_elem is not None else 'No title'
                                    author = author_elem.text.replace('/u/', '') if author_elem is not None else 'Unknown'
                                    url = link_elem.get('href') if link_elem is not None else ''
                                    published = published_elem.text if published_elem is not None else ''
                                    
                                    results.append({
                                        'platform': 'reddit',
                                        'subreddit': f'r/{subreddit}',
                                        'title': title,
                                        'text': '',  # RSS doesn't include full text
                                        'author': author,
                                        'score': 0,  # Not available in RSS
                                        'comments': 0,  # Not available in RSS
                                        'url': url,
                                        'created_at': published,
                                        'upvote_ratio': 0,
                                        'awards': 0,
                                        'flair': None,
                                        'is_video': False,
                                        'thumbnail': None,
                                        'strategy_used': 'rss_feed'
                                    })
                                success = True
                                
                    except Exception as rss_error:
                        pass  # RSS feed failed
                
                # Strategy 3: JSON API fallback (less reliable in serverless)
                if not success:
                    try:
                        
                        json_url = f"https://old.reddit.com/r/{subreddit}/hot.json?limit=10"
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (compatible; RedditScraper/1.0)',
                            'Accept': 'application/json'
                        }
                        
                        response = requests.get(json_url, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            data = response.json()
                            posts = data.get('data', {}).get('children', [])
                            
                            if posts:
                                print(f"JSON API success: Found {len(posts)} posts")
                                
                                for post_item in posts[:10]:
                                    post = post_item.get('data', {})
                                    
                                    results.append({
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
                                        'strategy_used': 'json_api'
                                    })
                                success = True
                                
                    except Exception as json_error:
                        pass  # JSON API failed
                
                # If all strategies failed
                if not success:
                    results.append({
                        'platform': 'reddit',
                        'subreddit': f'r/{subreddit}',
                        'error': 'All Reddit access methods failed',
                        'note': 'Try again later or check subreddit name',
                        'available_methods': ['Arctic Shift API', 'RSS Feed', 'JSON API'],
                        'recommendation': 'Arctic Shift API is most reliable for serverless environments'
                    })
                    
            except Exception as e:
                results.append({
                    'platform': 'reddit',
                    'subreddit': source,
                    'error': f'Unexpected error: {str(e)}'
                })
        
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
                options = data.get('options', {})
                
                # Check if we need to fetch comments/replies
                if options.get('include_comments', False):
                    # For comment fetching, we need to process each tweet URL individually
                    enhanced_results = []
                    base_results = scraper.scrape_twitter(sources, '', '', options)
                    
                    for result in base_results:
                        enhanced_results.append(result)
                        
                        # If this has a tweet URL, try to fetch replies
                        if result.get('url') and '/status/' in result.get('url', ''):
                            # Add a note about replies
                            result['replies_note'] = 'Fetching replies requires authentication. Twitter has restricted access to conversation threads.'
                            result['has_replies'] = True
                    
                    results = enhanced_results
                else:
                    results = scraper.scrape_twitter(sources, '', '', options)
            elif platform == 'instagram':
                results = scraper.scrape_instagram(sources, {})
            elif platform == 'reddit':
                options = data.get('options', {})
                results = scraper.scrape_reddit(sources, options)
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