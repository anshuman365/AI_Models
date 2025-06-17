# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
from transformers import pipeline
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
import re
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_secret_key')

# Download required NLTK resources
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

class TextSummarizer:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        
    def preprocess_text(self, text):
        """Clean and preprocess text"""
        # Remove extra whitespace and special characters
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\<.*?\>', '', text)
        return text.strip()

    def frequency_based_summarize(self, text, num_sentences=3):
        """Extractive summarization using word frequency"""
        sentences = sent_tokenize(text)
        
        words = word_tokenize(text.lower())
        words = [word for word in words if word.isalnum() and word not in self.stop_words]
        
        freq = {}
        for word in words:
            freq[word] = freq.get(word, 0) + 1
            
        max_freq = max(freq.values()) if freq else 1
        for word in freq:
            freq[word] /= max_freq
            
        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            for word in word_tokenize(sentence.lower()):
                if word in freq:
                    sentence_scores[i] = sentence_scores.get(i, 0) + freq[word]
                    
        if not sentence_scores:
            return "No significant sentences found."
            
        top_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:num_sentences]
        return ' '.join([sentences[i] for i in sorted(top_sentences)])
    
    def textrank_summarize(self, text, num_sentences=3):
        """Extractive summarization using TextRank algorithm"""
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = TextRankSummarizer()
        summary = summarizer(parser.document, num_sentences)
        return ' '.join([str(sentence) for sentence in summary])
    
    def abstractive_summarize(self, text, max_length=150, min_length=30):
        """Abstractive summarization using Transformers"""
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        result = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
        return result[0]['summary_text']
    
    def analyze_text(self, text):
        """Provide text analysis metrics"""
        words = word_tokenize(text)
        sentences = sent_tokenize(text)
        unique_words = set(word.lower() for word in words if word.isalnum())
        
        return {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "unique_words": len(unique_words),
            "avg_sentence_length": len(words)/len(sentences) if sentences else 0
        }

# Initialize summarizer
summarizer = TextSummarizer()

# Sample articles
SAMPLE_ARTICLES = {
    "Climate Change": """
    Climate change refers to long-term shifts in temperatures and weather patterns. 
    These shifts may be natural, but since the 1800s, human activities have been the main driver of climate change, 
    primarily due to the burning of fossil fuels (like coal, oil, and gas), which produces heat-trapping gases. 
    The consequences of climate change now include, among others, intense droughts, water scarcity, severe fires, 
    rising sea levels, flooding, melting polar ice, catastrophic storms and declining biodiversity.
    
    Scientists have high confidence that global temperatures will continue to rise for decades to come, 
    largely due to greenhouse gases produced by human activities. The Intergovernmental Panel on Climate Change (IPCC), 
    which includes more than 1,300 scientists from the United States and other countries, 
    forecasts a temperature rise of 2.5 to 10 degrees Fahrenheit over the next century.
    
    According to the IPCC, the extent of climate change effects on individual regions will vary over time 
    and with the ability of different societal and environmental systems to mitigate or adapt to change. 
    The Paris Agreement, adopted by 196 parties at COP 21 in Paris in 2015, aims to limit global warming to well below 2, 
    preferably to 1.5 degrees Celsius, compared to pre-industrial levels.
    """,
    
    "Machine Learning": """
    Machine learning (ML) is a type of artificial intelligence (AI) that allows software applications to become more accurate 
    at predicting outcomes without being explicitly programmed to do so. Machine learning algorithms use historical data 
    as input to predict new output values.
    
    There are four basic types of machine learning: supervised learning, unsupervised learning, semisupervised learning, 
    and reinforcement learning. Supervised learning requires the least amount of human intervention, 
    while reinforcement learning requires the most.
    
    Machine learning is important because it gives enterprises a view of trends in customer behavior and business operational patterns, 
    as well as supports the development of new products. Many of today's leading companies, such as Facebook, Google, and Uber, 
    make machine learning a central part of their operations. Machine learning has become a significant competitive differentiator 
    for many companies.
    """,
    
    "Renewable Energy": """
    Renewable energy is energy derived from natural sources that are replenished at a higher rate than they are consumed. 
    Sunlight and wind, for example, are such sources that are constantly being replenished. Renewable energy sources are plentiful 
    and all around us. Fossil fuels - coal, oil and gas - on the other hand, are non-renewable resources that take hundreds 
    of millions of years to form. Fossil fuels, when burned to produce energy, cause harmful greenhouse gas emissions.
    
    Generating renewable energy creates far lower emissions than burning fossil fuels. Transitioning from fossil fuels, 
    which currently account for the lion's share of emissions, to renewable energy is key to addressing the climate crisis.
    
    Renewables are now cheaper in most countries, and generate three times more jobs than fossil fuels. 
    Solar photovoltaics (PV) and onshore wind are the cheapest options for new electricity generation in a significant majority 
    of countries worldwide.
    """
}

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html', sample_articles=SAMPLE_ARTICLES.keys())

@app.route('/summarize', methods=['POST'])
def summarize():
    """Handle summarization request"""
    data = request.json
    text = data.get('text', '')
    method = data.get('method', 'TextRank')
    params = data.get('params', {})
    
    if not text.strip():
        return jsonify({"error": "Please enter text to summarize"}), 400
    
    # Preprocess text
    processed_text = summarizer.preprocess_text(text)
    
    # Get text metrics
    metrics = summarizer.analyze_text(processed_text)
    
    # Generate summary based on selected method
    try:
        if method == "TextRank":
            num_sentences = params.get('num_sentences', 3)
            summary = summarizer.textrank_summarize(processed_text, num_sentences)
        elif method == "Frequency":
            num_sentences = params.get('num_sentences', 3)
            summary = summarizer.frequency_based_summarize(processed_text, num_sentences)
        else:  # Transformer
            max_length = params.get('max_length', 150)
            min_length = params.get('min_length', 30)
            summary = summarizer.abstractive_summarize(processed_text, max_length, min_length)
    except Exception as e:
        app.logger.error(f"Summarization error: {str(e)}")
        return jsonify({"error": "Error during summarization. Please try again."}), 500
    
    # Calculate compression ratio
    summary_word_count = len(word_tokenize(summary))
    compression_ratio = f"{summary_word_count / metrics['word_count'] * 100:.1f}%" if metrics['word_count'] > 0 else "0%"
    
    return jsonify({
        "summary": summary,
        "metrics": metrics,
        "compression_ratio": compression_ratio,
        "summary_word_count": summary_word_count
    })

@app.route('/sample/<name>')
def sample_article(name):
    """Get sample article content"""
    if name in SAMPLE_ARTICLES:
        return jsonify({"content": SAMPLE_ARTICLES[name]})
    return jsonify({"error": "Article not found"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)