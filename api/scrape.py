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

def handler(request):
    """Vercel serverless function for scraping"""
    
    # Handle CORS preflight
    if request.get('method') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': ''
        }
    
    try:
        # Parse request body
        if isinstance(request.get('body'), str):
            data = json.loads(request.get('body', '{}'))
        else:
            data = request.get('body', {})
        
        platform = data.get('platform')
        sources = data.get('sources', [])
        
        if not platform or not sources:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Platform and sources required'})
            }
        
        # Route to appropriate scraper
        if platform == 'twitter':
            results = scraper.scrape_twitter(sources, '', '')
        elif platform == 'instagram':
            results = scraper.scrape_instagram(sources, {})
        elif platform == 'reddit':
            results = scraper.scrape_reddit(sources, {})
        else:
            results = [{'error': f'Unsupported platform: {platform}'}]
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'success',
                'platform': platform,
                'results': results,
                'count': len(results),
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
            })
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'error',
                'error': str(e)
            })
        }