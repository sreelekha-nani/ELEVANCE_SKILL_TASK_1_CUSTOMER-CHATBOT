import pickle
import re
import nltk
import os
import random
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from textblob import TextBlob

# Ensure NLTK data is available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class SentimentChatbot:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.load_model()
        
        # Comprehensive Response Rules
        self.context_responses = {
            "positive": {
                "general": ["Thank you for your positive feedback! We're glad you're happy.", "Awesome! Your satisfaction is our priority."],
                "product": ["Thank you for your feedback! We're delighted that you're enjoying our product."],
                "support": ["We appreciate your kind words. Our team is always happy to help."]
            },
            "negative": {
                "general": ["I'm sorry to hear about your experience. I've logged this as a support ticket for our team to investigate."],
                "working": ["I understand your frustration regarding the product failure. A support ticket has been created and escalated."],
                "refund": ["I understand you're looking for a refund. I've created a support ticket for our billing department. Please provide your order ID."]
            },
            "neutral": {
                "general": ["Thank you for your message. How can I assist you today?", "Understood. Is there anything specific you would like to know?"],
                "hours": ["Our support team is available from 9:00 AM to 6:00 PM, Monday to Friday.", "We are open weekdays from 9 AM to 6 PM."],
                "password": ["You can reset your password by clicking the 'Forgot Password' option on the login page."],
                "greeting": ["Hello! How can I assist you today?", "Hi there! How can I help you?"]
            }
        }
        
        # Refined Emotion Lexicon
        self.emotion_lexicon = {
            "happy": ["love", "great", "amazing", "happy", "excellent", "wonderful", "satisfied", "thanks", "thank"],
            "angry": ["worst", "terrible", "angry", "useless", "unacceptable", "horrible", "hate"],
            "frustrated": ["refund", "disappointed", "frustrated", "failed", "defective", "damaged", "stopped working", "broken", "fail"],
            "excited": ["wow", "excited", "awesome", "perfect", "brilliant", "incredible"],
            "confused": ["how", "why", "where", "what", "confused", "manual", "help", "question", "issue", "support"],
        }

    def load_model(self):
        try:
            if os.path.exists('trained_model/sentiment_model.pkl'):
                with open('trained_model/sentiment_model.pkl', 'rb') as f:
                    self.model = pickle.load(f)
                with open('trained_model/vectorizer.pkl', 'rb') as f:
                    self.vectorizer = pickle.load(f)
        except Exception:
            pass

    def predict_sentiment(self, text):
        if not text: return "neutral", 0.0
        text_lower = text.lower()
        
        # High-sensitivity problem markers
        negative_markers = ["worst", "terrible", "awful", "horrible", "hate", "disappointed", "garbage", "useless", "broken", "failed", "refund", "not working"]
        if any(word in text_lower for word in negative_markers):
            return "negative", 0.95
            
        positive_markers = ["love", "excellent", "amazing", "great", "best", "perfect", "wonderful"]
        if any(word in text_lower for word in positive_markers):
            return "positive", 0.95

        analysis = TextBlob(text)
        polarity = analysis.sentiment.polarity
        if polarity > 0.1: sentiment = "positive"
        elif polarity < -0.1: sentiment = "negative"
        else: sentiment = "neutral"
        
        confidence = 0.5 + (abs(polarity) / 2)
        return sentiment, float(confidence)

    def predict_emotion(self, text):
        text_lower = text.lower()
        
        # Priority mapping triggers
        frustrated_triggers = ["refund", "disappointed", "frustrated", "failed", "defective", "damaged", "stopped working", "broken", "not working"]
        angry_triggers = ["worst", "terrible", "angry", "useless", "unacceptable"]
        
        if any(w in text_lower for w in angry_triggers):
            return "angry", 0.95
        if any(w in text_lower for w in frustrated_triggers):
            return "frustrated", 0.95

        counts = {emotion: 0 for emotion in self.emotion_lexicon}
        for emotion, keywords in self.emotion_lexicon.items():
            for word in keywords:
                if word in text_lower: counts[emotion] += 1
        
        max_emotion = max(counts, key=counts.get)
        if counts[max_emotion] == 0:
            return "neutral", 0.5
        
        confidence = min(0.5 + (counts[max_emotion] * 0.15), 0.95)
        return max_emotion, float(confidence)

    def get_auto_priority(self, sentiment, emotion):
        """Logic: Auto-prioritize tickets based on sentiment and emotion."""
        if sentiment == 'negative' and emotion == 'angry':
            return 'Critical'
        if sentiment == 'negative' and emotion == 'frustrated':
            return 'High'
        if sentiment == 'neutral':
            return 'Medium'
        return 'Low'

    def get_smart_response(self, text, sentiment, ticket_num=None, priority=None):
        text_lower = text.lower()
        base_resp = ""
        
        # Greetings check
        greetings = ['hello', 'hi', 'hey']
        if any(text_lower.startswith(g) for g in greetings):
            return random.choice(self.context_responses["neutral"]["greeting"])

        if sentiment == "positive":
            if any(w in text_lower for w in ["product", "item"]): base_resp = random.choice(self.context_responses["positive"]["product"])
            elif any(w in text_lower for w in ["support", "team"]): base_resp = random.choice(self.context_responses["positive"]["support"])
            else: base_resp = random.choice(self.context_responses["positive"]["general"])
            
        elif sentiment == "negative":
            if any(w in text_lower for w in ["working", "broken", "failed"]): base_resp = random.choice(self.context_responses["negative"]["working"])
            elif any(w in text_lower for w in ["refund", "billing"]): base_resp = random.choice(self.context_responses["negative"]["refund"])
            else: base_resp = random.choice(self.context_responses["negative"]["general"])
            
            if ticket_num:
                p_text = f" as {priority} priority" if priority else ""
                base_resp += f" (Support Ticket Created: {ticket_num}{p_text})"
                
        else: # neutral
            if any(w in text_lower for w in ["hours", "time"]): base_resp = random.choice(self.context_responses["neutral"]["hours"])
            elif any(w in text_lower for w in ["password", "reset"]): base_resp = random.choice(self.context_responses["neutral"]["password"])
            else: base_resp = random.choice(self.context_responses["neutral"]["general"])
            
            if ticket_num:
                 base_resp += f" (Support Ticket Created: {ticket_num})"
            
        return base_resp
