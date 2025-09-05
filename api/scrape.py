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
        if not self.instagram_scraper:
            return [{"error": "Instagram scraper not available"}]
        
        results = []
        for source in sources:
            username = source.strip().replace('@', '')
            try:
                profile = self.instagram_scraper.scrape_user_profile(username)
                if profile:
                    results.append({
                        'platform': 'instagram',
                        'username': f'@{username}',
                        'full_name': profile.get('full_name', ''),
                        'followers': profile.get('followers', 0),
                        'posts_count': profile.get('posts_count', 0),
                        'posts': profile.get('posts', [])[:5]
                    })
                else:
                    results.append({
                        'platform': 'instagram',
                        'username': f'@{username}',
                        'error': 'Profile not found'
                    })
            except Exception as e:
                results.append({
                    'platform': 'instagram',
                    'username': f'@{username}',
                    'error': str(e)
                })
        return results
    
    def scrape_reddit(self, sources, options):
        if not self.advanced_scraper:
            return [{"error": "Reddit scraper not available"}]
        
        results = []
        for source in sources:
            try:
                source_urls = [f'r/{source.strip().replace("r/", "")}']
                scraped_data = self.advanced_scraper.scrape(source_urls, {'limit': 10})
                for item in scraped_data:
                    if item.get('platform') == 'reddit':
                        results.append({
                            'platform': 'reddit',
                            'subreddit': item.get('subreddit', source),
                            'title': item.get('title', ''),
                            'text': item.get('content', ''),
                            'author': item.get('author', ''),
                            'score': item.get('engagement', {}).get('score', 0),
                            'url': item.get('url', '')
                        })
                if not results:
                    results.append({
                        'platform': 'reddit',
                        'subreddit': source,
                        'error': 'No posts found'
                    })
            except Exception as e:
                results.append({
                    'platform': 'reddit',
                    'subreddit': source,
                    'error': str(e)
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
            if platform == 'twitter':
                results = scraper.scrape_twitter(sources, '', '')
            elif platform == 'instagram':
                results = scraper.scrape_instagram(sources, {})
            elif platform == 'reddit':
                results = scraper.scrape_reddit(sources, {})
            else:
                results = [{'error': f'Unsupported platform: {platform}'}]
            
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