import os, sys
import requests
import time 
import json 
from kafka import KafkaProducer
import yaml 
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def load_config(config_file):
    config_path = os.path.join(os.path.dirname(__file__), '..', 'configuration', config_file)
    with open(config_path) as f:
        return yaml.safe_load(f)

news_api_config = load_config('news_api.yml')
kafka_config = load_config('kafka.yml')

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWS_API_URL = news_api_config['NEWS_API_URL']
CATEGORIES = news_api_config['CATEGORIES']
TOPIC = kafka_config['KAFKA_TOPIC']


producer = KafkaProducer(
    bootstrap_servers=kafka_config['BROKER'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    api_version=tuple(kafka_config['API_VERSION'])
)

def fetch_news(category, country = "us"):
    params = {
        "apiKey": NEWS_API_KEY,
        "category": category,
        "country": country,
        "pageSize": 5
    }
    response = requests.get(NEWS_API_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get("articles", [])
    else:
        print(f"Error fetching category {category}: {response.status_code}")
        return []
    

def stream_news():
    while True:
        for category in CATEGORIES:
            print(f"\nFetching category : {category}")
            articles = fetch_news(category=category)
            for article in articles:
                message = {
                    "title": article["title"],
                    "description": article["description"],
                    "url": article["url"],
                    "publishedAt": article["publishedAt"],
                    "source": article["source"]["name"],
                    "category": category
                }
                print(f"Sending: {message['title']}({category})")
                producer.send(TOPIC, value=message)
                time.sleep(2)
            time.sleep(60)

if __name__ ==  "__main__":
    stream_news()