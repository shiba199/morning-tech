# -*- coding: utf-8 -*-
"""
朝刊テック - ステップ5: 「今朝のまとめ」生成モジュール（抽出型・無料・全自動）

過去24時間の記事をトピックごとにまとめる。要約は **抽出型**：
RSSの概要文（summary）や本文の冒頭1〜2文を抜き出して並べるだけで、LLMは使わない
（追加費用0円・完全自動。仕様書セクション7の採用方針）。

■ 設計方針（差し替え可能に作る）
  要約の入口は summarize_topic(label, articles) の1関数。
  入力＝記事リスト / 出力＝要約テキスト、というインターフェイスを固定してある。
  将来この中身を Claude API 呼び出しに差し替えれば（B案/C案）、
  build_digest など呼び出し側を変えずに「練られた要約」へ移行できる。

公開関数:
  build_digest(hours=24) … DBから過去hours時間の記事を読み、まとめ構造(dict)を返す
"""

import datetime
import re

import classify
import db

# 1トピックに載せる記事の最大件数
MAX_PER_TOPIC = 4
# 抽出する概要文のおおよその最大文字数（長すぎる概要を切り詰める）
EXCERPT_MAX = 120


def clean_text(raw):
    """RSSの概要文からHTMLタグ・余分な空白を除いた素のテキストを返す。"""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)          # HTMLタグ除去
    text = re.sub(r"&[a-zA-Z#0-9]+;", " ", text)  # &nbsp; などの実体参照を空白に
    text = re.sub(r"\s+", " ", text).strip()      # 連続空白を1つに
    return text


def first_sentences(text, max_len=EXCERPT_MAX):
    """テキストの冒頭1〜2文を、max_len程度までで抜き出す。"""
    if not text:
        return ""
    # 日本語の句点 / 英語のピリオドで文を区切る
    parts = re.split(r"(?<=[。．.!?！？])\s*", text)
    out = ""
    for p in parts:
        if not p:
            continue
        if out and len(out) + len(p) > max_len:
            break
        out += p
        if len(out) >= max_len:
            break
    out = out[:max_len].strip()
    # 元が長くて途中で切れた場合は省略記号を付ける
    if out and len(text) > len(out):
        out += "…"
    return out


def make_excerpt(article):
    """記事1件の抜粋テキストを作る。概要文が無ければタイトルで代用する。"""
    summary = clean_text(article.get("summary"))
    if summary:
        return first_sentences(summary)
    # 概要が無い記事（旧データなど）はタイトルを抜粋の代わりにする
    return article.get("title", "")


def summarize_topic(label, articles):
    """【差し替えポイント】1トピック分の要約テキストを返す。

    現状は抽出型：このトピックで最も新しい記事の抜粋を、トピックの要約文として使う。
    将来ここを Claude API に差し替えれば、複数記事をまとめた自然な要約文にできる。

    入力 : label … トピック名 / articles … そのトピックの記事リスト（新しい順）
    出力 : 要約テキスト（1〜2文程度）
    """
    if not articles:
        return ""
    lead = make_excerpt(articles[0])
    return f"{label}の新着が{len(articles)}件。{lead}"


def build_digest(hours=24, now=None):
    """過去hours時間の記事から「今朝のまとめ」構造を組み立てて返す。

    戻り値(dict):
      {
        "generated_at": ISO日時,
        "window_hours": 24,
        "total": 対象記事数,
        "topic_count": 記事が入ったトピック数,
        "groups": [
          {"id","label","summary","articles":[{title,link,source,excerpt,published}, ...]},
          ...
        ],
        "uncategorized": [ ... 同上 ... ]   # どのトピックにも入らなかった記事
      }
    """
    now = now or datetime.datetime.now()
    cutoff = now - datetime.timedelta(hours=hours)
    cutoff_iso = cutoff.isoformat(timespec="seconds")

    rows = db.get_articles_since(cutoff_iso)

    # トピックID -> 記事リスト（1記事が複数トピックに入ってよい）
    buckets = {t["id"]: [] for t in classify.TOPICS}
    uncategorized = []
    for r in rows:
        ids = [i for i in (r.get("topics") or "").split(",") if i]
        if ids:
            for tid in ids:
                buckets.setdefault(tid, []).append(r)
        else:
            uncategorized.append(r)

    def to_item(r):
        return {
            "title": r.get("title", ""),
            "link": r.get("link", ""),
            "source": r.get("source", ""),
            "published": r.get("published"),
            "excerpt": make_excerpt(r),
        }

    groups = []
    for topic in classify.TOPICS:
        items = buckets.get(topic["id"], [])
        if not items:
            continue  # 記事ゼロのトピックはまとめに出さない
        limited = items[:MAX_PER_TOPIC]
        groups.append({
            "id": topic["id"],
            "label": topic["label"],
            "summary": summarize_topic(topic["label"], items),
            "articles": [to_item(r) for r in limited],
        })

    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "window_hours": hours,
        "total": len(rows),
        "topic_count": len(groups),
        "groups": groups,
        "uncategorized": [to_item(r) for r in uncategorized[:MAX_PER_TOPIC]],
    }


# 単体動作確認用
if __name__ == "__main__":
    import json
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    db.init_db()
    digest = build_digest(hours=24)
    print(json.dumps(digest, ensure_ascii=False, indent=2))
