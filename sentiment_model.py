import pandas as pd
import numpy as np
import pickle
import os
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

# Download NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')

def clean_text(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    tokens = [t for t in tokens if t not in stop_words]
    return ' '.join(tokens)

def train_model():
    # Load dataset
    if not os.path.exists('dataset/sentiment_dataset.csv'):
        print("[ERROR] Dataset not found.")
        return

    df = pd.read_csv('dataset/sentiment_dataset.csv')
    
    # Preprocess
    df['clean_text'] = df['text'].apply(clean_text)
    
    X = df['clean_text']
    y = df['sentiment']
    
    # TF-IDF
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X_tfidf = vectorizer.fit_transform(X)
    
    # Multinomial Naive Bayes with high sensitivity
    model = MultinomialNB(alpha=0.1)
    model.fit(X_tfidf, y)
    
    # Save model and vectorizer
    if not os.path.exists('trained_model'):
        os.makedirs('trained_model')
        
    with open('trained_model/sentiment_model.pkl', 'wb') as f:
        pickle.dump(model, f)
        
    with open('trained_model/vectorizer.pkl', 'wb') as f:
        pickle.dump(vectorizer, f)
        
    print("[DEBUG] ML Model retrained for high sensitivity.")

if __name__ == "__main__":
    train_model()
