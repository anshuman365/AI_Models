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
PING_INTERVAL = 10  # 5 minutes
MAX_HISTORY = 100

# Initialize data
target_urls = []
ping_history = []
ping_interval = PING_INTERVAL
max_history = MAX_HISTORY
self_url = os.getenv('SELF_URL', 'http://localhost:5000')

def load_config():
    global target_urls, ping_interval, max_history, self_url
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                target_urls = data.get('urls', [])
                ping_interval = data.get('ping_interval', PING_INTERVAL)
                max_history = data.get('max_history', MAX_HISTORY)
                self_url = data.get('self_url', os.getenv('SELF_URL', 'http://localhost:5000'))
    except Exception as e:
        print(f"Config load error: {str(e)}")
        target_urls = []
        ping_interval = PING_INTERVAL
        max_history = MAX_HISTORY
        self_url = os.getenv('SELF_URL', 'http://localhost:5000')

def save_config():
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({
                'urls': target_urls,
                'ping_interval': ping_interval,
                'max_history': max_history,
                'self_url': self_url
            }, f)
    except Exception as e:
        print(f"Config save error: {str(e)}")

def load_history():
    global ping_history
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                ping_history = json.load(f)
    except Exception as e:
        print(f"History load error: {str(e)}")
        ping_history = []

def save_history():
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(ping_history, f)
    except Exception as e:
        print(f"History save error: {str(e)}")

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

def background_pinger():
    # Initial delay to allow server to start
    time.sleep(10)
    
    while True:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ping cycle started")
        
        # Ping targets
        for url in target_urls:
            result = ping_url(url)
            record = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'result': result
            }
            ping_history.append(record)
            print(f"Pinged {url}: {result['status']}")
        
        # Self-ping with retries
        if self_url:
            for _ in range(3):  # Retry up to 3 times
                try:
                    requests.get(f"{self_url}/ping", timeout=5)
                    print(f"Self-pinged: {self_url}")
                    break
                except Exception as e:
                    print(f"Self-ping failed: {str(e)}")
                    time.sleep(2)
        
        # Maintain history using configurable max_history
        while len(ping_history) > max_history:
            ping_history.pop(0)
        
        save_history()
        print("Ping cycle completed")
        time.sleep(ping_interval)  # Use the configurable interval

@app.template_filter('time_ago')
def time_ago(value):
    if value is None:
        return "Never"
        
    now = datetime.now()
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except:
            return value
    
    diff = now - value
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    else:
        days = seconds // 86400
        return f"{int(days)} days ago"

@app.template_filter('format_datetime')
def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except:
            return value
    
    if isinstance(value, datetime):
        return value.strftime(format)
    
    return str(value)

@app.route('/')
def index():
    # Convert last ping timestamp to datetime object if exists
    last_ping = None
    if ping_history:
        try:
            last_ping = datetime.fromisoformat(ping_history[-1]['timestamp'])
        except:
            last_ping = ping_history[-1]['timestamp']
    
    stats = {
        'total_urls': len(target_urls),
        'total_pings': len(ping_history),
        'last_ping': last_ping
    }
    
    success_rates = {}
    active_services = 0
    down_services = 0
    
    for url in target_urls:
        url_pings = [p for p in ping_history if p['url'] == url]
        success_count = sum(1 for p in url_pings if p['result']['status'] == 'success')
        success_rates[url] = f"{success_count}/{len(url_pings)}" if url_pings else "N/A"
        
        # Determine service status for health chart
        if url_pings:
            last_record = url_pings[-1]
            if last_record['result']['status'] == 'success':
                active_services += 1
            else:
                down_services += 1
    
    return render_template(
        'index.html',
        urls=target_urls,
        history=ping_history[-10:][::-1],
        stats=stats,
        success_rates=success_rates,
        self_url=self_url,
        active_services=active_services,
        down_services=down_services,
        ping_interval=ping_interval,
        max_history=max_history
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
        history=ping_history[::-1]
    )

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        global ping_interval, max_history, self_url
        
        try:
            new_interval = int(request.form.get('ping_interval', PING_INTERVAL))
            if new_interval < 10:  # Minimum 10 seconds
                new_interval = 10
            ping_interval = new_interval
        except ValueError:
            pass
            
        try:
            new_max = int(request.form.get('max_history', MAX_HISTORY))
            if new_max < 10:  # Minimum 10 records
                new_max = 10
            max_history = new_max
        except ValueError:
            pass
            
        self_url = request.form.get('self_url', self_url).strip()
        save_config()
        return redirect(url_for('settings'))
    
    return render_template(
        'settings.html',
        ping_interval=ping_interval,
        max_history=max_history,
        self_url=self_url
    )
    
@app.route('/clear-history')
def clear_history():
    global ping_history
    ping_history = []
    save_history()
    return redirect(url_for('settings'))

@app.route('/reset-config')
def reset_config():
    global target_urls, ping_interval, max_history
    target_urls = []
    ping_interval = PING_INTERVAL
    max_history = MAX_HISTORY
    save_config()
    ping_history = []
    save_history()
    return redirect(url_for('index'))

def start_background_thread():
    """Start background thread with safety checks"""
    load_config()
    load_history()
    
    # Check if thread is already running
    for thread in threading.enumerate():
        if thread.name == "BackgroundPinger":
            print("Background thread already running")
            return
    
    print("Starting background pinger thread...")
    thread = threading.Thread(target=background_pinger, name="BackgroundPinger")
    thread.daemon = True
    thread.start()

# Start thread when app runs
if __name__ == '__main__':
    start_background_thread()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
else:
    # For Gunicorn
    start_background_thread()