from http.server import BaseHTTPRequestHandler
import json
import requests

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            # Test Arctic Shift API directly
            arctic_url = "https://arctic-shift.photon-reddit.com/api/posts/search"
            params = {'subreddit': 'python', 'limit': 2}
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; SocialScraper/1.0)',
                'Accept': 'application/json'
            }
            
            response = requests.get(arctic_url, params=params, headers=headers, timeout=10)
            
            result = {
                'status': 'success',
                'arctic_shift_status': response.status_code,
                'arctic_shift_works': response.status_code == 200,
                'response_length': len(response.text) if response.status_code == 200 else 0
            }
            
            if response.status_code == 200:
                data = response.json()
                result['posts_found'] = len(data.get('data', []))
                
        except Exception as e:
            result = {
                'status': 'error',
                'error': str(e),
                'arctic_shift_works': False
            }
        
        self.wfile.write(json.dumps(result).encode())