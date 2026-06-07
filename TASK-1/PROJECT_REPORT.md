# Project Report: AI-Powered Sentiment Analysis Customer Support Chatbot

## 1. Introduction
The objective of this project was to develop an intelligent customer support chatbot capable of identifying user sentiments (Positive, Negative, Neutral) and providing appropriate responses. The system aims to enhance user experience by acknowledging customer emotions and tailoring bot interactions accordingly.

## 2. Problem Statement
Traditional chatbots often fail to understand the emotional context of a user's message, leading to generic or frustrating responses. By integrating sentiment analysis, the chatbot can prioritize urgent (negative) issues and acknowledge positive feedback more effectively.

## 3. Methodology

### 3.1 Data Collection
A custom dataset of 50 phrases was created, covering common customer support interactions.

### 3.2 Preprocessing
Text data underwent several cleaning steps:
- Case conversion to lowercase.
- Removal of special characters and punctuation.
- Tokenization.
- Stopword removal.

### 3.3 Model Selection
Three models were evaluated:
- **Logistic Regression**
- **Multinomial Naive Bayes**
- **Random Forest**

**Multinomial Naive Bayes** was selected as the best performing model based on F1-Score in this specific small-scale scenario.

### 3.4 Backend Development
- **Flask** was used for the web framework.
- **SQLAlchemy** managed the SQLite database with 4 tables: `Users`, `Conversations`, `Messages`, and `Sentiments`.

### 3.5 Frontend Design
A premium UI was crafted using **Midnight Teal** theme, implementing:
- Glassmorphism effects.
- Bootstrap 5 for layout.
- Chart.js for data visualization.

## 4. Features & Functionality
- **Real-time Sentiment Detection:** Messages are analyzed as soon as they are sent.
- **Adaptive Responses:** Different response sets for each sentiment.
- **Admin Analytics:** Visual representation of sentiment distribution.
- **Conversation History:** Users can see their past messages and bot replies.

## 5. Conclusion
The Sentiment Analysis Chatbot successfully demonstrates the integration of machine learning into a functional web application. The premium UI and real-time analysis provide a professional feel suitable for SaaS applications.

---

# API Documentation

## Authentication
### `POST /register`
Registers a new user.
- **Payload:** `username`, `email`, `password`.

### `POST /login`
Logs in a user.
- **Payload:** `email`, `password`.

## Chat
### `POST /send_message`
Analyzes and responds to a user message.
- **Request Body (JSON):**
  - `message`: string
  - `conversation_id`: int
- **Response Body (JSON):**
  - `user_message`: object (text, sentiment, confidence, timestamp)
  - `bot_message`: object (text, timestamp)

## Analytics
### `GET /api/sentiment_data`
Returns sentiment distribution for charts.
- **Response Body (JSON):**
  - `labels`: array of strings
  - `values`: array of integers
