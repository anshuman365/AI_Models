# app.py
from flask import Flask, render_template_string, Response, request, send_file
import itertools
import threading
import time
import os
import io

app = Flask(__name__)

# Store calculation state per client
calculation_states = {}
calculation_lock = threading.Lock()

# Store calculated pi digits per client
pi_results = {}
pi_lock = threading.Lock()

# Spigot algorithm for generating Pi digits
def pi_digits():
    """Generate Pi digits indefinitely"""
    # Algorithm by Jeremy Gibbons
    q, r, t, k, n, l = 1, 0, 1, 1, 3, 3
    while True:
        if 4 * q + r - t < n * t:
            yield str(n)
            q, r, t, k, n, l = (
                10 * q,
                10 * (r - n * t),
                t,
                k,
                (10 * (3 * q + r)) // t - 10 * n,
                l,
            )
        else:
            q, r, t, k, n, l = (
                q * k,
                (2 * q + r) * l,
                t * l,
                k + 1,
                (q * (7 * k + 2) + r * l) // (t * l),
                l + 2,
            )

def generate_pi_stream(client_id, limit):
    """Generator that yields Pi digits up to a limit"""
    digits = pi_digits()
    pi_str = "3."  # Start with 3 and decimal point
    
    # Track calculation state
    with calculation_lock:
        calculation_states[client_id] = {"running": True, "count": 0}
    
    try:
        for count, digit in enumerate(itertools.islice(digits, limit)):
            # Check if we should stop
            with calculation_lock:
                if not calculation_states.get(client_id, {}).get("running", True):
                    break
                calculation_states[client_id]["count"] = count + 1
            
            # Add digit to the string
            pi_str += digit
            
            # Add space every 50 digits for readability
            if (count + 1) % 50 == 0:
                pi_str += " "
                yield " "
            else:
                yield digit
            
            # Update stored result
            with pi_lock:
                pi_results[client_id] = pi_str
    finally:
        # Clean up
        with calculation_lock:
            if client_id in calculation_states:
                del calculation_states[client_id]
        # Store final result
        with pi_lock:
            pi_results[client_id] = pi_str

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pi Calculator</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                text-align: center; 
                margin-top: 50px; 
                background-color: #f0f8ff;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            #pi-display {
                font-size: 20px;
                letter-spacing: 1px;
                margin: 20px auto;
                padding: 20px;
                border: 1px solid #4CAF50;
                border-radius: 5px;
                background-color: #fff;
                overflow-wrap: break-word;
                min-height: 150px;
                max-height: 400px;
                overflow-y: auto;
                text-align: left;
                white-space: pre-wrap;
            }
            .controls {
                margin: 20px auto;
                display: flex;
                justify-content: center;
                gap: 10px;
                flex-wrap: wrap;
            }
            input, button {
                padding: 10px 15px;
                font-size: 16px;
                border-radius: 4px;
            }
            input {
                width: 120px;
                border: 1px solid #ccc;
            }
            button {
                background-color: #4CAF50;
                color: white;
                border: none;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            button:hover {
                background-color: #45a049;
            }
            button:disabled {
                background-color: #cccccc;
                cursor: not-allowed;
            }
            #stopBtn {
                background-color: #f44336;
            }
            #downloadBtn {
                background-color: #2196F3;
            }
            #stopBtn:hover {
                background-color: #d32f2f;
            }
            #downloadBtn:hover {
                background-color: #0b7dda;
            }
            .status {
                margin: 10px;
                font-size: 16px;
                color: #555;
            }
            .info {
                margin: 10px auto;
                max-width: 600px;
                text-align: left;
                background-color: #e7f4e4;
                padding: 15px;
                border-radius: 5px;
            }
            h1 {
                color: #2E8B57;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Pi Digit Calculator</h1>
            
            <div class="info">
                <p>Calculate π to a specific number of digits or infinitely.</p>
                <p><strong>Note:</strong> Calculating more than 10,000 digits may slow down your browser.</p>
            </div>
            
            <div class="controls">
                <input type="number" id="digitLimit" min="0" value="1000" placeholder="Digits limit (0=infinite)">
                <button id="calculateBtn" onclick="startCalculation()">Calculate Pi</button>
                <button id="stopBtn" onclick="stopCalculation()" style="display:none;">Stop Calculation</button>
                <button id="downloadBtn" onclick="downloadPi()" style="display:none;">Download as TXT</button>
            </div>
            
            <div class="status" id="status">Enter digits limit and click Calculate</div>
            
            <div id="pi-display">3.</div>
        </div>

        <script>
            let eventSource = null;
            let clientId = null;
            let digitCount = 0;
            
            function startCalculation() {
                const btn = document.getElementById('calculateBtn');
                const stopBtn = document.getElementById('stopBtn');
                const downloadBtn = document.getElementById('downloadBtn');
                const display = document.getElementById('pi-display');
                const status = document.getElementById('status');
                const digitLimit = document.getElementById('digitLimit').value;
                
                // Validate input
                if (!digitLimit && digitLimit !== '0') {
                    status.textContent = 'Please enter a digit limit';
                    return;
                }
                
                const limit = digitLimit === '0' ? 'infinite' : parseInt(digitLimit);
                
                if (isNaN(limit) || (limit !== 'infinite' && limit < 0)) {
                    status.textContent = 'Please enter a valid number (≥0)';
                    return;
                }
                
                // Reset display
                display.textContent = '3.';
                digitCount = 0;
                
                // Disable controls
                btn.disabled = true;
                document.getElementById('digitLimit').disabled = true;
                stopBtn.style.display = 'inline-block';
                downloadBtn.style.display = 'none'; // Hide download until calculation completes
                
                // Generate unique client ID
                clientId = 'client_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                
                // Start calculation
                status.textContent = limit === 'infinite' 
                    ? 'Calculating π infinitely...' 
                    : `Calculating π to ${limit} digits...`;
                
                eventSource = new EventSource(`/pi_feed?limit=${limit}&client_id=${clientId}`);
                
                eventSource.onmessage = function(event) {
                    const data = event.data;
                    
                    if (data === 'COMPLETE') {
                        status.textContent = `Calculation complete! Total digits: ${digitCount}`;
                        cleanup();
                        // Show download button after calculation completes
                        document.getElementById('downloadBtn').style.display = 'inline-block';
                    } else {
                        display.textContent += data;
                        digitCount += data.length;
                        
                        // Update status periodically
                        if (digitCount % 100 === 0) {
                            status.textContent = limit === 'infinite' 
                                ? `Calculating... Digits so far: ${digitCount}` 
                                : `Calculating... ${digitCount}/${limit} digits`;
                        }
                        
                        // Scroll to bottom to see latest digits
                        display.scrollTop = display.scrollHeight;
                    }
                };
                
                eventSource.onerror = function() {
                    status.textContent = 'Connection error or calculation stopped';
                    cleanup();
                    // Show download button even if calculation was stopped
                    document.getElementById('downloadBtn').style.display = 'inline-block';
                };
            }
            
            function stopCalculation() {
                if (eventSource) {
                    eventSource.close();
                }
                fetch(`/stop_calculation?client_id=${clientId}`);
                cleanup();
                // Show download button after stopping
                document.getElementById('downloadBtn').style.display = 'inline-block';
            }
            
            function cleanup() {
                const btn = document.getElementById('calculateBtn');
                const stopBtn = document.getElementById('stopBtn');
                
                if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                }
                
                btn.disabled = false;
                stopBtn.style.display = 'none';
                document.getElementById('digitLimit').disabled = false;
            }
            
            function downloadPi() {
                // Trigger download via server
                window.location.href = `/download_pi?client_id=${clientId}`;
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/pi_feed')
def pi_feed():
    """SSE route for streaming Pi digits"""
    limit = request.args.get('limit', '1000')
    client_id = request.args.get('client_id', 'default')
    
    # Parse limit (0 = infinite)
    try:
        limit = int(limit)
        if limit == 0:
            limit = None  # Infinite
    except ValueError:
        limit = 1000  # Default
    
    def event_stream():
        # Generate digits
        if limit is None:  # Infinite calculation
            digits = pi_digits()
            # Skip the first digit (3) since we already have it
            next(digits)
            count = 0
            
            # Initialize pi string
            with pi_lock:
                pi_results[client_id] = "3."
            
            # Send initial decimal point
            yield "data: .\n\n"
            
            try:
                while True:
                    # Check if we should stop
                    with calculation_lock:
                        state = calculation_states.get(client_id, {})
                        if not state.get("running", True):
                            break
                    
                    digit = next(digits)
                    yield f"data: {digit}\n\n"
                    count += 1
                    
                    # Add space every 50 digits for readability
                    if count % 50 == 0:
                        yield "data:  \n\n"
                        
                    # Update stored result
                    with pi_lock:
                        if client_id in pi_results:
                            pi_results[client_id] += digit
                        else:
                            pi_results[client_id] = "3." + digit
            except StopIteration:
                pass
        else:  # Finite calculation
            # Initialize pi string
            with pi_lock:
                pi_results[client_id] = "3."
            
            # Get the generator
            stream = generate_pi_stream(client_id, limit)
            
            # Skip the initial "3." since we already have it
            next(stream)
            
            # Stream the digits
            for digit in stream:
                yield f"data: {digit}\n\n"
        
        # Send completion signal
        yield "data: COMPLETE\n\n"
    
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/stop_calculation')
def stop_calculation():
    """Stop an ongoing calculation"""
    client_id = request.args.get('client_id')
    if client_id:
        with calculation_lock:
            if client_id in calculation_states:
                calculation_states[client_id]["running"] = False
                return "Calculation stopped", 200
    return "Client not found", 404

@app.route('/download_pi')
def download_pi():
    """Download the calculated Pi digits as TXT file"""
    client_id = request.args.get('client_id')
    if not client_id:
        return "Client ID missing", 400
    
    # Get the stored Pi result
    with pi_lock:
        pi_str = pi_results.get(client_id, "3.")
    
    # Create in-memory file
    mem_file = io.BytesIO()
    mem_file.write(pi_str.encode('utf-8'))
    mem_file.seek(0)
    
    # Count digits after decimal point
    decimal_digits = len(pi_str) - 2  # Subtract "3." prefix
    
    # Create filename
    filename = f"pi_{decimal_digits}_digits.txt"
    
    # Send file
    return send_file(
        mem_file,
        as_attachment=True,
        download_name=filename,
        mimetype='text/plain'
    )

if __name__ == '__main__':
    app.run(debug=True, port=8080)
