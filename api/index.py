#!/usr/bin/env python3
"""
Vercel serverless function for Social Media Scraper API
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import our scraper modules
try:
    from social_scraper import AdvancedScraper
    from syndication_scraper import TwitterSyndicationScraper, InstagramPublicScraper
except ImportError as e:
    print(f"Import error: {e}")
    # Create dummy classes for deployment
    class AdvancedScraper:
        def scrape(self, *args, **kwargs):
            return [{"error": "Scraper not available"}]
    
    class TwitterSyndicationScraper:
        def scrape_user_timeline(self, *args, **kwargs):
            return [{"error": "Twitter scraper not available"}]
    
    class InstagramPublicScraper:
        def scrape_user_profile(self, *args, **kwargs):
            return {"error": "Instagram scraper not available"}

app = Flask(__name__)
CORS(app)

class UnifiedScraper:
    """Unified scraper that handles multiple platforms"""
    
    def __init__(self):
        self.advanced_scraper = AdvancedScraper()
        self.twitter_scraper = TwitterSyndicationScraper()
        self.instagram_scraper = InstagramPublicScraper()
    
    def scrape_reddit(self, sources, options):
        """Scrape Reddit using no-auth JSON API"""
        results = []
        
        for source in sources:
            source_urls = [f'r/{source.strip().replace("r/", "").replace("/", "")}']
            filters = {
                'limit': options.get('limit', 25),
                'fetch_comments': options.get('fetch_comments', True)
            }
            
            try:
                scraped_data = self.advanced_scraper.scrape(source_urls, filters)
                
                for item in scraped_data:
                    if item.get('platform') == 'reddit':
                        reddit_post = {
                            'platform': 'reddit',
                            'subreddit': item.get('subreddit', source),
                            'title': item.get('title', ''),
                            'text': item.get('content', ''),
                            'author': item.get('author', ''),
                            'score': item.get('engagement', {}).get('score', 0),
                            'comments': len(item.get('comments', [])),
                            'upvote_ratio': item.get('engagement', {}).get('upvote_ratio', 0),
                            'url': item.get('url', ''),
                            'created_time': item.get('created_at', ''),
                            'awards': item.get('awards', 0),
                            'flair': item.get('flair'),
                            'all_comments': item.get('comments', [])
                        }
                        results.append(reddit_post)
                        
            except Exception as e:
                results.append({
                    'platform': 'reddit',
                    'subreddit': source,
                    'error': f'Could not scrape r/{source}. Error: {str(e)}'
                })
        
        return results
    
    def scrape_facebook(self, sources, cookies, options):
        """Scrape Facebook"""
        results = []
        
        for source in sources:
            results.append({
                'platform': 'facebook',
                'page_name': source,
                'error': 'Facebook requires authentication for most content',
                'note': 'Use Facebook Graph API or browser automation for full access'
            })
        
        return results
    
    def scrape_twitter(self, sources, bearer_token, cookies):
        """Scrape Twitter using no-auth Syndication API"""
        results = []
        
        for source in sources:
            username = source.strip().replace('@', '')
            
            try:
                tweets = self.twitter_scraper.scrape_user_timeline(
                    username, 
                    limit=20, 
                    include_replies=True
                )
                
                for tweet in tweets:
                    twitter_post = {
                        'platform': 'twitter',
                        'username': f'@{username}',
                        'text': tweet.get('text', ''),
                        'created_at': tweet.get('created_at', ''),
                        'likes': tweet.get('likes', 0),
                        'retweets': tweet.get('retweets', 0),
                        'replies': tweet.get('replies', 0),
                        'quotes': tweet.get('quotes', 0),
                        'url': tweet.get('permalink', ''),
                        'media': tweet.get('media', [])
                    }
                    results.append(twitter_post)
                    
                if not tweets:
                    results.append({
                        'platform': 'twitter',
                        'username': f'@{username}',
                        'error': 'No tweets found or user may be private'
                    })
                    
            except Exception as e:
                results.append({
                    'platform': 'twitter',
                    'username': f'@{username}',
                    'error': str(e)
                })
        
        return results
    
    def scrape_instagram(self, sources, options):
        """Scrape Instagram using no-auth public API"""
        results = []
        
        for source in sources:
            username = source.strip().replace('@', '')
            
            try:
                profile = self.instagram_scraper.scrape_user_profile(username)
                
                if profile:
                    instagram_profile = {
                        'platform': 'instagram',
                        'username': f'@{username}',
                        'full_name': profile.get('full_name', ''),
                        'bio': profile.get('biography', ''),
                        'followers': profile.get('followers', 0),
                        'following': profile.get('following', 0),
                        'posts_count': profile.get('posts_count', 0),
                        'is_verified': profile.get('is_verified', False),
                        'posts': profile.get('posts', [])[:12]
                    }
                    results.append(instagram_profile)
                else:
                    results.append({
                        'platform': 'instagram',
                        'username': f'@{username}',
                        'error': 'Profile not found or private'
                    })
                    
            except Exception as e:
                results.append({
                    'platform': 'instagram',
                    'username': f'@{username}',
                    'error': str(e)
                })
        
        return results
    
    def scrape_platform(self, platform, request_data):
        """Main scraping method"""
        
        if platform == 'reddit':
            return self.scrape_reddit(
                request_data['sources'],
                request_data.get('options', {})
            )
        
        elif platform == 'facebook':
            return self.scrape_facebook(
                request_data['sources'],
                request_data.get('cookies', ''),
                request_data.get('options', {})
            )
        
        elif platform == 'twitter':
            return self.scrape_twitter(
                request_data['sources'],
                request_data.get('bearer_token', ''),
                request_data.get('cookies', '')
            )
        
        elif platform == 'instagram':
            return self.scrape_instagram(
                request_data['sources'],
                request_data.get('options', {})
            )
        
        else:
            raise ValueError(f"Unsupported platform: {platform}")

# Initialize scraper
scraper = UnifiedScraper()

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """API endpoint for scraping"""
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        platform = data.get('platform')
        if not platform:
            return jsonify({'error': 'Platform not specified'}), 400
        
        if platform not in ['reddit', 'facebook', 'twitter', 'instagram']:
            return jsonify({'error': f'Unsupported platform: {platform}'}), 400
        
        sources = data.get('sources', [])
        if not sources:
            return jsonify({'error': 'No sources provided'}), 400
        
        # Perform scraping
        results = scraper.scrape_platform(platform, data)
        
        return jsonify({
            'status': 'success',
            'platform': platform,
            'results': results,
            'count': len(results),
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/status', methods=['GET'])
def api_status():
    """Get scraping status"""
    return jsonify({
        'status': 'ready',
        'supported_platforms': ['reddit', 'facebook', 'twitter', 'instagram'],
        'timestamp': datetime.now().isoformat(),
        'environment': 'vercel'
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'environment': 'vercel'
    })

# Vercel serverless function handler
def handler(request, context=None):
    """Vercel serverless function entry point"""
    with app.app_context():
        return app.full_dispatch_request()

# For local testing
if __name__ == '__main__':
    app.run(debug=True)