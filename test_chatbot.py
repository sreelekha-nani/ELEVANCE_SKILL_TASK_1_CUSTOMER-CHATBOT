import unittest
from chatbot import SentimentChatbot
import os

class TestSentimentChatbot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chatbot = SentimentChatbot()

    def test_positive_sentiment(self):
        sentiment, confidence = self.chatbot.predict_sentiment("I love this product, it's amazing!")
        self.assertEqual(sentiment, "positive")
        self.assertGreaterEqual(confidence, 0.5)
        self.assertLessEqual(confidence, 1.0)

    def test_negative_sentiment(self):
        sentiment, confidence = self.chatbot.predict_sentiment("I am very disappointed with your service.")
        self.assertEqual(sentiment, "negative")
        self.assertGreaterEqual(confidence, 0.5)

    def test_neutral_sentiment(self):
        sentiment, confidence = self.chatbot.predict_sentiment("What are your working hours?")
        self.assertEqual(sentiment, "neutral")

    def test_empty_message(self):
        sentiment, confidence = self.chatbot.predict_sentiment("")
        self.assertEqual(sentiment, "neutral")
        self.assertEqual(confidence, 0.0)

    def test_long_message(self):
        long_text = "I am absolutely thrilled and happy with the product. " * 20
        sentiment, confidence = self.chatbot.predict_sentiment(long_text)
        self.assertEqual(sentiment, "positive")

    def test_special_characters(self):
        sentiment, confidence = self.chatbot.predict_sentiment("!!! @#$% ^&*()")
        self.assertEqual(sentiment, "neutral")

    def test_smart_response_context(self):
        # Test keyword 'hours' in neutral
        response = self.chatbot.get_smart_response("What are your hours?", "neutral")
        self.assertIn("9:00 AM to 6:00 PM", response)
        
        # Test keyword 'working' in negative
        response = self.chatbot.get_smart_response("It's not working", "negative")
        self.assertIn("troubleshoot", response.lower())

if __name__ == '__main__':
    unittest.main()
