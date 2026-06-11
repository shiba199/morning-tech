# -*- coding: utf-8 -*-
"""
朝刊テック - ステップ6: 毎朝の自動更新パイプライン（1コマンド）

定期実行（GitHub Actions の cron / タスクスケジューラ）から呼ばれる入口。
次を順番に実行する:
  1. RSS取得 → SQLite保存（重複は登録しない）          … fetch_feeds + db
  2. 未分類記事のトピック分類（キーワードマッチ）         … classify
  3. フロント用の静的スナップショット(JSON)を web/data に書き出す

なぜスナップショットを書き出すか:
  GitHub Actions のランナーは毎回まっさらで、常駐サーバー(app.py)は動かせない。
  そこで「取得・分類した結果」を JSON ファイルとして書き出し、
  リポジトリにコミットして保存する。これにより:
    - 次回以降も articles.db / JSON が残る（履歴として積み上がる）
    - 静的ホスティング(GitHub Pages)だけで閲覧できる土台になる（ステップ8 PWA への布石）
  app.py（ローカルのAPIサーバー）と同じデータ形状で出力するので、フロントは共通で扱える。

実行: .venv/Scripts/python.exe update.py
"""

import json
import os
import sys

import app          # JSONの生成ロジックを再利用（データ形状を一元化）
import classify
import db
import fetch_feeds
import notify        # ステップ7: Discord通知
import summarize

# Windowsコンソール(cp932)対策
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = os.path.join(app.WEB_DIR, "data")


def step_fetch_and_save():
    """ステップ1+2: 全フィードを取得してDBへ保存する。"""
    all_articles = []
    for feed in fetch_feeds.FEEDS:
        all_articles.extend(fetch_feeds.fetch_feed(feed))
    new_count, skipped = db.save_articles(all_articles)
    print(f"[取得] {len(all_articles)} 件取得 / 新規 {new_count} 件 ・ 既存 {skipped} 件")
    return new_count


def step_classify():
    """ステップ3: 未分類の記事をトピック分類してDBへ書き戻す。"""
    targets = db.get_articles_for_classification(only_unclassified=True)
    for a in targets:
        topic_ids = classify.classify_article(a["title"])
        db.set_article_topics(a["link"], topic_ids)
    print(f"[分類] 新たに {len(targets)} 件を分類")
    return len(targets)


def step_write_snapshots():
    """フロント用の静的JSONを web/data に書き出す（app.py と同じ形状）。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    snapshots = {
        "articles.json": {"articles": app.get_articles_payload()},
        "topics.json":   {"topics": app.get_topics_payload()},
        "sources.json":  {"sources": app.get_sources_payload()},
        "digest.json":   summarize.build_digest(hours=24),
    }
    for name, obj in snapshots.items():
        path = os.path.join(DATA_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"[出力] 静的スナップショットを書き出し: {', '.join(snapshots.keys())} → {DATA_DIR}")


def main():
    print("=" * 60)
    print("朝刊テック 自動更新を開始します")
    print("=" * 60)

    db.init_db()
    step_fetch_and_save()
    step_classify()
    step_write_snapshots()

    # ステップ7: 「今朝のまとめ」をDiscordに通知（DISCORD_WEBHOOK_URL 未設定ならスキップ）
    digest = summarize.build_digest(hours=24)
    notify.send_digest(digest)

    total = db.count_articles()
    print(f"\n完了。DB総件数: {total} 件")


if __name__ == "__main__":
    main()
