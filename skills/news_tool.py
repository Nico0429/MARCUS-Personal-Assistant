import requests
import os
import re
import random
import feedparser
from dotenv import load_dotenv

load_dotenv()

class NewsTool:
    def __init__(self):
        self.api_key = os.getenv("NEWS_API_KEY")
        self.base_url = "https://newsapi.org/v2/top-headlines"

    def fetch_weather(self):
        """Smart weather fetcher: Defaults to exact Home Base unless international travel is detected."""
        import os
        try:
            # 1. Load Home Base from .env (Fallback to New York)
            home_city = os.getenv("HOME_CITY", "New York")
            home_lat = os.getenv("HOME_LAT", "40.7128")
            home_lon = os.getenv("HOME_LON", "-74.0060")
            home_country = os.getenv("HOME_COUNTRY", "United States")

            # 2. Check current IP location
            loc_url = "http://ip-api.com/json/"
            loc_res = requests.get(loc_url, timeout=3).json()
            
            current_country = loc_res.get("country", "")
            
            # 3. The Smart Switch
            if current_country and current_country != home_country:
                # You traveled internationally! Use the dynamic IP location.
                lat = loc_res.get("lat")
                lon = loc_res.get("lon")
                city = loc_res.get("city", "your location")
            else:
                # You are in SA. Ignore ISP routing lies and use exact Home Base.
                lat = home_lat
                lon = home_lon
                city = home_city

            # 4. Fetch the weather
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            weather_res = requests.get(weather_url, timeout=3).json()
            temp = round(weather_res['current_weather']['temperature'])
            
            return f"It is currently {temp} degrees in {city}."
            
        except Exception as e:
            print(f"[ NewsTool ] Weather fetch failed: {e}")
            return ""
        

    def fetch_markets(self):
        """Fetches USD/ZAR and Bitcoin prices (No API Keys needed)"""
        try:
            # ER-API for Currency
            rates = requests.get("https://open.er-api.com/v6/latest/USD", timeout=3).json()
            zar = round(rates['rates']['ZAR'], 2)
            
            # CoinGecko for Crypto
            btc_res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=3).json()
            
            # THE FIX: Force it into a solid integer with no commas 
            btc = int(btc_res['bitcoin']['usd'])
            
            # Split it into two clean sentences for better TTS pacing
            return f"The Rand is trading at {zar} to the Dollar. And Bitcoin sits at {btc} dollars."
        except Exception as e:
            print(f"[ NewsTool ] Market fetch failed: {e}")
            return "Market data is currently unavailable."

    def fetch_daily_news(self, topic="general"):
        news_data = []

        def extract_long_summary(article):
            desc = (article.get('description') or "").strip()
            content = (article.get('content') or "").strip()
            if "[+" in content: content = content.split("[+")[0].strip()
            content = content.rstrip("…").rstrip("...")
            
            combined = ""
            if desc and content and not content.startswith(desc[:30]): combined = f"{desc} {content}"
            elif content: combined = content
            elif desc: combined = desc
            else: return "No extended summary was provided."
            
            last_period = combined.rfind('.')
            if last_period != -1: combined = combined[:last_period + 1]
            return combined

        local_count = 0
        
        # 1. Only fetch Local SA News if the user wants "general" news
        if topic == "general":
            try:
                n24_feed = feedparser.parse("http://feeds.news24.com/articles/news24/TopStories/rss")
                valid_local = [entry for entry in n24_feed.entries if hasattr(entry, 'title')]
                selected_local = random.sample(valid_local, min(3, len(valid_local)))
                
                for article in selected_local:
                    img_url = ""
                    if hasattr(article, 'enclosures') and len(article.enclosures) > 0:
                        img_url = article.enclosures[0].get('href', "")
                    elif hasattr(article, 'media_content') and len(article.media_content) > 0:
                        img_url = article.media_content[0].get('url', "")

                    if not img_url and hasattr(article, 'summary'):
                        img_match = re.search(r'src="([^"]+\.jpg|[^"]+\.png|[^"]+\.jpeg)"', article.summary, re.IGNORECASE)
                        if img_match: img_url = img_match.group(1)

                    if not img_url and hasattr(article, 'link'):
                        try:
                            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                            page_html = requests.get(article.link, headers=headers, timeout=3).text
                            og_match = re.search(r'property="og:image"[\s]+content="([^"]+)"', page_html, re.IGNORECASE)
                            if og_match: img_url = og_match.group(1)
                        except Exception: pass 

                    clean_desc = re.sub('<[^<]+>', '', article.get('summary', '')).strip()
                    if not clean_desc: clean_desc = "No further details were provided."

                    news_data.append({
                        'type': 'Local',
                        'title': article.title.strip(),
                        'description': clean_desc,
                        'image_url': img_url
                    })
                    local_count += 1
            except Exception as e:
                print(f"[ NewsTool ] News24 RSS fetch failed: {e}")

        # 2. Fetch Global News via NewsAPI 
        global_needed = 5 - local_count
        
        # --- THE FIX: Smart Routing between Category and Keyword Search ---
        valid_categories = ['business', 'entertainment', 'general', 'health', 'science', 'sports', 'technology']
        global_params = {'language': 'en', 'pageSize': 20, 'apiKey': self.api_key}
        
        if topic in valid_categories:
            global_params['category'] = topic
        else:
            # If it's a custom phrase like "AI OR Politics", use the search query parameter!
            global_params['q'] = topic 
        # ------------------------------------------------------------------

        try:
            global_response = requests.get(self.base_url, params=global_params).json()
            valid_global = [a for a in global_response.get('articles', []) if a.get('title') and a.get('urlToImage')]
            
            selected_global = random.sample(valid_global, min(global_needed, len(valid_global)))
            for article in selected_global:
                news_data.append({
                    'type': topic.capitalize() if topic in valid_categories else 'Focus',
                    'title': article['title'].split(" - ")[0].strip(),
                    'description': extract_long_summary(article),
                    'image_url': article['urlToImage']
                })
        except Exception as e:
            print(f"[ NewsTool ] Global fetch failed: {e}")

        random.shuffle(news_data)
        return news_data