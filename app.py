from flask import Flask, request, redirect, g, flash, render_template
import requests
import re
import sqlite3
from urllib.parse import quote, unquote

app = Flask(__name__)
app.secret_key = '1557'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('url.db')
        g.db.execute('CREATE TABLE IF NOT EXISTS url_mapping (short_url TEXT, original_url TEXT)')
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


@app.route('/', methods=['GET', 'POST'])
def home():
  if request.method == 'POST':
    db = get_db()
    c = db.cursor()
    original_url = request.form['url']
    match = re.search(r'https://chzzk.naver.com/live/(.*)', original_url)
    if match is None:
      flash('URL 형식이 잘못되었습니다.')
      return render_template('home.html')

    streamer_id = match.group(1)

    headers = {
      'Cookie': 'NID_AUT=; NID_SES=',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Whale/3.24.223.21 Safari/537.36',
    }
    try:
      response = requests.get(f"https://api.chzzk.naver.com/service/v1/channels/{streamer_id}/live-detail", headers=headers)
      response.raise_for_status()
    except requests.exceptions.RequestException as e:
      flash('API 응답이 없습니다.')
      return render_template('home.html')

    response_json = response.json()
    channel_name = quote(response_json['content']['channel']['channelName'], safe='')

    short_url = f"{channel_name}"

    c.execute('SELECT * FROM url_mapping WHERE original_url = ?', (original_url,))
    if c.fetchone() is not None:
      flash('이미 존재하는 URL입니다.')
      return render_template('home.html')

    c.execute('INSERT INTO url_mapping VALUES (?, ?)', (short_url, original_url))
    db.commit()

    flash(f'{unquote(channel_name)}에 대한 단축 URL이 성공적으로 생성되었습니다.')
    return render_template('home.html')

  return render_template('home.html')

@app.route('/<path:path>')
def redirect_url(path):
  db = get_db()
  c = db.cursor()
  c.execute('SELECT original_url FROM url_mapping WHERE short_url = ?', (quote(path, safe=''),))
  result = c.fetchone()
  if result is None:
    flash("URL을 찾을 수 없습니다.")
    return redirect('/')
  original_url = result[0]

  return redirect(original_url)

if __name__ == '__main__':
    app.run(debug=True)