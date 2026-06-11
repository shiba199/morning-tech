# -*- coding: utf-8 -*-
"""
朝刊テック - ステップ3: トピック分類モジュール（キーワードマッチ版）

記事のタイトル（＋あれば概要文）に、各トピックのキーワードが含まれるかで
トピックを判定する。1記事が複数トピックに属してよい（仕様書セクション6）。

■ 設計方針（差し替え可能に作る）
  分類の入口は classify_text(text) の1関数だけ。中身は今は「キーワードマッチ」だが、
  将来この関数の中身を Claude API などの「LLM分類」に差し替えれば、
  呼び出し側（db.py / 表示側）は一切変えずに精度を上げられる。
  （仕様書セクション6：案1=キーワードマッチ → 案2=LLM分類）

■ トピックID は HTML デザイン見本（docs/morning_tech_briefing.html）と揃える:
    ai=生成AI / cloud=クラウド / sec=セキュリティ / data=データ分析 / dev=開発ツール
"""

# --- トピック定義（設定画面でオンオフできるよう、コードの一覧データとして管理） ---
# id    … HTML と揃えた内部ID（タグの色分け・絞り込みに使う）
# label … 画面に出す日本語名
# keywords … このトピックと判定するためのキーワード（小文字で比較。日本語はそのまま）
TOPICS = [
    {
        "id": "ai",
        "label": "生成AI",
        "keywords": [
            "bedrock", "claude", "gpt", "llm", "rag", "生成ai", "生成 ai",
            "aiエージェント", "ai エージェント", "agent", "エージェント",
            "機械学習", "machine learning", "sagemaker", "anthropic",
            "openai", "gemini", "transformer", "プロンプト", "推論", "ファインチューニング",
        ],
    },
    {
        "id": "cloud",
        "label": "クラウド",
        "keywords": [
            "ec2", "s3", "vpc", "移行", "マイグレーション", "migration",
            "サーバーレス", "serverless", "lambda", "fargate", "ecs", "eks",
            "コンテナ", "container", "kubernetes", "rds", "aurora",
            "オンプレ", "クラウド移行", "インフラ", "cloudfront", "route 53",
        ],
    },
    {
        "id": "sec",
        "label": "セキュリティ",
        "keywords": [
            "guardduty", "waf", "iam", "脆弱性", "ランサムウェア", "ransomware",
            "セキュリティ", "security", "暗号", "encryption", "マルウェア",
            "malware", "認証", "認可", "不正アクセス", "cve", "kms",
            "secrets manager", "shield", "ddos", "ゼロトラスト",
        ],
    },
    {
        "id": "data",
        "label": "データ分析",
        "keywords": [
            "opensearch", "redshift", "データ基盤", "データ分析", "bi",
            "athena", "glue", "quicksight", "emr", "kinesis",
            "データレイク", "data lake", "data warehouse", "dwh", "etl",
            "分析基盤", "ビッグデータ", "big data", "dynamodb",
        ],
    },
    {
        "id": "dev",
        "label": "開発ツール",
        "keywords": [
            "cdk", "amplify", "コーディングエージェント", "ci/cd", "cicd",
            "codepipeline", "codebuild", "codedeploy", "codewhisperer",
            "github", "git", "デプロイ", "deploy", "開発ツール", "sdk",
            "cli", "terraform", "iac", "やってみた", "cloudformation",
        ],
    },
]

# id -> label の早見表（表示側で使う）
TOPIC_LABELS = {t["id"]: t["label"] for t in TOPICS}


def classify_text(text):
    """
    与えられたテキストにマッチするトピックIDのリストを返す。

    ここが「分類の入口」。今はキーワードマッチだが、将来 LLM 分類に
    差し替えるならこの関数の中身だけを変えればよい（入出力は固定）。

    入力 : text … 判定対象の文字列（タイトル＋概要文など）
    出力 : ["ai", "dev"] のようなトピックIDのリスト（該当なしは []）
    """
    if not text:
        return []

    lowered = text.lower()
    matched = []
    for topic in TOPICS:
        for kw in topic["keywords"]:
            if kw in lowered:
                matched.append(topic["id"])
                break  # 1トピックにつき1回ヒットすれば十分
    return matched


def classify_article(title, summary=""):
    """記事のタイトルと概要から、トピックIDのリストを返す。"""
    text = f"{title} {summary}".strip()
    return classify_text(text)


def topics_to_labels(topic_ids):
    """トピックIDのリストを日本語ラベルのリストに変換する。"""
    return [TOPIC_LABELS.get(tid, tid) for tid in topic_ids]


# 単体動作確認用（python classify.py で簡単なテストを実行）
if __name__ == "__main__":
    samples = [
        "Amazon Bedrock に新しい Claude モデルが追加されました",
        "GuardDuty が S3 のマルウェアスキャンに対応",
        "AWS CDK でサーバーレスAPIを構築してみた",
        "Redshift Serverless でデータ分析基盤を作る",
        "今日のランチはカレーでした",  # どのトピックにも該当しない例
    ]
    for s in samples:
        ids = classify_text(s)
        labels = topics_to_labels(ids)
        print(f"- {s}")
        print(f"    → {ids}  {labels if labels else '（該当トピックなし）'}")
