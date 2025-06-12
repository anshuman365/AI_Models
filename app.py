from flask import Flask, render_template, send_file, redirect, url_for
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
import joblib
import os
import threading

app = Flask(__name__)
app.config['MODEL_READY'] = False
app.config['TRAINING'] = False

def train_model():
    app.config['TRAINING'] = True
    try:
        # Load dataset
        print("Downloading dataset...")
        df = pd.read_csv('https://raw.githubusercontent.com/mwitiderrick/spam/master/spam.csv', encoding='latin-1')
        df = df[['v1', 'v2']]
        df.columns = ['label', 'text']
        
        # Preprocess data
        df['label'] = df['label'].map({'ham': 0, 'spam': 1})
        X = df['text']
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
    app.run(host='0.0.0.0', port=5000, debug=True)