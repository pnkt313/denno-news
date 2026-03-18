import os
import feedparser
from flask import Flask, render_template, request
from newspaper import Article, Config
import nltk
from datetime import datetime

# --- NLTKデータの初期設定 ---
# Render等の環境で正しく動作させるための設定
nltk_data_path = os.path.join(os.getcwd(), "nltk_data")
if not os.path.exists(nltk_data_path):
    os.makedirs(nltk_data_path)
nltk.data.path.append(nltk_data_path)

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', download_dir=nltk_data_path)

app = Flask(__name__)

# --- RSSフィードの定義 ---
RSS_FEEDS = {
    'top': 'https://news.yahoo.co.jp/rss/topics/top-picks.xml',
    'japan': 'https://news.yahoo.co.jp/rss/topics/domestic.xml',
    'world': 'https://news.yahoo.co.jp/rss/topics/world.xml',
    'business': 'https://news.yahoo.co.jp/rss/topics/business.xml',
    'technology': 'https://news.yahoo.co.jp/rss/topics/it.xml',
    'entertainment': 'https://news.yahoo.co.jp/rss/topics/entertainment.xml',
    'sports': 'https://news.yahoo.co.jp/rss/topics/sports.xml',
    'science': 'https://news.yahoo.co.jp/rss/topics/science.xml',
}

def fetch_article_content(url):
    """URLから記事本文を抽出する（タイムアウト設定付き）"""
    config = Config()
    config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    config.request_timeout = 7  # スマホでのタイムアウト防止のため短めに設定
    
    try:
        article = Article(url, config=config)
        article.download()
        article.parse()
        # 本文の最初の300文字程度を抽出（HTMLタグを改行に置換）
        content = article.text[:350].replace('\n', '<br>')
        return content if content else "本文の取得に失敗しました。"
    except Exception as e:
        return f"記事の読み込み中にエラーが発生しました。"

@app.route('/')
def index():
    # カテゴリの取得（デフォルトは 'top'）
    cat = request.args.get('cat', 'top')
    feed_url = RSS_FEEDS.get(cat, RSS_FEEDS['top'])
    
    # RSSフィードを解析
    feed = feedparser.parse(feed_url)
    # スマホでの読み込み速度を優先し、最新の6件に絞る
    raw_entries = feed.entries[:6]
    
    entries = []
    weeks = ['月', '火', '水', '木', '金', '土', '日']
    
    for entry in raw_entries:
        # --- 日付の日本語変換処理 ---
        published_label = entry.get('published', '')
        try:
            # RSSの標準形式 (RFC 822) 'Thu, 19 Mar 2026 02:13:00 GMT' 等を解析
            dt = datetime.strptime(published_label, '%a, %d %b %Y %H:%M:%S %Z')
            # 日本語形式 '2026年03月19日（木）' に変換
            wd = dt.weekday()
            published_label = dt.strftime(f'%Y年%m月%d日（{weeks[wd]}）')
        except:
            # 変換に失敗した場合は元の文字列を使用
            pass

        # データの格納
        entries.append({
            'title': entry.title,
            'link': entry.link,
            'published': published_label,
            'content': fetch_article_content(entry.link)
        })

    return render_template('index.html', entries=entries, current_cat=cat)

if __name__ == '__main__':
    # ローカル実行用
    app.run(debug=True, port=5000)
