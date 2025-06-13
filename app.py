# app.py (main application)
import os
import base64
import email
from flask import Flask, render_template
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import joblib
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import string
import re
import os
import json
from dotenv import load_dotenv
load_dotenv()  # Load environment variables

# Initialize Flask app
app = Flask(__name__)

# Initialize NLP components
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))
stemmer = PorterStemmer()

# Load ML model
model = joblib.load('spam_model.joblib')
tfidf = joblib.load('tfidf_vectorizer.joblib')

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'

def get_gmail_service():
    """Authenticate and create Gmail API service"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def clean_text(text):
    """Preprocess email text for classification"""
    if text is None:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    # Convert to lowercase
    text = text.lower()
    # Remove stopwords and stem
    words = text.split()
    words = [stemmer.stem(word) for word in words if word not in stop_words]
    return ' '.join(words)

def classify_email(email_text):
    """Classify email as spam or ham"""
    cleaned_text = clean_text(email_text)
    features = tfidf.transform([cleaned_text])
    prediction = model.predict(features)
    return "spam" if prediction[0] == 1 else "ham"

def get_emails(max_results=10):
    """Fetch emails from Gmail account"""
    service = get_gmail_service()
    results = service.users().messages().list(
        userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])
    
    email_list = []
    
    for msg in messages:
        msg_data = service.users().messages().get(
            userId='me', id=msg['id']).execute()
        
        # Extract email data
        payload = msg_data['payload']
        headers = payload['headers']
        
        email_info = {
            'id': msg['id'],
            'subject': '',
            'from': '',
            'date': '',
            'snippet': msg_data.get('snippet', ''),
            'body': '',
            'spam': False
        }
        
        for header in headers:
            if header['name'] == 'Subject':
                email_info['subject'] = header['value']
            if header['name'] == 'From':
                email_info['from'] = header['value']
            if header['name'] == 'Date':
                email_info['date'] = header['value']
        
        # Get email body
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    text = base64.urlsafe_b64decode(data).decode('utf-8')
                    email_info['body'] = text
        else:
            data = payload['body']['data']
            text = base64.urlsafe_b64decode(data).decode('utf-8')
            email_info['body'] = text
        
        # Classify email
        full_text = email_info['subject'] + " " + email_info['body']
        email_info['spam'] = classify_email(full_text) == "spam"
        
        email_list.append(email_info)
    
    return email_list

# Update create_credentials_from_env()
def create_credentials_from_env():
    """Create credentials.json from environment variables"""
    credentials_file = 'credentials.json'
    
    if os.path.exists(credentials_file):
        return
    
    # Get credentials from environment
    credentials_data = {
        "installed": {
            "client_id": os.getenv("CLIENT_ID"),
            "project_id": os.getenv("PROJECT_ID"),
            "auth_uri": os.getenv("AUTH_URI"),
            "token_uri": os.getenv("TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER"),
            "client_secret": os.getenv("CLIENT_SECRET"),
            "redirect_uris": json.loads(os.getenv("REDIRECT_URIS"))
        }
    }
    
    with open(credentials_file, 'w') as f:
        json.dump(credentials_data, f, indent=2)
    print(f"Created {credentials_file} from environment variables")

@app.route('/')
def index():
    """Main endpoint to display emails"""
    try:
        emails = get_emails(max_results=20)
        return render_template('index.html', emails=emails)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    create_credentials_from_env()
    app.run(host='0.0.0.0', port=5000)