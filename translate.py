# -*- coding: utf-8 -*-
"""
朝刊テック - 翻訳モジュール（英語→日本語・無料・キー不要）

英語記事のタイトル・概要を日本語に翻訳する。Google翻訳の無料エンドポイントを
標準ライブラリ urllib で叩くだけ（APIキー不要・追加費用0円・依存追加なし）。

■ 設計方針（差し替え可能に作る）
  翻訳の入口は translate(text) の1関数。中身を Claude API などに差し替えても、
  呼び出し側（update.py）は変えなくてよい。
  非公式エンドポイントのため失敗することがあるが、その場合は原文をそのまま返す
  （翻訳できなくても記事が消えない＝安全側に倒す）。
"""

import json
import re
import urllib.parse
import urllib.request

# 日本語（ひらがな・カタカナ・漢字・半角カナ）を含むかの判定用
_JP_RE = re.compile(r"[぀-ヿ㐀-鿿ｦ-ﾟ]")

# エンドポイントのURL長に収めるための上限（超過分は切り詰めて翻訳）
_MAX_CHARS = 4500

_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
_UA = "Mozilla/5.0 (compatible; MorningTechBot/1.0)"


def has_japanese(text):
    """テキストに日本語が含まれるか。含まれていれば翻訳不要とみなす。"""
    return bool(_JP_RE.search(text or ""))


def translate(text, source="en", target="ja"):
    """text を target 言語に翻訳して返す。失敗時は原文をそのまま返す。"""
    if not text or not text.strip():
        return text
    snippet = text[:_MAX_CHARS]
    try:
        params = urllib.parse.urlencode({
            "client": "gtx", "sl": source, "tl": target, "dt": "t", "q": snippet,
        })
        req = urllib.request.Request(f"{_ENDPOINT}?{params}", headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # data[0] は [翻訳片, 原文片, ...] のリスト。翻訳片を連結する。
        chunks = data[0] or []
        out = "".join(c[0] for c in chunks if c and c[0])
        return out or text
    except Exception:  # noqa: BLE001  失敗しても原文を返して処理を止めない
        return text


def translate_if_english(text):
    """日本語を含まないテキストだけ翻訳する（既に日本語ならそのまま）。"""
    if not text or has_japanese(text):
        return text
    return translate(text)


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for s in [
        "Amazon EC2 now supports new instance types for machine learning",
        "AWS announces general availability of Amazon Bedrock new features",
        "すでに日本語の記事はそのまま",
    ]:
        print(f"- 原文: {s}")
        print(f"  訳 : {translate_if_english(s)}")
