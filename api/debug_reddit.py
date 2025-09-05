from http.server import BaseHTTPRequestHandler
import json
import requests
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            content_length = int(self.headers.get('content-length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            sources = data.get('sources', [])
            options = data.get('options', {})
            
            debug_info = {
                'step': 'starting',
                'sources': sources,
                'options': options
            }
            
            if not sources:
                result = {'error': 'No sources provided', 'debug': debug_info}
                self.wfile.write(json.dumps(result).encode())
                return
            
            results = []
            
            for source in sources:
                subreddit = source.strip().replace('r/', '').replace('/', '')
                debug_info['current_subreddit'] = subreddit
                debug_info['step'] = 'trying_arctic_shift'
                
                try:
                    # Test Arctic Shift API
                    arctic_url = "https://arctic-shift.photon-reddit.com/api/posts/search"
                    params = {'subreddit': subreddit, 'limit': 10}
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (compatible; SocialScraper/1.0)',
                        'Accept': 'application/json'
                    }
                    
                    response = requests.get(arctic_url, params=params, headers=headers, timeout=15)
                    debug_info['arctic_status'] = response.status_code
                    
                    if response.status_code == 200:
                        data_response = response.json()
                        posts = data_response.get('data', [])
                        debug_info['posts_found'] = len(posts)
                        debug_info['step'] = 'processing_posts'
                        
                        for post in posts[:5]:  # Limit for debug
                            post_data = {
                                'platform': 'reddit',
                                'subreddit': f'r/{subreddit}',
                                'title': post.get('title', ''),
                                'author': post.get('author', 'Unknown'),
                                'score': post.get('score', 0),
                                'url': f"https://reddit.com{post.get('permalink', '')}",
                                'strategy_used': 'arctic_shift_api_debug'
                            }
                            results.append(post_data)
                        
                        debug_info['step'] = 'success'
                        break  # Success, no need to try other sources
                    else:
                        debug_info['arctic_error'] = f'HTTP {response.status_code}'
                        
                except Exception as e:
                    debug_info['arctic_exception'] = str(e)
                    debug_info['step'] = 'arctic_failed'
            
            result = {
                'status': 'success',
                'results': results,
                'count': len(results),
                'debug': debug_info
            }
            
        except Exception as e:
            result = {
                'status': 'error',
                'error': str(e),
                'debug': debug_info if 'debug_info' in locals() else {'error': 'failed_early'}
            }
        
        self.wfile.write(json.dumps(result).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()