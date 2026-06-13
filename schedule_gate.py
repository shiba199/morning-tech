# -*- coding: utf-8 -*-
"""
朝刊テック - 通知スケジュール判定（アプリから時刻を変えられるようにするための土台）

アプリの設定画面で選んだ「配信したい時刻」は web/data/settings.json に保存される
（アプリが GitHub API 経由で直接書き込む）。自動実行はこのファイルを読み、
「いま通知すべきか」を判定する。

仕組み:
  - GitHub Actions の cron は30分おきに動く（時刻ぴったりを保証できないため）。
  - 各実行で「設定時刻を過ぎていて、まだ今日通知していなければ送る」＝1日1回・設定時刻以降の
    最初の実行で通知（キャッチアップ方式。GitHubの遅延に強い）。
  - 「今日もう送ったか」は web/data/notify_state.json に記録して重複送信を防ぐ。

時刻はすべて日本時間(JST=UTC+9)で扱う。GitHubランナーはUTCのため +9時間して判定する。
"""

import datetime
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "data")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
STATE_PATH = os.path.join(DATA_DIR, "notify_state.json")

# 設定ファイルが無いときの既定値
DEFAULT_SETTINGS = {"send_time": "06:47", "enabled": True}

# 日本標準時（夏時間なし＝常に UTC+9）
JST = datetime.timezone(datetime.timedelta(hours=9))


def now_jst():
    """現在時刻を日本時間で返す。"""
    return datetime.datetime.now(datetime.timezone.utc).astimezone(JST)


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_settings():
    """設定（配信時刻・有効フラグ）を読む。無ければ既定値で作成する。"""
    data = _read_json(SETTINGS_PATH)
    if not isinstance(data, dict):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, ensure_ascii=False, indent=2)
        return dict(DEFAULT_SETTINGS)
    # 欠けたキーは既定値で補う
    merged = dict(DEFAULT_SETTINGS)
    merged.update(data)
    return merged


def _parse_hhmm(text):
    """"HH:MM" を (時, 分) に。不正なら既定の 6:47。"""
    try:
        h, m = str(text).split(":")
        h, m = int(h), int(m)
        if 0 <= h < 24 and 0 <= m < 60:
            return h, m
    except (ValueError, AttributeError):
        pass
    return 6, 47


def mark_notified(date_iso):
    """今日通知済みを記録する。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"last_notified_date": date_iso}, f, ensure_ascii=False, indent=2)


def should_notify(force=False, now=None):
    """いま通知すべきかを判定する。

    戻り値: (送るべきか: bool, 理由メッセージ: str)
    force=True（手動実行）のときは時刻・重複チェックを飛ばして必ず送る。
    """
    now = now or now_jst()
    today_iso = now.date().isoformat()

    if force:
        return True, "手動実行（--force）のため時刻判定をスキップして送信"

    settings = load_settings()
    if not settings.get("enabled", True):
        return False, "設定で通知がオフのため送信しません"

    state = _read_json(STATE_PATH) or {}
    if state.get("last_notified_date") == today_iso:
        return False, f"本日（{today_iso}）はすでに通知済みのため送信しません"

    h, m = _parse_hhmm(settings.get("send_time"))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if now < target:
        return False, f"まだ配信時刻前（設定 {h:02d}:{m:02d} / 現在 {now.strftime('%H:%M')} JST）のため送信しません"

    return True, f"配信時刻（{h:02d}:{m:02d}）を過ぎているため送信します"
