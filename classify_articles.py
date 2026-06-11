# -*- coding: utf-8 -*-
"""
朝刊テック - ステップ3: 保存済み記事をトピック分類して結果を表示・保存するスクリプト

DB(articles.db)の記事を classify.py（キーワードマッチ）で分類し、
判定したトピックを DB の topics 列に書き戻したうえで、
トピックごとにまとめてコンソールに一覧表示する。

実行: .venv/Scripts/python.exe classify_articles.py
      （全記事を再分類したいときは: classify_articles.py --all）

前提: 先に fetch_feeds.py を実行して記事が保存されていること。
"""

import sys

import classify
import db

# Windowsコンソール(cp932)対策: 標準出力をUTF-8に固定
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    # --all を付けると未分類だけでなく全記事を分類し直す
    reclassify_all = "--all" in sys.argv

    db.init_db()  # topics 列のマイグレーションもここで実行される

    articles = db.get_articles_for_classification(only_unclassified=not reclassify_all)
    mode = "全記事(再分類)" if reclassify_all else "未分類の記事"
    print(f"分類対象: {mode} … {len(articles)} 件")

    if not articles:
        print("分類する記事がありません（先に fetch_feeds.py を実行してください）。")
        # 既に分類済みの記事があれば、現状を表示する
        show_summary_from_db()
        return

    # --- 1件ずつ分類して DB に書き戻す ---
    classified = 0
    for a in articles:
        topic_ids = classify.classify_article(a["title"])
        db.set_article_topics(a["link"], topic_ids)
        classified += 1

    print(f"分類して保存しました: {classified} 件\n")

    show_summary_from_db()


def show_summary_from_db():
    """DBの全記事を読み、トピック別に集計して一覧表示する。"""
    articles = db.get_recent_articles(limit=100)
    if not articles:
        return

    # トピックID -> 記事リスト（1記事が複数トピックに入ることがある）
    by_topic = {t["id"]: [] for t in classify.TOPICS}
    no_topic = []

    for a in articles:
        topics_str = a.get("topics")
        ids = topics_str.split(",") if topics_str else []
        ids = [i for i in ids if i]  # 空文字を除去
        if ids:
            for tid in ids:
                by_topic.setdefault(tid, []).append(a)
        else:
            no_topic.append(a)

    print("=" * 70)
    print("トピック別 記事一覧")
    print("=" * 70)

    for topic in classify.TOPICS:
        items = by_topic.get(topic["id"], [])
        print(f"\n■ {topic['label']}  （{len(items)} 件）")
        if not items:
            print("    （該当なし）")
            continue
        for a in items:
            labels = classify.topics_to_labels(
                [i for i in (a.get("topics") or "").split(",") if i]
            )
            print(f"    - {a['title']}")
            print(f"        {a['source']} ／ タグ: {' '.join(labels)}")

    if no_topic:
        print(f"\n□ 未分類（どのトピックにも該当せず）  （{len(no_topic)} 件）")
        for a in no_topic:
            print(f"    - {a['title']}  （{a['source']}）")

    print("\n" + "=" * 70)
    print(f"合計記事数: {len(articles)} 件")


if __name__ == "__main__":
    main()
