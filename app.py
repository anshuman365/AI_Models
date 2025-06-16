import os
import logging
import requests
import re
import json
from flask import Flask, request, redirect, url_for, session, render_template_string, abort
from threading import Thread
from time import sleep
from telegram import Update, constants
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackContext
)
from datetime import datetime
from dotenv import load_dotenv
from prompt import SYSTEM_PROMPT, BEHAVIOUR_TONE

load_dotenv()

# Load environment variables
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_API_URL = "https://api.sarvam.ai/v1/chat/completions"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "admin123")  # Default password
MEMORY_FILE = "user_memory.json"
KEEP_ALIVE_PORT = int(os.getenv("KEEP_ALIVE_PORT", 8080))

# Configure logging
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

# Combine prompts with proper structure
SYSTEM_PROMPT_F = f"""
{BEHAVIOUR_TONE}

{'-'*50}

{SYSTEM_PROMPT}
"""

# Models fallback list
MODEL_NAMES = ["sarvam-m"]  # Using only compatible model

# Initialize Flask app for web interface
web_app = Flask(__name__)
web_app.secret_key = os.getenv("FLASK_SECRET", "supersecretkey")

# Web interface routes
@web_app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>AK Smartalk AI - Admin</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                h1 { color: #2c3e50; }
                .btn { 
                    display: inline-block; 
                    padding: 10px 20px; 
                    background: #3498db; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 10px 5px;
                }
                .btn:hover { background: #2980b9; }
                .logout { float: right; }
                .file-content { 
                    background: #f5f5f5; 
                    padding: 15px; 
                    border-radius: 5px; 
                    margin-top: 20px;
                    max-height: 600px;
                    overflow: auto;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>AK Smartalk AI - Admin Panel 
                    <a href="/logout" class="btn logout">Logout</a>
                </h1>
                
                <div>
                    <a href="/view_json" class="btn">View JSON Data</a>
                    <a href="/view_txt" class="btn">View TXT History</a>
                </div>
                
                {% if file_content %}
                <div class="file-content">
                    <pre>{{ file_content }}</pre>
                </div>
                {% endif %}
            </div>
        </body>
        </html>
    ''', file_content=session.pop('file_content', None))

@web_app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == WEB_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Login</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; }
                        .container { max-width: 400px; margin: 0 auto; }
                        .form-group { margin-bottom: 15px; }
                        input[type="password"] { 
                            width: 100%; 
                            padding: 10px; 
                            border: 1px solid #ddd; 
                            border-radius: 4px; 
                        }
                        .btn { 
                            padding: 10px 20px; 
                            background: #3498db; 
                            color: white; 
                            border: none; 
                            border-radius: 4px; 
                            cursor: pointer; 
                        }
                        .error { color: red; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Admin Login</h1>
                        {% if error %}<p class="error">{{ error }}</p>{% endif %}
                        <form method="POST">
                            <div class="form-group">
                                <label for="password">Password:</label>
                                <input type="password" id="password" name="password" required>
                            </div>
                            <button type="submit" class="btn">Login</button>
                        </form>
                    </div>
                </body>
                </html>
            ''', error="Invalid password!")
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 400px; margin: 0 auto; }
                .form-group { margin-bottom: 15px; }
                input[type="password"] { 
                    width: 100%; 
                    padding: 10px; 
                    border: 1px solid #ddd; 
                    border-radius: 4px; 
                }
                .btn { 
                    padding: 10px 20px; 
                    background: #3498db; 
                    color: white; 
                    border: none; 
                    border-radius: 4px; 
                    cursor: pointer; 
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Admin Login</h1>
                <form method="POST">
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit" class="btn">Login</button>
                </form>
            </div>
        </body>
        </html>
    ''')

@web_app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@web_app.route('/view_json')
def view_json():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        if os.path.exists(MEMORY_FILE) and os.path.getsize(MEMORY_FILE) > 0:
            with open(MEMORY_FILE, 'r') as f:
                data = json.load(f)
                session['file_content'] = json.dumps(data, indent=2)
        else:
            session['file_content'] = "No JSON data available"
    except Exception as e:
        session['file_content'] = f"Error loading JSON: {str(e)}"
    return redirect(url_for('index'))

@web_app.route('/view_txt')
def view_txt():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        if os.path.exists("conversation_history.txt") and os.path.getsize("conversation_history.txt") > 0:
            with open("conversation_history.txt", 'r', encoding='utf-8') as f:
                session['file_content'] = f.read()
        else:
            session['file_content'] = "No conversation history available"
    except Exception as e:
        session['file_content'] = f"Error loading TXT: {str(e)}"
    return redirect(url_for('index'))

def run_web_app():
    web_app.run(host='0.0.0.0', port=KEEP_ALIVE_PORT, use_reloader=False)

def keep_alive():
    """Keep the service alive by periodically accessing it"""
    while True:
        try:
            # Self-ping to keep the service active
            requests.get(f"http://localhost:{KEEP_ALIVE_PORT}/", timeout=10)
            logging.info("Keep-alive ping successful")
        except Exception as e:
            logging.error(f"Keep-alive ping failed: {str(e)}")
        sleep(300)  # Ping every 5 minutes

# Save history to local file
def save_conversation(user_id, user_input, bot_response):
    with open("conversation_history.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | User {user_id}:\n{user_input}\nBot:\n{bot_response}\n\n")

# Load user memory from file
def load_user_memory():
    try:
        if os.path.exists(MEMORY_FILE) and os.path.getsize(MEMORY_FILE) > 0:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logging.error(f"Error loading memory: {str(e)}")
        return {}

# Save user memory to file
def save_user_memory(memory_data):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory_data, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving memory: {str(e)}")

# Convert conversation list to linear string
def conversation_to_string(conversation_list):
    lines = []
    for msg in conversation_list:
        role = "user" if msg["role"] == "user" else "bot"
        content = msg["content"].replace('\n', ' ')  # Flatten content
        lines.append(f"{role}: {content}")
    return "\n".join(lines)

# Parse linear string to conversation list
def string_to_conversation(conversation_str):
    conversation = []
    lines = conversation_str.split('\n')
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("user: "):
            content = line[6:].strip()
            conversation.append({"role": "user", "content": content})
        elif line.startswith("bot: "):
            content = line[5:].strip()
            conversation.append({"role": "assistant", "content": content})
    return conversation

# Summarize context for long conversations
def summarize_context(conversation_history):
    """Summarize long conversations by keeping only last 2 exchanges"""
    if len(conversation_history) > 10:
        return conversation_history[-4:]  # Keep last 2 exchanges (4 messages)
    return conversation_history

# Language detection function
def detect_language(text):
    """Simple Hindi/English detector"""
    hindi_chars = set("ऀँंःऄअआइईउऊऋऌऍऎएऐऑऒओऔकखगघङचछजझञटठडढणतथदधनऩपफबभमयरऱलळऴवशषसहऺऻ़ऽािीुूृॄॅॆेैॉॊोौ्ॎॏॐ॒॑॓॔ॕॖॗक़ख़ग़ज़ड़ढ़फ़य़ॠॡॢॣ।॥०१२३४५६७८९॰ॱॲॳॴॵॶॷॸॹॺॻॼॽॾॿ")
    return "hindi" if any(char in hindi_chars for char in text) else "english"

# Sarvam AI call with conversation history
def call_sarvam_api(user_input, conversation_history, user_memory=None):
    # Log conversation history details
    logging.info(f"Conversation history length: {len(conversation_history)}")
    if conversation_history:
        logging.info(f"Last message: {conversation_history[-1]['content'][:50]}...")
    
    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Prepare messages with system prompt
    messages = [{"role": "system", "content": SYSTEM_PROMPT_F}]
    
    # Add memory context if available
    if user_memory:
        memory_context = "User's stored information:\n"
        for key, value in user_memory.items():
            memory_context += f"- {key} = {value}\n"
        messages.append({"role": "system", "content": memory_context})
    
    # Add conversation history
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_input})
    
    for model in MODEL_NAMES:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500,
            "top_p": 0.9,
            "presence_penalty": 0.6,  # Reduces repetition
            "frequency_penalty": 0.6   # Reduces repetition
        }
        try:
            response = requests.post(SARVAM_API_URL, headers=headers, json=payload, timeout=30)
            if response.ok:
                return response.json()["choices"][0]["message"]["content"]
            else:
                logging.warning(f"Model {model} failed: {response.text}")
                # Enhanced error logging
                try:
                    error_details = response.json().get('error', {})
                    logging.error(f"API Error: {error_details.get('message', 'Unknown error')}")
                    logging.error(f"Error type: {error_details.get('type', 'unknown')}")
                except:
                    logging.error(f"Full API error: {response.text}")
        except Exception as e:
            logging.error(f"API Error: {str(e)}")
    return "⚠️ Sorry, all AI models failed to respond. Please try again later."

# Initialize user data with proper structure
def init_user_data(context: CallbackContext, user_id: int):
    # Initialize bot_data structure
    if 'user_memory' not in context.bot_data:
        context.bot_data['user_memory'] = load_user_memory()
    
    if 'users' not in context.bot_data:
        context.bot_data['users'] = {}
    
    user_id_str = str(user_id)
    
    # Initialize user-specific data
    if user_id not in context.bot_data['users']:
        # Load from persistent storage if available
        user_persistent = context.bot_data['user_memory'].get(user_id_str, {})
        
        # Initialize conversation history
        conversation_str = user_persistent.get("conversation", "")
        conversation_list = string_to_conversation(conversation_str) if conversation_str else []
        
        # Initialize memory
        memory_dict = user_persistent.get("memory", {})
        
        context.bot_data['users'][user_id] = {
            'conversation': conversation_list,
            'memory': memory_dict
        }
    
    # Ensure memory exists
    user_data = context.bot_data['users'][user_id]
    if user_data['memory'] is None:
        user_data['memory'] = {}
    
    return user_data

# Update persistent storage for a user
def update_persistent_user_data(context: CallbackContext, user_id: int):
    user_id_str = str(user_id)
    user_data = context.bot_data['users'].get(user_id)
    
    if not user_data:
        return
    
    # Convert conversation to string format
    conversation_str = conversation_to_string(user_data['conversation'])
    
    # Update persistent storage
    context.bot_data['user_memory'][user_id_str] = {
        "memory": user_data['memory'],
        "conversation": conversation_str
    }
    
    # Save to file
    save_user_memory(context.bot_data['user_memory'])

# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = init_user_data(context, user.id)
    
    await update.message.reply_text(
        f"👋 Hello {user.full_name}! I'm AK Smartalk AI - your personal assistant.\n"
        "You can ask me anything about education, technology, or general knowledge. 😊\n\n"
        "Type /help to see what I can do!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = init_user_data(context, update.effective_user.id)
    await update.message.reply_text(
        "🚀 Available Commands:\n"
        "/start - Start a new session\n"
        "/help - Show this help message\n"
        "/memory - View stored information\n"
        "/clear_memory - Delete all stored data\n"
        "/clear_history - Clear conversation history\n\n"
        "💡 Features:\n"
        "- Remember information: 'name = Anshuman' or 'Remember key = value'\n"
        "- Recall stored values: 'What did I remember?'\n"
        "- Continuous conversation memory\n"
        "- Emotionally aware responses\n\n"
        "Just chat naturally - I'm here to help!"
    )

async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = init_user_data(context, update.effective_user.id)
    
    if not user_data['memory']:
        await update.message.reply_text("🧠 No information has been stored yet.")
        return
        
    output_lines = ["🧠 Stored information:"]
    for key, value in user_data['memory'].items():
        output_lines.append(f"• {key} = {value}")
        
    await update.message.reply_text("\n".join(output_lines))

async def clear_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = init_user_data(context, user.id)
    user_data['memory'] = {}
    
    # Update persistent storage
    update_persistent_user_data(context, user.id)
    
    await update.message.reply_text("✅ All stored data has been successfully deleted!")

async def clear_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = init_user_data(context, user.id)
    user_data['conversation'] = []
    
    # Update persistent storage
    update_persistent_user_data(context, user.id)
    
    await update.message.reply_text("✅ Conversation history has been successfully cleared!")

# Handle multi-line memory assignments
def handle_multi_line_memory(user_input: str):
    # Check if the input looks like a multi-line memory assignment
    if not user_input.lower().startswith(("remember", "save", "store")):
        return None
    
    # Extract all lines after the first
    lines = user_input.split('\n')[1:]
    if not lines:
        return None
    
    memory_items = {}
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        # Try to parse key-value pairs
        if '=' in line:
            try:
                key, value = [part.strip() for part in line.split('=', 1)]
                memory_items[key] = value
            except:
                # If not in key=value format, store the whole line
                memory_items[line] = "(no value)"
        else:
            # Store the whole line as a key with empty value
            memory_items[line] = "(no value)"
    
    return memory_items

# Message Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = init_user_data(context, user.id)
    user_input = update.message.text

    # Detect language for consistency
    current_language = detect_language(user_input)
    logging.info(f"Detected language: {current_language} for user input: {user_input[:50]}...")

    # Handle multi-line memory assignments
    if '\n' in user_input:
        memory_items = handle_multi_line_memory(user_input)
        if memory_items:
            # Add all items to memory
            for key, value in memory_items.items():
                user_data['memory'][key] = value
            
            # Update persistent storage
            update_persistent_user_data(context, user.id)
            
            # Confirm with user
            output_lines = ["✅ Remembered the following:"]
            for key, value in memory_items.items():
                output_lines.append(f"• {key} = {value}")
                
            await update.message.reply_text("\n".join(output_lines))
            return

    # Handle formal assignment with '='
    if '=' in user_input:
        try:
            # Split only on first '=' to handle values containing '='
            parts = user_input.split('=', 1)
            if len(parts) < 2:
                raise ValueError("Invalid format")
                
            key = parts[0].strip()
            value = parts[1].strip()
            
            # Remove any trailing content after newline
            if '\n' in value:
                value = value.split('\n')[0].strip()
                
            user_data['memory'][key] = value
            
            # Update persistent storage
            update_persistent_user_data(context, user.id)
            
            await update.message.reply_text(f"✅ Remembered: `{key} = {value}`", 
                                          parse_mode=constants.ParseMode.MARKDOWN)
            return
        except Exception as e:
            logging.error(f"Assignment error: {str(e)}")
            await update.message.reply_text("⚠️ Correct format: `key = value`", 
                                          parse_mode=constants.ParseMode.MARKDOWN)
            return

    # Handle memory recall requests
    recall_phrases = [
        "memory", "remembered", "recall", "stored", "saved", 
        "what did I tell you", "what I remember", "show my data",
        "tell what I say to remember"
    ]
    
    if any(phrase in user_input.lower() for phrase in recall_phrases):
        if not user_data['memory']:
            await update.message.reply_text("❌ No information has been stored yet.")
            return
            
        output_lines = ["🧠 Stored information:"]
        for key, value in user_data['memory'].items():
            output_lines.append(f"• {key} = {value}")
            
        await update.message.reply_text("\n".join(output_lines))
        return

    # Summarize context for API call
    api_conversation_history = summarize_context(user_data['conversation'])
    
    # AI response with conversation history AND memory context
    ai_response = call_sarvam_api(
        user_input, 
        api_conversation_history,
        user_data['memory']
    )
    
    # Save to conversation history
    user_data['conversation'].append({"role": "user", "content": user_input})
    user_data['conversation'].append({"role": "assistant", "content": ai_response})
    
    # Limit conversation history to last 200 messages (100 exchanges)
    if len(user_data['conversation']) > 200:
        user_data['conversation'] = user_data['conversation'][-200:]
    
    # Update persistent storage
    update_persistent_user_data(context, user.id)
    save_conversation(user.id, user_input, ai_response)

    try:
        await update.message.reply_text(ai_response, parse_mode=constants.ParseMode.MARKDOWN)
    except:
        await update.message.reply_text(ai_response)  # fallback if markdown error

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Error: {context.error}")
    if update.message:
        await update.message.reply_text("⚠️ A technical issue occurred. Please try again later.")

# Main app
def main():
    # Verify environment variables
    if not TELEGRAM_TOKEN:
        logging.critical("❌ TELEGRAM_BOT_TOKEN environment variable missing!")
        exit(1)
    if not SARVAM_API_KEY:
        logging.critical("❌ SARVAM_API_KEY environment variable missing!")
        exit(1)
    
    # Start web server in a separate thread
    web_thread = Thread(target=run_web_app, daemon=True)
    web_thread.start()
    logging.info(f"🌐 Web server started on port {KEEP_ALIVE_PORT}")
    
    # Start keep-alive pinger in another thread
    keep_alive_thread = Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    logging.info("🔋 Keep-alive system activated")
    
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("memory", memory_command))
    application.add_handler(CommandHandler("clear_memory", clear_memory_command))
    application.add_handler(CommandHandler("clear_history", clear_history_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)

    logging.info("🤖 AK Smartalk AI is active!")
    application.run_polling()

if __name__ == "__main__":
    main()