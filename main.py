import os
import ssl
import smtplib
import feedparser

from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

SENDER = os.getenv("GMAIL_ADDRESS")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT = "adedolaposamuel21@gmail.com"

SEARCH_TERMS = [
    "kidnapping Nigeria",
    "abducted Nigeria",
    "kidnap victims Nigeria",
]

GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"

def fetch_news():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    articles = {}

    for term in SEARCH_TERMS:
        params = {
            "q": f"{term} when:1d",
            "hl": "en-NG",
            "g1": "NG",
            "ceid": "NG:en",
        }

        url = f"{GOOGLE_NEWS_RSS_URL}?{urlencode(params)}"
        feed = feedparser.parse(url)

        for item in feed.enteries:
            link = item.get("link", "")
            title = item.get("title", "Untitled")

            if not link or link in articles:
                continue

            published = item.get("published")

            if not published:
                continue

            try:
                from email.utils import parsedate_to_datetime

                published_at = parsedate_to_datetime(published)

                if published_at.tzinfo is None:
                    published_at = published_at.replace(
                        tzinfo=timezone.utc)
                if published_at < cutoff:
                    continue

            except (ValueError, TypeError):
                continue

            source = item.get("source", {}).get(
                "title", "Unknown Source"
            )

            articles[link] = {
                "title" : title,
                "link": link,
                "source": source,
                "published": published_at,
            }

    return sorted(
        articles.values(),
        key = lambda article: article["published"],
        reverse = True
    )

def send_email(articles):
    if not SENDER or not APP_PASSWORD:
        raise ValueError(
            "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env"
        )

    message = EmailMessage()
    today = datetime.now().strftime("%d %B %Y")
    
    message["Subject"] = f"Nigeria Kidnapping News Digest - {today}"
    message["From"] = SENDER
    message["To"] = RECIPIENT

    if not articles:
        body = (
            "No matching kidnapping news articles were found "
            "in the last 24 hours.\n\n"
            "This does not confirm that no incidents occured"
        )
    else:
        lines = [
            f"NIGERIA KIDNAPPING NEWS DIGETS",
            f"Articles found: {len(articles)}",
            "COVERAGE: Approximately the last 24 hours",
            "",
        ]

        for number, article in enumerate(articles, start=1):
            published = article["published"].strftime(
                "%d %b %Y %H:%M UTC"
            )

            lines.extend([
                f"{number}. {article['title']}",
                f"Source: {article["source"]}"
                f"Published: {published}",
                f"Link: {article['link']}",
            ])

        body = "\n".join(lines)

    message.set_content(body)

    context = ssl.create_default_context()

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls(context=context)
        server.login(SENDER, APP_PASSWORD)
        server.send_message(message)

if __name__ == "__main__":
    print("Fetching news articles...")
    news = fetch_news()
    print(f"Found {len(news)} matching articles.")

    send_email(news)
    print(f"Digest sent to {RECIPIENT}.")