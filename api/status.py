from datetime import datetime

def handler(request):
    """Vercel serverless function for API status"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': {
            'status': 'ready',
            'supported_platforms': ['reddit', 'facebook', 'twitter', 'instagram'],
            'timestamp': datetime.now().isoformat(),
            'environment': 'vercel'
        }
    }