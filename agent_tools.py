import requests
import json
import feedparser
from textblob import TextBlob
from datetime import datetime
from typing import List, Dict
from decouple import config
from schemas import BinancePriceData, CoingeckoMarketData


class CryptoTools:
    def __init__(self):
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"
        self.binance_base_url = "https://api.binance.com/api/v3"
        self.rss_feed_urls = [
            "https://cointelegraph.com/rss",
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://decrypt.co/feed",
        ]

    # Crypto Data Fetchers
    def fetch_coingecko_list(self):
        """
        Fetches a list of supported cryptocurrencies from CoinGecko.
        """
        url = f"{self.coingecko_base_url}/coins/list"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching CoinGecko data: {response.status_code}")
            return None

    def fetch_coingecko_market_data(self, coin_id: str):
        """
        Fetches market data for a specific cryptocurrency from CoinGecko.
        :param coin_id: The ID of the cryptocurrency (e.g., 'bitcoin').
        :return: JSON data of market information.
        """
        url = f"{self.coingecko_base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": coin_id,
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching CoinGecko data: {response.status_code}")
            return None

    def fetch_binance_price(self, symbol: str):
        """
        Fetches the latest price for a trading pair from Binance.
        :param symbol: The trading pair symbol (e.g., 'BTCUSDT').
        :return: JSON data of the latest price.
        """
        url = f"{self.binance_base_url}/ticker/price"
        params = {"symbol": symbol}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching Binance data: {response.status_code}")
            return None

    # News Fetchers
    def fetch_cryptopanic_news(self) -> List[Dict]:
        """Fetch crypto news from CryptoPanic API."""
        url = "https://cryptopanic.com/api/v1/posts/"
        params = {
            "auth_token": config("CRYPTOPANIC_API_KEY"),
            "filter": "trending",
            "kind": "news",
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return [
                {
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "source": "CryptoPanic",
                    "published_at": article.get("published_at"),
                    "sentiment": article.get("votes", {}).get("important", "neutral"),
                }
                for article in data.get("results", [])
            ]
        else:
            raise Exception("Failed to fetch news from CryptoPanic API")

    def fetch_rss_news(self) -> List[Dict]:
        """Fetch crypto news from RSS feeds."""
        articles = []
        for url in self.rss_feed_urls:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                articles.append(
                    {
                        "title": entry.title,
                        "url": entry.link,
                        "source": feed.feed.title,
                        "published_at": (
                            entry.published if hasattr(entry, "published") else None
                        ),
                        "content": entry.summary,
                    }
                )
        return articles

    # Sentiment Analysis
    def analyze_sentiment(self, text: str) -> str:
        """Perform sentiment analysis using TextBlob."""
        analysis = TextBlob(text)
        if analysis.sentiment.polarity > 0:
            return "bullish"
        elif analysis.sentiment.polarity < 0:
            return "bearish"
        else:
            return "neutral"

    # News Processing
    def process_news_articles(self, articles: List[Dict]) -> List[Dict]:
        """Process news articles by adding sentiment and formatting timestamps."""
        for article in articles:
            content = article.get("content", article.get("title", ""))
            article["sentiment"] = self.analyze_sentiment(content)
            if article.get("published_at"):
                try:
                    # Try to parse the datetime with the expected format
                    article["published_at"] = datetime.strptime(
                        article["published_at"], "%Y-%m-%dT%H:%M:%S%z"
                    ).strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # If the first format fails, try parsing with the alternative format
                    article["published_at"] = datetime.strptime(
                        article["published_at"], "%a, %d %b %Y %H:%M:%S %z"
                    ).strftime("%Y-%m-%d %H:%M:%S")
        return articles

    # Save to JSON
    def save_to_json(self, data: List[Dict], filename: str):
        """Save processed data to a JSON file."""
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    # Main function to aggregate and process news
    def aggregate_and_process_news(self, rss_feeds: List[str]):
        """Aggregate news from CryptoPanic and RSS feeds, then process and save to JSON."""
        print("Fetching news from CryptoPanic...")
        cryptopanic_news = self.fetch_cryptopanic_news()

        print("Fetching news from RSS feeds...")
        rss_feeds = [
            "https://cointelegraph.com/rss",
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://decrypt.co/feed",
        ]
        rss_news = self.fetch_rss_news(rss_feeds)

        print("Processing news articles...")
        all_articles = cryptopanic_news + rss_news
        processed_articles = self.process_news_articles(all_articles)
        return processed_articles

        # print("Saving processed news to JSON file...")
        # self.save_to_json(processed_articles, "crypto_news.json")

        # print("News aggregation completed! File saved as crypto_news.json")


crypto_tools = CryptoTools()
# Example usage
if __name__ == "__main__":
    crypto_tools = CryptoTools()

    # Example of fetching market data
    coingecko_data = crypto_tools.fetch_coingecko_market_data(coin_id="bitcoin")
    print("CoinGecko Market Data:", json.dumps(coingecko_data, indent=2))

    # Example of aggregating and processing news
    rss_feeds = [
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://decrypt.co/feed",
    ]
    crypto_tools.aggregate_and_process_news(rss_feeds)
