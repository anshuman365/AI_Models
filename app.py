from flask import Flask, render_template, send_file, redirect, url_for
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
import joblib
import threading
import requests
import zipfile
import io
import os

app = Flask(__name__)
app.config['MODEL_READY'] = False
app.config['TRAINING'] = False

def download_dataset():
    """Try multiple sources to download the dataset"""
    urls = [
        # Option 1
        ("https://raw.githubusercontent.com/Ankit152/spam-sms/master/spam.csv", 
         lambda: pd.read_csv("https://raw.githubusercontent.com/Ankit152/spam-sms/master/spam.csv", encoding='latin-1')),
        
        # Option 2
        ("https://raw.githubusercontent.com/mohitgupta-omg/Kaggle-SMS-Spam-Collection-Dataset-/master/spam.csv", 
         lambda: pd.read_csv("https://raw.githubusercontent.com/mohitgupta-omg/Kaggle-SMS-Spam-Collection-Dataset-/master/spam.csv", encoding='latin-1')),
        
        # Option 3 (different column names)
        ("https://raw.githubusercontent.com/stedy/Machine-Learning-with-R-datasets/master/sms_spam.csv",
         lambda: pd.read_csv("https://raw.githubusercontent.com/stedy/Machine-Learning-with-R-datasets/master/sms_spam.csv")),
        
        # Option 4 (UCI zip file)
        ("https://archive.ics.uci.edu/ml/machine-learning-databases/00228/smsspamcollection.zip",
         lambda: download_and_extract_uci())
    ]
    
    for url, download_func in urls:
        try:
            print(f"Trying dataset from: {url}")
            df = download_func()
            if not df.empty:
                print(f"Successfully loaded dataset from {url}")
                return df
        except Exception as e:
            print(f"Failed to load from {url}: {str(e)}")
    
    raise Exception("All dataset sources failed")

def download_and_extract_uci():
    """Download and extract UCI dataset"""
    response = requests.get("https://archive.ics.uci.edu/ml/machine-learning-databases/00228/smsspamcollection.zip")
    response.raise_for_status()
    
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        with z.open('SMSSpamCollection') as f:
            df = pd.read_csv(f, sep='\t', header=None, names=['label', 'text'])
    return df

def train_model():
    app.config['TRAINING'] = True
    try:
        # Load dataset
        print("Downloading dataset...")
        df = download_dataset()
        
        # Handle different column names
        if 'v1' in df.columns and 'v2' in df.columns:
            df = df[['v1', 'v2']].rename(columns={'v1': 'label', 'v2': 'text'})
        elif 'type' in df.columns:
            df = df.rename(columns={'type': 'label'})
        
        # Preprocess data
        df['label'] = df['label'].map({'ham': 0, 'spam': 1, 'yes':1, 'no':0})
        df['label'] = pd.to_numeric(df['label'], errors='coerce').fillna(0).astype(int)
        
        X = df['text'].fillna('')
        y = df['label']
        
        # Train model
        print("Training model...")
        model = make_pipeline(TfidfVectorizer(max_features=5000), MultinomialNB())
        model.fit(X, y)
        
        # Save model
        joblib.dump(model.named_steps['multinomialnb'], 'spam_model.joblib')
        joblib.dump(model.named_steps['tfidfvectorizer'], 'tfidf_vectorizer.joblib')
        print("Model saved successfully")
        app.config['MODEL_READY'] = True
    except Exception as e:
        print(f"Error during training: {str(e)}")
    finally:
        app.config['TRAINING'] = False

@app.route('/')
def index():
    status = "ready" if app.config['MODEL_READY'] else "not_ready"
    training = app.config['TRAINING']
    return render_template('index.html', status=status, training=training)

@app.route('/train', methods=['POST'])
def start_training():
    if not app.config['TRAINING'] and not app.config['MODEL_READY']:
        thread = threading.Thread(target=train_model)
        thread.start()
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    if filename in ['spam_model.joblib', 'tfidf_vectorizer.joblib']:
        return send_file(filename, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)