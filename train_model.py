# train_model.py (run locally to create ML model)
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score
import joblib

# Load dataset
df = pd.read_csv('https://raw.githubusercontent.com/mwitiderrick/spam/master/spam.csv', encoding='latin-1')
df = df[['v1', 'v2']]
df.columns = ['label', 'text']

# Preprocess data
df['label'] = df['label'].map({'ham': 0, 'spam': 1})
X = df['text']
y = df['label']

# Train model
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = make_pipeline(TfidfVectorizer(max_features=5000), MultinomialNB())
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")

# Save model
joblib.dump(model.named_steps['multinomialnb'], 'spam_model.joblib')
joblib.dump(model.named_steps['tfidfvectorizer'], 'tfidf_vectorizer.joblib')