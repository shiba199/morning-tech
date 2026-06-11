# -*- coding: utf-8 -*-
"""
朝刊テック - ステップ1+2: RSS取得 + SQLite保存スクリプト

日本語フィード3つ（AWS日本語ブログ・DevelopersIO・Publickey）から
最新記事のタイトル・リンク・日付・取得元を取得し、コンソールに一覧表示する。

ステップ2: 取得した記事を SQLite(articles.db) に保存する。
           link を一意キーにして、同じ記事は二重登録しない。
           2回目以降の実行では、新規記事だけが追加される。

実行: .venv/Scripts/python.exe fetch_feeds.py
"""

import datetime
import sys

import feedparser

import db  # ステップ2: SQLite保存モジュール

# Windowsコンソール(cp932)対策: 標準出力をUTF-8に固定する
# これがないと日本語や「–」などで UnicodeEncodeError になる
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# --- 取得元（仕様書セクション5の日本語フィード3つ） ---
# 取得元はコードに一覧データとして管理する（あとで設定画面でオンオフできるようにする）
FEEDS = [
    {"name": "AWS 公式ブログ（日本語）", "url": "https://aws.amazon.com/jp/blogs/news/feed/"},
    {"name": "DevelopersIO",            "url": "https://dev.classmethod.jp/feed/"},
    {"name": "Publickey",               "url": "https://www.publickey1.jp/atom.xml"},
]

# 1フィードあたり表示する最大件数
MAX_PER_FEED = 5


def parse_published(entry):
    """記事の公開日時を datetime で返す（取れなければ None）。"""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            # time.struct_time -> datetime
            return datetime.datetime(*t[:6])
    return None


def format_date(dt):
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "日付不明"


def fetch_feed(feed):
    """1つのフィードを取得して記事リストを返す。"""
    print(f"\n取得中: {feed['name']}  ({feed['url']})")
    parsed = feedparser.parse(feed["url"])

    # 取得失敗やフォーマット不正の検知
    if parsed.bozo:
        print(f"  ⚠ 警告: フィードの解析で問題が発生しました ({parsed.bozo_exception})")
    if not parsed.entries:
        print("  ⚠ 記事が0件でした（URLや配信状況を確認してください）")
        return []

    articles = []
    for entry in parsed.entries[:MAX_PER_FEED]:
        articles.append({
            "source":    feed["name"],
            "title":     entry.get("title", "（タイトルなし）"),
            "link":      entry.get("link", ""),
            "published": parse_published(entry),
            # ステップ5「今朝のまとめ（抽出型）」の素材になるRSS概要文。
            # HTMLタグが混じることがあるため、整形は summarize.py 側で行う（ここでは生のまま保存）。
            "summary":   entry.get("summary", "") or entry.get("description", ""),
        })
    print(f"  → {len(articles)} 件取得")
    return articles


def main():
    all_articles = []
    for feed in FEEDS:
        all_articles.extend(fetch_feed(feed))

    # 新しい順に並べ替え（日付不明は末尾）
    all_articles.sort(
        key=lambda a: a["published"] or datetime.datetime.min,
        reverse=True,
    )

    # --- 一覧表示 ---
    print("\n" + "=" * 70)
    print(f"取得記事 一覧（合計 {len(all_articles)} 件 / 新しい順）")
    print("=" * 70)
    for i, a in enumerate(all_articles, 1):
        print(f"\n[{i:>2}] {a['title']}")
        print(f"     取得元 : {a['source']}")
        print(f"     日付   : {format_date(a['published'])}")
        print(f"     リンク : {a['link']}")

    # --- ステップ2: SQLite へ保存（link が重複する記事はスキップ） ---
    db.init_db()
    new_count, skipped = db.save_articles(all_articles)
    total_in_db = db.count_articles()

    print("\n" + "=" * 70)
    print(f"取得: {len(all_articles)} 件")
    print(f"DB保存: 新規 {new_count} 件 / スキップ(登録済み) {skipped} 件")
    print(f"DB総件数: {total_in_db} 件  （ファイル: {db.DB_PATH}）")


if __name__ == "__main__":
    main()
