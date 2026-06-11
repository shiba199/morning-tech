# -*- coding: utf-8 -*-
"""
朝刊テック - ステップ2: SQLite 保存モジュール

取得した記事を SQLite に保存する。
リンクURL(link)をユニークキーにして、同じ記事は二重登録しない。

使い方:
    import db
    db.init_db()
    new_count, skipped = db.save_articles(articles)

articles は fetch_feeds.fetch_feed() が返す辞書のリスト:
    {"source": str, "title": str, "link": str, "published": datetime | None}
"""

import datetime
import os
import sqlite3

# DB ファイルはこのスクリプトと同じフォルダに置く
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "articles.db")


def get_connection():
    """DB接続を返す（呼び出し側で close すること）。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """テーブルが無ければ作成する。link に UNIQUE 制約をかけて重複を防ぐ。"""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                source     TEXT    NOT NULL,
                title      TEXT    NOT NULL,
                link       TEXT    NOT NULL UNIQUE,   -- ここを一意キーにして二重登録を防ぐ
                published  TEXT,                       -- ISO形式の文字列 or NULL
                fetched_at TEXT    NOT NULL,           -- このレコードを保存した日時(ISO)
                topics     TEXT,                       -- ステップ3: 分類したトピックID（カンマ区切り）or NULL
                summary    TEXT                        -- ステップ5: RSSの概要文（抽出型まとめの素材）or NULL
            )
            """
        )
        conn.commit()
        _ensure_columns(conn)  # 既存DBに後から増えた列を追加する
    finally:
        conn.close()


def _ensure_columns(conn):
    """既存の articles テーブルに、後から追加された列が無ければ補う（マイグレーション）。

    CREATE TABLE IF NOT EXISTS は既存テーブルに列を足さないため、
    PRAGMA で列の有無を確認し、足りない列を ALTER TABLE で追加する。
        topics  … ステップ3で追加
        summary … ステップ5で追加
    """
    cols = [row["name"] for row in conn.execute("PRAGMA table_info(articles)")]
    for name in ("topics", "summary"):
        if name not in cols:
            conn.execute(f"ALTER TABLE articles ADD COLUMN {name} TEXT")
    conn.commit()


def save_articles(articles):
    """
    記事リストを保存する。link が既に存在する記事はスキップする。

    戻り値: (new_count, skipped_count)
        new_count     … 新しく登録した件数
        skipped_count … 既に登録済みでスキップした件数
    """
    conn = get_connection()
    new_count = 0
    skipped_count = 0
    now_iso = datetime.datetime.now().isoformat(timespec="seconds")

    try:
        for a in articles:
            link = a.get("link", "")
            if not link:
                # link が無い記事は一意に扱えないのでスキップ
                skipped_count += 1
                continue

            published = a.get("published")
            published_iso = published.isoformat() if published else None
            summary = a.get("summary") or None

            # INSERT OR IGNORE: link が UNIQUE 制約に当たれば無視される
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO articles (source, title, link, published, fetched_at, summary)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (a.get("source", ""), a.get("title", ""), link, published_iso, now_iso, summary),
            )
            # rowcount が 1 なら新規挿入、0 なら既存でスキップ
            if cur.rowcount == 1:
                new_count += 1
            else:
                skipped_count += 1
                # 既存記事でも summary が未保存なら後追いで埋める（バックフィル）。
                # ステップ5で summary 列を追加したため、それ以前に保存済みの記事を救済する。
                if summary:
                    conn.execute(
                        "UPDATE articles SET summary = ? WHERE link = ? AND (summary IS NULL OR summary = '')",
                        (summary, link),
                    )

        conn.commit()
    finally:
        conn.close()

    return new_count, skipped_count


def set_article_topics(link, topic_ids):
    """1記事(link で指定)の topics 列を更新する。

    topic_ids … ["ai", "dev"] のようなトピックIDのリスト。
                 DBにはカンマ区切りの文字列（例 "ai,dev"）で保存する。
                 空リストなら空文字を保存する（＝分類済みだが該当なし、を表す）。
    戻り値: 更新した行数（通常 1、該当 link が無ければ 0）。
    """
    conn = get_connection()
    try:
        topics_str = ",".join(topic_ids)
        cur = conn.execute(
            "UPDATE articles SET topics = ? WHERE link = ?",
            (topics_str, link),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def get_articles_for_classification(only_unclassified=True):
    """分類対象の記事を返す。

    only_unclassified=True … topics が未設定(NULL)の記事だけ（＝まだ分類していない記事）。
    only_unclassified=False … 全記事（再分類したいとき）。
    """
    conn = get_connection()
    try:
        sql = "SELECT id, source, title, link, published, topics FROM articles"
        if only_unclassified:
            sql += " WHERE topics IS NULL"
        sql += " ORDER BY (published IS NULL), published DESC, id DESC"
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_articles():
    """保存済みの総件数を返す。"""
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM articles").fetchone()
        return row["c"]
    finally:
        conn.close()


def get_recent_articles(limit=20):
    """保存済み記事を新しい順（published優先、無ければ取得順）に取得する。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT source, title, link, published, fetched_at, topics, summary
            FROM articles
            ORDER BY (published IS NULL), published DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_articles_since(cutoff_iso):
    """published が cutoff_iso 以降の記事を新しい順に返す（まとめ生成用）。

    cutoff_iso … ISO形式の日時文字列（例 "2026-06-10T07:00:00"）。
    published が同じISO形式で保存されているため、文字列比較で期間を絞れる。
    published が NULL（日付不明）の記事は対象外にする。
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT source, title, link, published, fetched_at, topics, summary
            FROM articles
            WHERE published IS NOT NULL AND published >= ?
            ORDER BY published DESC, id DESC
            """,
            (cutoff_iso,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
