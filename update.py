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
import schedule_gate # 配信時刻の判定（アプリで選んだ時刻に通知する）
import summarize
import translate     # 英語記事の日本語翻訳（無料・キー不要）

# Windowsコンソール(cp932)対策
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = os.path.join(app.WEB_DIR, "data")


def step_fetch_and_save():
    """ステップ1+2: 全フィードを取得してDBへ保存する。"""
    all_articles = []
    for feed in fetch_feeds.get_active_feeds():
        all_articles.extend(fetch_feeds.fetch_feed(feed))
    new_count, skipped = db.save_articles(all_articles)
    print(f"[取得] {len(all_articles)} 件取得 / 新規 {new_count} 件 ・ 既存 {skipped} 件")
    return new_count


def step_translate():
    """英語記事のタイトル・概要を日本語に翻訳してDBへ書き戻す。

    まだ翻訳処理していない記事だけを対象にする（translated が NULL）。英語のものは
    翻訳し、日本語のものはそのまま。いずれも処理済みにして、同じ記事を毎回翻訳しにいかない。
    """
    targets = db.get_untranslated()
    translated_count = 0
    for a in targets:
        title = a.get("title") or ""
        summary = a.get("summary") or ""
        if title and not translate.has_japanese(title):
            # タイトルが英語の記事だけ翻訳（概要も英語なら翻訳）
            new_title = translate.translate(title)
            new_summary = translate.translate(summary) if (summary and not translate.has_japanese(summary)) else summary
            db.mark_translated(a["link"], new_title, new_summary)
            translated_count += 1
        else:
            # 日本語記事は処理済みフラグだけ立てる（翻訳しない）
            db.mark_translated(a["link"], title, summary)
    print(f"[翻訳] 対象 {len(targets)} 件中 英語 {translated_count} 件を日本語化")


def step_classify():
    """ステップ3: 未分類の記事をトピック分類してDBへ書き戻す。"""
    targets = db.get_articles_for_classification(only_unclassified=True)
    for a in targets:
        topic_ids = classify.classify_article(a["title"])
        db.set_article_topics(a["link"], topic_ids)
    print(f"[分類] 新たに {len(targets)} 件を分類")
    return len(targets)


def step_write_snapshots(digest):
    """フロント用の静的JSONを web/data に書き出す（app.py と同じ形状）。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    snapshots = {
        "articles.json": {"articles": app.get_articles_payload()},
        "topics.json":   {"topics": app.get_topics_payload()},
        "sources.json":  {"sources": app.get_sources_payload()},
        "digest.json":   digest,
    }
    for name, obj in snapshots.items():
        path = os.path.join(DATA_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"[出力] 静的スナップショットを書き出し: {', '.join(snapshots.keys())} → {DATA_DIR}")


def step_notify(digest, force=False):
    """配信時刻の判定にもとづいてDiscord通知を送る。

    アプリの設定画面で選んだ時刻（web/data/settings.json）を schedule_gate が読み、
    「設定時刻を過ぎていて、今日まだ送っていなければ送る」と判定する。
    force=True（手動実行）のときは判定を飛ばして必ず送る。
    """
    # 設定ファイルが無ければ既定値で作成しておく（初回・アプリ未設定時の保険）
    schedule_gate.load_settings()

    now = schedule_gate.now_jst()
    do_send, reason = schedule_gate.should_notify(force=force, now=now)
    print(f"[通知判定] {reason}")
    if not do_send:
        return

    result = notify.send_digest(digest)
    # 送信を実際に試みた日は「本日通知済み」として記録し、重複送信を防ぐ
    # （URL未設定で送れなかった場合は記録せず、登録後の次回実行で送れるようにする）
    if result in ("sent", "skipped-empty"):
        schedule_gate.mark_notified(now.date().isoformat())


def main():
    force = "--force" in sys.argv

    print("=" * 60)
    print(f"朝刊テック 自動更新を開始します{'（--force 手動実行）' if force else ''}")
    print("=" * 60)

    db.init_db()
    step_fetch_and_save()
    step_translate()   # 分類より前に翻訳（日本語タイトルで分類できるように）
    step_classify()
    digest = summarize.build_digest(hours=24)
    step_write_snapshots(digest)
    step_notify(digest, force=force)

    total = db.count_articles()
    print(f"\n完了。DB総件数: {total} 件")


if __name__ == "__main__":
    main()
