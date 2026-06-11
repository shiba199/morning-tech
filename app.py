# -*- coding: utf-8 -*-
"""
朝刊テック - ステップ4: Webアプリ（バックエンド）

morning_tech_briefing.html のデザインを土台にした Webアプリを、
SQLite(articles.db)の実データで動かすための簡易サーバー。

■ 方針（完全無料・追加インストール不要）
  Python標準ライブラリ http.server だけで実装する（FastAPI/uvicorn等を入れない）。
  ブラウザの JavaScript から RSS を直叩きすると CORS で失敗するため、
  RSS取得・分類はバックエンド側で済ませ、フロントは自分のAPIだけを叩く（仕様書セクション4）。

■ 提供するもの
  GET  /                … Webアプリ本体（web/index.html）
  GET  /api/articles    … DBの記事一覧（トピック分類済み）をJSONで返す
  GET  /api/topics      … 興味トピックの一覧（チップ・設定用）をJSONで返す
  GET  /api/sources     … ニュース取得元の一覧（設定用）をJSONで返す
  GET  /api/digest      … 「今朝のまとめ」（過去24時間・抽出型）をJSONで返す

実行: .venv/Scripts/python.exe app.py
      → ブラウザで http://localhost:8000 を開く

前提: 先に fetch_feeds.py（取得＋保存）と classify_articles.py（分類）を実行しておくこと。
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import classify
import db
import fetch_feeds  # 取得元一覧 FEEDS を使う
import summarize    # ステップ5: 「今朝のまとめ」生成

# Windowsコンソール(cp932)対策
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "127.0.0.1"
PORT = 8000

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")


def source_meta(source):
    """取得元名から、カードのバッジ用の (種別クラス, 短い表示名) を返す。

    種別クラスは HTML の .src.aws / .src.dev / .src.news の色分けに対応する。
    """
    if "AWS" in source:
        return ("aws", "AWS Blog")
    if "DevelopersIO" in source:
        return ("dev", "DevelopersIO")
    if "Publickey" in source:
        return ("news", "Publickey")
    return ("news", source)


def article_to_payload(a):
    """DBの記事1件を、フロントが描画しやすい形のdictに変換する。"""
    topics_str = a.get("topics") or ""
    topic_ids = [t for t in topics_str.split(",") if t]
    labels = classify.topics_to_labels(topic_ids)
    src_class, src_label = source_meta(a.get("source", ""))

    return {
        "source": a.get("source", ""),
        "srcClass": src_class,
        "srcLabel": src_label,
        "title": a.get("title", ""),
        "link": a.get("link", ""),
        "published": a.get("published"),  # ISO文字列 or None
        "topics": topic_ids,              # ["ai", "dev"]
        "tags": list(zip(topic_ids, labels)),  # [["ai","生成AI"], ...]（フロントでタグ表示）
        "why": labels[0] if labels else "",     # 「なぜ表示したか」= 先頭トピック
    }


def get_articles_payload(limit=100):
    return [article_to_payload(a) for a in db.get_recent_articles(limit=limit)]


def get_topics_payload():
    """興味トピック一覧（id/label）。HTMLのチップ・設定で使う。"""
    return [{"id": t["id"], "label": t["label"]} for t in classify.TOPICS]


def get_sources_payload():
    """ニュース取得元一覧。設定画面で使う（オンオフは将来対応）。"""
    return [{"name": f["name"], "url": f["url"]} for f in fetch_feeds.FEEDS]


class Handler(BaseHTTPRequestHandler):
    # アクセスログは簡潔に
    def log_message(self, fmt, *args):
        sys.stderr.write(f"  {self.address_string()} - {fmt % args}\n")

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except FileNotFoundError:
            self.send_error(404, "Not Found")
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # クエリ文字列は無視してパスだけ見る
        path = self.path.split("?", 1)[0]

        if path == "/" or path == "/index.html":
            self._send_file(os.path.join(WEB_DIR, "index.html"), "text/html; charset=utf-8")
        elif path == "/api/articles":
            self._send_json({"articles": get_articles_payload()})
        elif path == "/api/topics":
            self._send_json({"topics": get_topics_payload()})
        elif path == "/api/sources":
            self._send_json({"sources": get_sources_payload()})
        elif path == "/api/digest":
            self._send_json(summarize.build_digest(hours=24))
        else:
            # それ以外は web/ 配下の静的ファイルとして配信
            # （manifest.json / sw.js / icons/ / data/ など PWA・スナップショット用）
            self._serve_static(path)

    # 拡張子 → Content-Type の対応（PWAに必要な分）
    CONTENT_TYPES = {
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".webmanifest": "application/manifest+json; charset=utf-8",
    }

    def _serve_static(self, path):
        """web/ 配下のファイルを安全に配信する（ディレクトリ外への参照は拒否）。"""
        rel = path.lstrip("/")
        full = os.path.normpath(os.path.join(WEB_DIR, rel))
        # パストラバーサル対策: WEB_DIR の外に出るパスは拒否
        if not full.startswith(WEB_DIR):
            self.send_error(403, "Forbidden")
            return
        if not os.path.isfile(full):
            self.send_error(404, "Not Found")
            return
        ext = os.path.splitext(full)[1].lower()
        ctype = self.CONTENT_TYPES.get(ext, "application/octet-stream")
        self._send_file(full, ctype)


def main():
    db.init_db()
    total = db.count_articles()
    print("朝刊テック Webアプリを起動します。")
    print(f"  DB記事数: {total} 件")
    if total == 0:
        print("  ⚠ 記事が0件です。先に fetch_feeds.py と classify_articles.py を実行してください。")
    print(f"  URL: http://localhost:{PORT}  （停止: Ctrl+C）")

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
