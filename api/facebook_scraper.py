#!/usr/bin/env python3
"""
Facebook scraper with enhanced cookie support
"""

import requests
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import unquote
import time

class FacebookScraper:
    """
    Facebook scraper with cookie authentication
    """
    
    def __init__(self, cookies: str = None):
        self.session = requests.Session()
        self.base_url = "https://www.facebook.com"
        self.mobile_url = "https://m.facebook.com"
        self.mbasic_url = "https://mbasic.facebook.com"
        
        # User agents for different strategies
        self.user_agents = {
            'mobile': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'desktop': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'mbasic': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
        }
        
        self.cookies = self._parse_cookies(cookies) if cookies else {}
        
    def _parse_cookies(self, cookies: str) -> Dict:
        """Parse cookie string or dict into proper format"""
        if isinstance(cookies, dict):
            return cookies
            
        cookie_dict = {}
        if isinstance(cookies, str):
            # Handle both JSON and cookie string formats
            try:
                # Try JSON format first
                cookie_dict = json.loads(cookies)
            except:
                # Parse cookie string format
                for cookie in cookies.split(';'):
                    if '=' in cookie:
                        key, value = cookie.strip().split('=', 1)
                        # URL decode the value
                        cookie_dict[key] = unquote(value)
        
        return cookie_dict
    
    def _make_request(self, url: str, user_agent_type: str = 'mobile') -> Optional[requests.Response]:
        """Make request with proper headers and cookies"""
        headers = {
            'User-Agent': self.user_agents[user_agent_type],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        try:
            response = self.session.get(
                url,
                headers=headers,
                cookies=self.cookies,
                timeout=15,
                allow_redirects=True
            )
            return response
        except Exception as e:
            print(f"Request error: {str(e)}")
            return None
    
    def scrape_page(self, page_name: str) -> Dict:
        """
        Scrape a Facebook page using multiple strategies
        """
        result = {
            'platform': 'facebook',
            'page_name': page_name,
            'url': f'https://facebook.com/{page_name}',
            'scraped_at': datetime.now().isoformat()
        }
        
        # Strategy 1: Try mbasic.facebook.com (simpler HTML)
        mbasic_url = f"{self.mbasic_url}/{page_name}"
        response = self._make_request(mbasic_url, 'mbasic')
        
        if response and response.status_code == 200:
            # Check if we hit login/checkpoint
            if 'login' in response.url.lower() or 'checkpoint' in response.url.lower():
                # Strategy 2: Try mobile.facebook.com
                mobile_url = f"{self.mobile_url}/{page_name}"
                response = self._make_request(mobile_url, 'mobile')
                
                if response and response.status_code == 200:
                    if 'login' in response.url.lower() or 'checkpoint' in response.url.lower():
                        # Strategy 3: Try desktop with different approach
                        desktop_url = f"{self.base_url}/{page_name}/posts"
                        response = self._make_request(desktop_url, 'desktop')
        
        # Process response
        if response and response.status_code == 200:
            if 'login' not in response.url.lower() and 'checkpoint' not in response.url.lower():
                result['status'] = 'success'
                result.update(self._extract_page_data(response.text, page_name))
            else:
                result['status'] = 'auth_required'
                result['error'] = 'Authentication required - cookies may be invalid or expired'
                result['redirect_url'] = response.url
        else:
            result['status'] = 'failed'
            result['error'] = f'Failed to fetch page: HTTP {response.status_code if response else "No response"}'
        
        return result
    
    def _extract_page_data(self, html: str, page_name: str) -> Dict:
        """Extract data from Facebook page HTML"""
        data = {
            'posts': [],
            'page_info': {}
        }
        
        # Extract page title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            data['page_info']['title'] = title_match.group(1).strip()
        
        # Try to extract page likes/followers (various patterns)
        followers_patterns = [
            r'(\d+(?:,\d+)*)\s*(?:people\s+)?(?:follow|like)',
            r'(?:followers?|likes?).*?(\d+(?:,\d+)*)',
            r'"followerCount":\s*(\d+)',
        ]
        
        for pattern in followers_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                followers_str = match.group(1).replace(',', '')
                data['page_info']['followers'] = int(followers_str)
                break
        
        # Extract posts
        # For mbasic/mobile, look for story containers
        post_patterns = [
            r'<div[^>]*(?:role="article"|data-sigil="story-div")[^>]*>(.*?)</div>\s*</div>',
            r'<div[^>]*class="[^"]*story[^"]*"[^>]*>(.*?)</div>\s*</div>',
            r'<article[^>]*>(.*?)</article>'
        ]
        
        posts_found = 0
        for pattern in post_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches[:10]:  # Limit to 10 posts
                # Clean the HTML and extract text
                text = re.sub(r'<[^>]+>', ' ', match)
                text = re.sub(r'\s+', ' ', text).strip()
                
                if len(text) > 50:  # Only include substantial content
                    post_data = {
                        'id': f'{page_name}_post_{posts_found}',
                        'text': text[:500],  # Limit text length
                        'created_at': datetime.now().isoformat()
                    }
                    
                    # Try to extract engagement metrics
                    likes_match = re.search(r'(\d+(?:,\d+)*)\s*(?:likes?|reactions?)', match, re.IGNORECASE)
                    if likes_match:
                        post_data['likes'] = int(likes_match.group(1).replace(',', ''))
                    
                    comments_match = re.search(r'(\d+(?:,\d+)*)\s*comments?', match, re.IGNORECASE)
                    if comments_match:
                        post_data['comments'] = int(comments_match.group(1).replace(',', ''))
                    
                    shares_match = re.search(r'(\d+(?:,\d+)*)\s*shares?', match, re.IGNORECASE)
                    if shares_match:
                        post_data['shares'] = int(shares_match.group(1).replace(',', ''))
                    
                    data['posts'].append(post_data)
                    posts_found += 1
        
        data['posts_count'] = len(data['posts'])
        
        # If no posts found with patterns, try basic text extraction
        if posts_found == 0:
            # Look for any text blocks that might be posts
            text_blocks = re.findall(r'>([^<]{100,})<', html)
            for text in text_blocks[:5]:
                if not any(skip in text.lower() for skip in ['login', 'sign up', 'cookie', 'privacy']):
                    data['posts'].append({
                        'id': f'{page_name}_text_{len(data["posts"])}',
                        'text': text.strip()[:500],
                        'created_at': datetime.now().isoformat(),
                        'type': 'text_extract'
                    })
        
        return data
    
    def scrape_multiple(self, page_names: List[str]) -> List[Dict]:
        """Scrape multiple Facebook pages"""
        results = []
        
        for page_name in page_names:
            # Clean page name
            page_name = page_name.strip().replace('facebook.com/', '').replace('https://', '').replace('http://', '').strip('/')
            
            if page_name:
                print(f"Scraping Facebook page: {page_name}")
                result = self.scrape_page(page_name)
                results.append(result)
                
                # Small delay between requests
                time.sleep(1)
        
        return results


# Test function
if __name__ == "__main__":
    print("Testing Facebook Scraper with Enhanced Cookie Support")
    print("=" * 50)
    
    # Test cookies (use the provided ones)
    cookies = {
        "c_user": "61580384938081",
        "xs": "20:-Txh_epgprXf5A:2:1757053679:-1:-1",
        "datr": "xlC6aIBBjEpW0br55lpMLP9c"
    }
    
    # Or as string
    cookie_string = "c_user=61580384938081; xs=20:-Txh_epgprXf5A:2:1757053679:-1:-1; datr=xlC6aIBBjEpW0br55lpMLP9c"
    
    scraper = FacebookScraper(cookie_string)
    
    # Test pages
    test_pages = ["Meta", "NASA", "NatGeo"]
    
    results = scraper.scrape_multiple(test_pages)
    
    print("\nResults:")
    print("-" * 40)
    
    for result in results:
        if result['status'] == 'success':
            print(f"✅ {result['page_name']}: {result.get('posts_count', 0)} posts")
            if result.get('page_info', {}).get('followers'):
                print(f"   Followers: {result['page_info']['followers']:,}")
            if result.get('posts'):
                print(f"   First post: {result['posts'][0]['text'][:100]}...")
        else:
            print(f"❌ {result['page_name']}: {result.get('error', 'Unknown error')}")