# app.py
import os
import time
import json
import threading
import requests
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

# Configuration
CONFIG_FILE = 'config.json'
HISTORY_FILE = 'history.json'
PING_INTERVAL = 300  # 5 minutes
MAX_HISTORY = 100    # Max records to keep

# Initialize data structures
target_urls = []
ping_history = []
self_url = os.getenv('SELF_URL', 'http://localhost:5000')

# Load configuration from file
def load_config():
    global target_urls
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                target_urls = data.get('urls', [])
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        target_urls = []

# Save configuration to file
def save_config():
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'urls': target_urls}, f)
    except Exception as e:
        print(f"Error saving config: {str(e)}")

# Load history from file
def load_history():
    global ping_history
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                ping_history = json.load(f)
    except Exception as e:
        print(f"Error loading history: {str(e)}")
        ping_history = []

# Save history to file
def save_history():
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(ping_history, f)
    except Exception as e:
        print(f"Error saving history: {str(e)}")

# Ping a URL and record results
def ping_url(url):
    try:
        start_time = time.time()
        response = requests.get(url, timeout=10)
        response_time = round(time.time() - start_time, 2)
        return {
            'status': 'success',
            'http_status': response.status_code,
            'response_time': response_time,
            'error': None
        }
    except Exception as e:
        return {
            'status': 'error',
            'http_status': None,
            'response_time': None,
            'error': str(e)
        }

# Background pinger function
def background_pinger():
    while True:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting ping cycle")
        
        # Ping all target URLs
        for url in target_urls:
            result = ping_url(url)
            record = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'result': result
            }
            ping_history.append(record)
            print(f"Pinged {url}: {result['status']}")
        
        # Self-ping to keep this service alive
        try:
            requests.get(f"{self_url}/ping", timeout=5)
            print(f"Self-pinged: {self_url}")
        except Exception as e:
            print(f"Self-ping failed: {str(e)}")
        
        # Trim history and save data
        while len(ping_history) > MAX_HISTORY:
            ping_history.pop(0)
        
        save_history()
        print("Ping cycle completed")
        
        # Wait for next cycle
        time.sleep(PING_INTERVAL)

# Web interface routes
@app.route('/')
def index():
    stats = {
        'total_urls': len(target_urls),
        'total_pings': len(ping_history),
        'last_ping': ping_history[-1]['timestamp'] if ping_history else 'Never'
    }
    
    # Calculate success rates
    success_rates = {}
    for url in target_urls:
        url_pings = [p for p in ping_history if p['url'] == url]
        success_count = sum(1 for p in url_pings if p['result']['status'] == 'success')
        success_rates[url] = f"{success_count}/{len(url_pings)}" if url_pings else "N/A"
    
    return render_template(
        'index.html',
        urls=target_urls,
        history=ping_history[-10:][::-1],  # Show last 10 entries, newest first
        stats=stats,
        success_rates=success_rates,
        self_url=self_url
    )

@app.route('/add', methods=['POST'])
def add_url():
    url = request.form.get('url', '').strip()
    if url and url not in target_urls:
        target_urls.append(url)
        save_config()
    return redirect(url_for('index'))

@app.route('/remove/<path:url>')
def remove_url(url):
    if url in target_urls:
        target_urls.remove(url)
        save_config()
    return redirect(url_for('index'))

@app.route('/ping')
def ping():
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/history')
def history():
    return render_template(
        'history.html',
        history=ping_history[::-1]  # Show all history, newest first
    )

# Start background thread when app runs
if __name__ == '__main__':
    # Load initial data
    load_config()
    load_history()
    
    # Start background thread
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        print("Starting background pinger thread...")
        thread = threading.Thread(target=background_pinger)
        thread.daemon = True
        thread.start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
else:
    # When running with Gunicorn
    load_config()
    load_history()
    print("Starting background pinger thread for Gunicorn...")
    thread = threading.Thread(target=background_pinger)
    thread.daemon = True
    thread.start()