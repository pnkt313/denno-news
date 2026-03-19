import os
from flask import Flask, render_template, request
import feedparser
from newspaper import Article, Config
import concurrent.futures
import re
import nltk

# --- NLTKデータの保存先を明示 ---
nltk_data_path = os.path.join(os.getcwd(), "nltk_data")
if not os.path.exists(nltk_data_path):
    os.makedirs(nltk_data_path)
nltk.data.path.append(nltk_data_path)

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', download_dir=nltk_data_path)

app = Flask(__name__)

CATEGORIES = {
    'top': 'https://news.google.com/news/rss?hl=ja&gl=JP&ceid=JP:ja',
    'japan': 'https://news.google.com/news/rss/headlines/section/topic/NATION?hl=ja&gl=JP&ceid=JP:ja',
    'world': 'https://news.google.com/news/rss/headlines/section/topic/WORLD?hl=ja&gl=JP&ceid=JP:ja',
    'business': 'https://news.google.com/news/rss/headlines/section/topic/BUSINESS?hl=ja&gl=JP&ceid=JP:ja',
    'technology': 'https://news.google.com/news/rss/headlines/section/topic/TECHNOLOGY?hl=ja&gl=JP&ceid=JP:ja',
    'entertainment': 'https://news.google.com/news/rss/headlines/section/topic/ENTERTAINMENT?hl=ja&gl=JP&ceid=JP:ja',
    'sports': 'https://news.google.com/news/rss/headlines/section/topic/SPORTS?hl=ja&gl=JP&ceid=JP:ja',
    'science': 'https://news.google.com/news/rss/headlines/section/topic/SCIENCE?hl=ja&gl=JP&ceid=JP:ja'
}

def remove_html_tags(text):
    if not text: return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def fetch_article_content(entry):
    config = Config()
    # ブラウザからのアクセスに見せかける設定を強化
    config.browser_user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    config.request_timeout = 10 # タイムアウトを少し伸ばす

    try:
        article = Article(entry.link, config=config)
        article.download()
        article.parse()
        
        # 本文の抽出（400文字）
        content = article.text[:400].replace('\n', '<br>')
        
        # --- 画像取得ロジックの強化 ---
        # 1. まず代表画像を探す
        top_image_url = article.top_image
        
        # 2. 代表画像がない場合、記事内の画像リストから最初の一つを探す
        if not top_image_url and article.images:
            for img in article.images:
                # 広告やアイコンっぽい小さい画像を除外（簡易判定）
                if "icon" not in img.lower() and "logo" not in img.lower():
                    top_image_url = img
                    break
        
        # ゴミ取り
        if content.startswith('GE'):
            content = content.replace('GE', '', 1).lstrip()

        if not content or len(content) < 30:
            content = remove_html_tags(getattr(entry, 'summary', ''))
        
        return {
            'title': entry.title, 
            'link': entry.link, 
            'published': getattr(entry, 'published', ''), 
            'content': content,
            'top_image_url': top_image_url
        }
    except Exception as e:
        print(f"Error fetching {entry.link}: {e}") # ログでエラーを確認できるように
        return {
            'title': entry.title, 
            'link': entry.link, 
            'published': getattr(entry, 'published', ''), 
            'content': remove_html_tags(getattr(entry, 'summary', '')),
            'top_image_url': None
        }

@app.route('/')
def index():
    cat_key = request.args.get('cat', 'top')
    rss_url = CATEGORIES.get(cat_key, CATEGORIES['top'])
    
    feed = feedparser.parse(rss_url)
    raw_entries = feed.entries[:6]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        entries = list(executor.map(fetch_article_content, raw_entries))
        
    return render_template('index.html', entries=entries, current_cat=cat_key)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
