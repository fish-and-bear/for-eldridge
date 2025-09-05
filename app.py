#!/usr/bin/env python3
"""
Flask Backend for Social Media Scraper
Integrates Facebook, Reddit, and Twitter scraping with web UI
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import sys
from datetime import datetime
import threading
import time
import random

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our scraper modules
from social_scraper import AdvancedScraper
from syndication_scraper import TwitterSyndicationScraper, InstagramPublicScraper

app = Flask(__name__, template_folder='.')
CORS(app)

# Configure Flask
app.config['SECRET_KEY'] = 'your-secret-key-here'

class UnifiedScraper:
    """Unified scraper that handles multiple platforms"""
    
    def __init__(self):
        self.advanced_scraper = AdvancedScraper()
        self.twitter_scraper = TwitterSyndicationScraper()
        self.instagram_scraper = InstagramPublicScraper()
        self.scraping_status = {}
    
    def scrape_reddit(self, sources, options):
        """Scrape Reddit using no-auth JSON API"""
        results = []
        
        for source in sources:
            # Use the advanced scraper's Reddit functionality
            source_urls = [f'r/{source.strip().replace("r/", "").replace("/", "")}']
            filters = {
                'limit': options.get('limit', 25),
                'fetch_comments': options.get('fetch_comments', True)
            }
            
            try:
                scraped_data = self.advanced_scraper.scrape(source_urls, filters)
                
                # Convert to unified format
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
                print(f"Error scraping Reddit r/{source}: {e}")
                # Fallback to demo data
                results.append({
                    'platform': 'reddit',
                    'subreddit': source,
                    'title': f'Error accessing r/{source}',
                    'text': f'Could not scrape r/{source}. Error: {str(e)}',
                    'error': True
                })
        
        return results
    
    def scrape_facebook(self, sources, cookies, options):
        """Scrape Facebook using real scraping methods only"""
        results = []
        
        for source in sources:
            source_urls = [f'https://facebook.com/{source.strip()}']
            
            # Use the advanced scraper's Facebook functionality (real scraping only)
            try:
                scraped_data = self.advanced_scraper.scrape(source_urls, {
                    'limit': options.get('limit', 10)
                })
                
                for item in scraped_data:
                    if item.get('platform') == 'facebook':
                        results.append(item)
                        
            except Exception as e:
                print(f"Error scraping Facebook {source}: {e}")
                results.append({
                    'platform': 'facebook',
                    'page_name': source,
                    'error': 'Facebook requires authentication for most content',
                    'note': 'Facebook blocking prevents unauthenticated scraping',
                    'alternatives': [
                        'Use Facebook Graph API with access token',
                        'Use browser automation with login credentials',
                        'Use official Facebook data export tools'
                    ]
                })
        
        return results
    
    def scrape_twitter(self, sources, bearer_token, cookies):
        """Scrape Twitter using no-auth Syndication API"""
        results = []
        
        for source in sources:
            username = source.strip().replace('@', '')
            
            try:
                # Use the syndication scraper (no auth required!)
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
                        'conversation_id': tweet.get('conversation_id'),
                        'in_reply_to': tweet.get('in_reply_to_status_id'),
                        'reply_chain': tweet.get('reply_chain', []),
                        'conversation_stats': tweet.get('conversation_stats', {}),
                        'media': tweet.get('media', []),
                        'is_thread': bool(tweet.get('reply_chain')),
                        'thread_position': len([r for r in tweet.get('reply_chain', []) if r.get('is_thread_continuation')])
                    }
                    results.append(twitter_post)
                    
                if not tweets:
                    results.append({
                        'platform': 'twitter',
                        'username': f'@{username}',
                        'error': 'No tweets found or user may be private',
                        'note': 'Using Twitter Syndication API (no auth)'
                    })
                    
            except Exception as e:
                print(f"Error scraping Twitter @{username}: {e}")
                results.append({
                    'platform': 'twitter',
                    'username': f'@{username}',
                    'error': str(e),
                    'note': 'Twitter Syndication API error'
                })
        
        return results
    
    def scrape_instagram(self, sources, options):
        """Scrape Instagram using no-auth public API"""
        results = []
        
        for source in sources:
            username = source.strip().replace('@', '')
            
            try:
                # Use the Instagram public API scraper
                profile = self.instagram_scraper.scrape_user_profile(username)
                
                if profile:
                    # Convert profile to unified format
                    instagram_profile = {
                        'platform': 'instagram',
                        'username': f'@{username}',
                        'full_name': profile.get('full_name', ''),
                        'bio': profile.get('biography', ''),
                        'followers': profile.get('followers', 0),
                        'following': profile.get('following', 0),
                        'posts_count': profile.get('posts_count', 0),
                        'is_verified': profile.get('is_verified', False),
                        'profile_pic': profile.get('profile_pic'),
                        'posts': []
                    }
                    
                    # Add recent posts
                    for post in profile.get('posts', []):
                        instagram_post = {
                            'platform': 'instagram',
                            'username': f'@{username}',
                            'post_id': post.get('shortcode'),
                            'url': post.get('url'),
                            'caption': post.get('caption', ''),
                            'likes': post.get('likes', 0),
                            'comments': post.get('comments', 0),
                            'is_video': post.get('is_video', False),
                            'thumbnail': post.get('thumbnail'),
                            'display_url': post.get('display_url'),
                            'created_at': datetime.fromtimestamp(post.get('timestamp', 0)).isoformat() if post.get('timestamp') else ''
                        }
                        instagram_profile['posts'].append(instagram_post)
                    
                    results.append(instagram_profile)
                else:
                    results.append({
                        'platform': 'instagram',
                        'username': f'@{username}',
                        'error': 'Profile not found or private',
                        'note': 'Using Instagram Public API (no auth)'
                    })
                    
            except Exception as e:
                print(f"Error scraping Instagram @{username}: {e}")
                results.append({
                    'platform': 'instagram',
                    'username': f'@{username}',
                    'error': str(e),
                    'note': 'Instagram Public API error'
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

@app.route('/')
def index():
    """Serve the main UI"""
    return render_template('index.html')

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
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{platform}_scrape_{timestamp}.json'
        filepath = os.path.join('results', filename)
        
        # Create results directory if it doesn't exist
        os.makedirs('results', exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'status': 'success',
            'platform': platform,
            'results': results,
            'count': len(results),
            'filename': filename,
            'timestamp': timestamp
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/status')
def api_status():
    """Get scraping status"""
    return jsonify({
        'status': 'ready',
        'supported_platforms': ['reddit', 'facebook', 'twitter', 'instagram'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/demo', methods=['GET'])
def api_demo():
    """Get demo data for testing"""
    
    demo_data = {
        'reddit': scraper.scrape_reddit(['technology', 'worldnews'], {'limit': 3}),
        'twitter': scraper.scrape_twitter(['elonmusk', 'NASA'], '', ''),
        'instagram': scraper.scrape_instagram(['cristiano', 'instagram'], {'limit': 2}),
        'facebook': {'note': 'Facebook requires authentication - use cookies or Graph API for real data'}
    }
    
    return jsonify({
        'status': 'success',
        'demo_data': demo_data,
        'message': 'This is demo data. Real scraping requires proper authentication.'
    })

@app.route('/results/<filename>')
def serve_results(filename):
    """Serve scraped result files"""
    return send_from_directory('results', filename)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

# Create necessary directories on startup
os.makedirs('results', exist_ok=True) 
os.makedirs('logs', exist_ok=True)

# Vercel requires the app to be available at module level
if __name__ == '__main__':
    print("\n🚀 Starting Social Media Scraper")
    print("=" * 50)
    print(f"📊 Dashboard: http://localhost:5000")
    print(f"🔗 API: http://localhost:5000/api/")
    print(f"💡 Demo: http://localhost:5000/api/demo")
    print("=" * 50)
    
    # Run Flask app locally
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )