# app.py
import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image
import spacy
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
from umap import UMAP
from bertopic import BERTopic
import gc
import os
import base64
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import time
import joblib

# --------------------------
# Configuration
# --------------------------
st.set_page_config(
    layout="wide",
    page_title="IntelliInsight",
    page_icon="🧠",
    initial_sidebar_state="expanded"
)

# --------------------------
# Model Initialization (CPU Optimized)
# --------------------------
@st.cache_resource(show_spinner=False)
def load_models():
    """Load all ML models optimized for CPU"""
    models = {}
    
    # Text models
    try:
        models['sentiment'] = pipeline(
            "text-classification",
            model="distilbert-base-uncased-finetuned-sst-2-english"
        )
        models['ner'] = spacy.load("en_core_web_sm")
        models['topic'] = BERTopic(embedding_model=SentenceTransformer('all-MiniLM-L6-v2'))
    except:
        st.error("Error loading text models. Please check requirements.txt")
        
    # Image model - use lightweight version
    try:
        models['image_model'] = torch.hub.load(
            'pytorch/vision', 
            'mobilenet_v2', 
            pretrained=True
        ).eval()
    except:
        st.error("Error loading image model. Please check PyTorch installation")
    
    return models

# --------------------------
# Image Processing Pipeline
# --------------------------
def image_classification(image, model):
    """CPU-optimized image classification"""
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406], 
            std=[0.229, 0.224, 0.225]
        )
    ])
    
    input_tensor = transform(image).unsqueeze(0)
    
    with torch.no_grad():
        output = model(input_tensor)
    
    probabilities = torch.nn.functional.softmax(output[0], dim=0)
    
    # Get ImageNet classes
    try:
        with open('imagenet_classes.txt') as f:
            classes = [line.strip() for line in f.readlines()]
    except:
        classes = [str(i) for i in range(1000)]
    
    # Get top predictions
    top5_prob, top5_catid = torch.topk(probabilities, 5)
    results = {classes[top5_catid[i]]: top5_prob[i].item() for i in range(5)}
    
    # Release memory
    gc.collect()
    
    return results

