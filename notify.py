# -*- coding: utf-8 -*-
"""
朝刊テック - ステップ7: 通知（Discord webhook）

「今朝のまとめ」をDiscordのwebhookに投稿する。スマホのDiscordアプリが
OSのプッシュ通知を出すので、体感は「普通のアプリ通知」になる。

■ 方針（無料・追加依存なし）
  送信は Python標準ライブラリ urllib だけで行う（requests等を入れない）。
  webhook URL は環境変数 DISCORD_WEBHOOK_URL から読む。
  GitHub Actions では「リポジトリの Secrets」に入れた値が環境変数として渡る。
  未設定なら送信せずスキップする（ローカルのテスト実行で誤爆しないため）。

■ 差し替え可能に作る
  通知の入口は send_digest(digest) の1関数。中身を Web Push（ステップ8）や
  メールに差し替えても、呼び出し側（update.py）は変えなくてよい。

単体実行:
  通常        : python notify.py          … DBからまとめを作って送信（URL未設定ならスキップ）
  内容だけ確認: python notify.py --dry-run … 送らずに、送る予定の本文を表示
"""

import datetime
import json
import os
import sys
import urllib.request

import summarize

# Windowsコンソール(cp932)対策
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WEBHOOK_ENV = "DISCORD_WEBHOOK_URL"
EMBED_COLOR = 0xFF6A3D  # 朝焼けオレンジ（HTMLの --sun1 と揃える）

# Discordの制限に対する安全側の上限
MAX_FIELDS = 10          # 1メッセージのフィールド数（トピック数ぶん。実際は最大5）
MAX_FIELD_VALUE = 1000   # フィールド本文の文字数（公式上限1024より安全側）
MAX_LINKS_PER_TOPIC = 4  # 1トピックに載せるリンク数


def build_payload(digest):
    """まとめ構造(dict) から Discord webhook 用のJSONペイロードを組み立てる。"""
    gen = digest.get("generated_at")
    try:
        day = datetime.datetime.fromisoformat(gen).strftime("%Y-%m-%d") if gen else ""
    except ValueError:
        day = ""

    total = digest.get("total", 0)
    topic_count = digest.get("topic_count", 0)
    groups = digest.get("groups", [])

    fields = []
    for g in groups[:MAX_FIELDS]:
        lines = []
        for a in g.get("articles", [])[:MAX_LINKS_PER_TOPIC]:
            title = (a.get("title") or "").replace("\n", " ").strip()
            link = a.get("link") or ""
            line = f"• [{title}]({link})" if link else f"• {title}"
            # フィールド本文の上限を超えないよう積み上げる
            if sum(len(x) + 1 for x in lines) + len(line) > MAX_FIELD_VALUE:
                break
            lines.append(line)
        fields.append({
            "name": f"{g.get('label','')}（{len(g.get('articles', []))}件）",
            "value": "\n".join(lines) if lines else "（記事なし）",
            "inline": False,
        })

    description = (
        f"過去24時間の IT・AWS ニュース **{total}** 件を、"
        f"**{topic_count}** トピックに整理しました。"
    )

    return {
        "username": "朝刊テック",
        "embeds": [{
            "title": f"🌅 今朝のまとめ — {day}".strip(" —"),
            "description": description,
            "color": EMBED_COLOR,
            "fields": fields,
            "footer": {"text": "朝刊テック / 抽出型まとめ（無料・自動生成）"},
        }],
    }


def _post(url, payload):
    """webhookへJSONをPOSTする。成功(2xx)で True。"""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return 200 <= resp.status < 300


def send_digest(digest, dry_run=False):
    """【通知の入口】まとめをDiscordに送る。

    戻り値: "sent" / "skipped-empty" / "skipped-no-url" / "dry-run" / "error"
    """
    # 新着が無い朝は通知しない（ノイズ回避）
    if not digest.get("groups"):
        print("通知スキップ: 過去24時間の新着がありません。")
        return "skipped-empty"

    payload = build_payload(digest)

    if dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return "dry-run"

    url = os.environ.get(WEBHOOK_ENV, "").strip()
    if not url:
        print(f"通知スキップ: 環境変数 {WEBHOOK_ENV} が未設定です（ローカルでは正常）。")
        return "skipped-no-url"

    try:
        ok = _post(url, payload)
        if ok:
            print("通知を送信しました（Discord）。")
            return "sent"
        print("通知の送信に失敗しました（webhookの応答が異常）。")
        return "error"
    except Exception as e:  # noqa: BLE001  ネットワーク等の失敗で更新全体を止めない
        print(f"通知の送信に失敗しました: {e}")
        return "error"


def main():
    dry_run = "--dry-run" in sys.argv
    import db
    db.init_db()
    digest = summarize.build_digest(hours=24)
    send_digest(digest, dry_run=dry_run)


if __name__ == "__main__":
    main()
