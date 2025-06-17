# text_summarizer.py
import streamlit as st
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
from transformers import pipeline
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
import re

# Download required NLTK resources
nltk.download('punkt')
nltk.download('stopwords')

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

def main():
    st.set_page_config(page_title="NLP Text Summarizer", page_icon="✂️")
    st.title("✂️ NLP Text Summarizer")
    st.write("Shorten articles using extractive or abstractive summarization techniques")
    
    # Initialize session state
    if 'original_text' not in st.session_state:
        st.session_state.original_text = ""
    
    # Method selection
    method = st.sidebar.radio("Summarization Method", 
                            ["TextRank (Extractive)", 
                             "Frequency-Based (Extractive)", 
                             "Transformer (Abstractive)"])
    
    # Input options
    input_option = st.sidebar.radio("Input Source", ["Text Area", "Sample Article"])
    
    # Load sample articles
    sample_articles = {
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
        """
    }
    
    # Text input handling
    if input_option == "Text Area":
        text = st.text_area("Paste your article here:", height=300, key="input_text")
    else:
        selected_article = st.sidebar.selectbox("Choose sample article", list(sample_articles.keys()))
        text = sample_articles[selected_article]
        st.text_area("Article preview:", value=text, height=300, disabled=True)
    
    # Process text when available
    if st.button("Summarize") and text.strip():
        # Save original text
        st.session_state.original_text = text
        
        # Initialize summarizer
        summarizer = TextSummarizer()
        processed_text = summarizer.preprocess_text(text)
        
        # Get text metrics
        metrics = summarizer.analyze_text(processed_text)
        
        # Create columns for metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Original Words", metrics['word_count'])
        col2.metric("Sentences", metrics['sentence_count'])
        col3.metric("Unique Words", metrics['unique_words'])
        col4.metric("Avg. Sentence Length", f"{metrics['avg_sentence_length']:.1f} words")
        
        # Generate summary based on selected method
        with st.spinner("Generating summary..."):
            if "TextRank" in method:
                num_sentences = st.sidebar.slider("Number of sentences", 1, 10, 3)
                summary = summarizer.textrank_summarize(processed_text, num_sentences)
                compression_ratio = f"{len(summary.split()) / metrics['word_count'] * 100:.1f}%"
                
            elif "Frequency" in method:
                num_sentences = st.sidebar.slider("Number of sentences", 1, 10, 3)
                summary = summarizer.frequency_based_summarize(processed_text, num_sentences)
                compression_ratio = f"{len(summary.split()) / metrics['word_count'] * 100:.1f}%"
                
            else:  # Abstractive
                max_length = st.sidebar.slider("Max Length", 50, 300, 150)
                min_length = st.sidebar.slider("Min Length", 10, 100, 30)
                summary = summarizer.abstractive_summarize(processed_text, max_length, min_length)
                compression_ratio = f"{len(summary.split()) / metrics['word_count'] * 100:.1f}%"
        
        # Display results
        st.subheader("📝 Summary")
        st.info(f"Compression ratio: {compression_ratio}")
        st.write(summary)
        
        # Add download button
        st.download_button(
            label="Download Summary",
            data=summary,
            file_name="summary.txt",
            mime="text/plain"
        )
        
        # Show comparison
        with st.expander("Original Text vs Summary"):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Original Text")
                st.write(st.session_state.original_text)
            with col2:
                st.subheader("Summary")
                st.write(summary)

if __name__ == "__main__":
    main()