# --------------------------
# Text Analytics
# --------------------------
def analyze_text(text, models):
    """Text analysis pipeline"""
    # Sentiment analysis
    sentiment = models['sentiment'](text)
    
    # NER with spaCy
    doc = models['ner'](text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    
    # Topic modeling
    topics, _ = models['topic'].transform([text])
    
    # Keyword extraction
    wordcloud = WordCloud(width=800, height=400).generate(text)
    
    return {
        "sentiment": sentiment,
        "entities": entities,
        "topic": topics[0] if topics else -1,
        "wordcloud": wordcloud
    }

# --------------------------
# Data Visualization Engine
# --------------------------
def advanced_visualization(df):
    """Interactive visualization with Plotly"""
    # Auto-detect column types
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    
    # 3D Scatter Plot Matrix
    if len(numeric_cols) >= 3:
        fig1 = px.scatter_matrix(
            df,
            dimensions=numeric_cols[:3],
            color=categorical_cols[0] if len(categorical_cols) > 0 else None,
            title="3D Scatter Matrix",
            height=700
        )
    else:
        fig1 = px.scatter(df, title="Scatter Plot")
    
    # Time Series Analysis
    time_fig = None
    if 'date' in df.columns:
        try:
            df['date'] = pd.to_datetime(df['date'])
            time_fig = px.line(df, x='date', y=numeric_cols[0], title="Time Series")
        except:
            pass
    
    # Correlation Matrix
    corr_fig = None
    if len(numeric_cols) > 1:
        corr_matrix = df[numeric_cols].corr()
        corr_fig = px.imshow(
            corr_matrix,
            text_auto=True,
            title="Correlation Matrix",
            aspect="auto"
        )
    
    return fig1, time_fig, corr_fig

# --------------------------
# File Handling Utilities
# --------------------------
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temporary location"""
    try:
        with open(os.path.join("temp_files", uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    except:
        return False

# --------------------------
# UI Components
# --------------------------
def render_sidebar(models_loaded):
    """Render the sidebar configuration"""
    with st.sidebar:
        st.title("⚙️ IntelliInsight Configuration")
        
        st.subheader("Resource Monitor")
        if models_loaded:
            st.success("Models loaded successfully")
        else:
            st.warning("Models not loaded")
        
        st.divider()
        st.subheader("Performance Settings")
        st.caption("Adjust for large datasets")
        sample_size = st.slider("Data Sampling %", 1, 100, 100)
        
        st.divider()
        st.caption("© 2023 IntelliInsight | Cloud-Optimized Analytics")

# --------------------------
# Main Application
# --------------------------
def main():
    # Initialize session state
    if 'models_loaded' not in st.session_state:
        st.session_state.models_loaded = False
    
    # Create temp directory
    os.makedirs("temp_files", exist_ok=True)
    
    # Page header
    st.title("🧠 IntelliInsight - Cloud Analytics Platform")
    st.caption("Advanced data analysis platform optimized for cloud deployment")
    
    # Load models
    if not st.session_state.models_loaded:
        with st.spinner("🚀 Loading AI models (this may take a minute)..."):
            try:
                models = load_models()
                st.session_state.models = models
                st.session_state.models_loaded = True
            except Exception as e:
                st.error(f"Model loading failed: {str(e)}")
                st.stop()
    
    # Render sidebar
    render_sidebar(st.session_state.models_loaded)
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs([
        "📊 Data Visualization", 
        "📝 Text Analytics", 
        "🖼️ Image Intelligence"
    ])

    # Data Visualization Tab
    with tab1:
        st.header("Advanced Data Visualization")
        uploaded_file = st.file_uploader(
            "Upload Dataset", 
            type=["csv", "xlsx"],
            accept_multiple_files=False
        )
        
        if uploaded_file:
            # Save file temporarily
            if save_uploaded_file(uploaded_file):
                file_path = os.path.join("temp_files", uploaded_file.name)
                
                # Load data
                if uploaded_file.name.endswith('.xlsx'):
                    df = pd.read_excel(file_path)
                else:
                    df = pd.read_csv(file_path)
                
                # Cleanup
                try:
                    os.remove(file_path)
                except:
                    pass
                
                st.success(f"Loaded {len(df)} rows with {len(df.columns)} columns")
                
                # Advanced visualization
                fig1, time_fig, corr_fig = advanced_visualization(df)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(fig1, use_container_width=True)
                    if corr_fig:
                        st.plotly_chart(corr_fig, use_container_width=True)
                with col2:
                    if time_fig:
                        st.plotly_chart(time_fig, use_container_width=True)
                    
                    # Data profiling
                    with st.expander("Data Profile Report"):
                        st.subheader("Data Summary")
                        col1, col2 = st.columns(2)
                        col1.metric("Total Rows", len(df))
                        col2.metric("Total Columns", len(df.columns))
                        
                        st.subheader("Missing Values")
                        missing_df = pd.DataFrame(df.isnull().sum(), columns=["Missing Values"])
                        st.dataframe(missing_df, use_container_width=True)
            else:
                st.error("Failed to save uploaded file")

    # Text Analytics Tab
    with tab2:
        st.header("Text Analysis")
        text_input = st.text_area("Enter text for analysis", height=200, 
                                 placeholder="Paste any text for sentiment analysis, entity recognition, and topic modeling...")
        
        if st.button("Analyze Text", use_container_width=True) and text_input.strip():
            with st.spinner("🔍 Analyzing text..."):
                try:
                    results = analyze_text(text_input, st.session_state.models)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Sentiment Analysis")
                        sentiment_label = results['sentiment'][0]['label']
                        sentiment_score = results['sentiment'][0]['score']
                        if sentiment_label == "POSITIVE":
                            st.success(f"😄 Positive ({sentiment_score:.0%} confidence)")
                        elif sentiment_label == "NEGATIVE":
                            st.error(f"😠 Negative ({sentiment_score:.0%} confidence)")
                        else:
                            st.info(f"😐 Neutral ({sentiment_score:.0%} confidence)")
                        
                        st.subheader("Named Entities")
                        if results['entities']:
                            entities_df = pd.DataFrame(results['entities'], columns=["Entity", "Type"])
                            st.dataframe(entities_df, hide_index=True, use_container_width=True)
                        else:
                            st.info("No named entities detected")
                        
                    with col2:
                        st.subheader("Topic Modeling")
                        if results['topic'] != -1:
                            st.info(f"Detected Topic ID: #{results['topic']}")
                        else:
                            st.warning("No topics detected")
                        
                        st.subheader("Keyword Cloud")
                        fig, ax = plt.subplots()
                        ax.imshow(results['wordcloud'], interpolation='bilinear')
                        ax.axis("off")
                        st.pyplot(fig)
                        
                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")

    # Image Intelligence Tab
    with tab3:
        st.header("Image Classification")
        image_file = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
        
        if image_file:
            image = Image.open(image_file)
            st.image(image, caption="Uploaded Image", use_column_width=True)
            
            if st.button("Analyze Image", use_container_width=True):
                with st.spinner("🤖 Processing image..."):
                    try:
                        results = image_classification(
                            image, 
                            st.session_state.models['image_model']
                        )
                        
                        # Display results
                        st.subheader("Classification Results")
                        results_df = pd.DataFrame(
                            list(results.items()), 
                            columns=["Class", "Confidence"]
                        ).sort_values("Confidence", ascending=False)
                        
                        # Interactive chart
                        fig = px.bar(
                            results_df, 
                            x="Confidence", 
                            y="Class", 
                            orientation='h',
                            color="Confidence",
                            color_continuous_scale="Viridis"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Show top prediction
                        top_class, top_conf = list(results.items())[0]
                        st.success(f"**Top Prediction:** {top_class} ({top_conf:.0%} confidence)")
                        
                    except Exception as e:
                        st.error(f"Image processing failed: {str(e)}")

if __name__ == "__main__":
    main()