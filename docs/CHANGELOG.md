# 仕様・ドキュメント更新履歴

> 仕様変更があるたびに、このファイルの先頭に「日付・変更内容」を1行追記すること。
> これにより、チャット（セッション）が変わっても「いつ・何を変えたか」が追えるようにする。
> 記入フォーマット: `- YYYY-MM-DD: 変更内容（対象ファイル）`

## 2026-06-14（追記4）
- **新機能: 英語記事の日本語自動翻訳**（仕様書セクション3「英語記事の翻訳」を実装。無料・キー不要）:
  - `translate.py` を新設。Google翻訳の無料エンドポイントを標準ライブラリ `urllib` で叩いて英→日翻訳（追加依存なし）。
    入口は `translate(text)` の1関数（将来 Claude API へ差し替え可）。失敗時は原文を返す安全設計。`has_japanese()` で訳要否を判定。
  - `AWS公式ブログ` を日本語版→**英語版「AWS News Blog（英語）」**（`/blogs/aws/feed/`）に変更（`BUILTIN_FEEDS`）。一次情報が速い。
  - `update.py` に翻訳ステップを追加（取得→**翻訳**→分類の順）。DBに `translated` 列を追加し、未処理（NULL）の記事だけ処理。
    英語タイトル/概要を日本語化し、日本語記事は素通し。いずれも処理済みにして同じ記事を毎回翻訳しにいかない（API負荷・取りこぼし防止）。
  - 固有名詞（Amazon S3 / Bedrock / GuardDuty 等）は概ね保持されるため、翻訳後の日本語タイトルでもキーワード分類が機能することを確認。
  - 動作確認: 英語記事のタイトル・概要が日本語化され、分類（例: クラウド＋セキュリティ）も正しく付くことを確認。`web/data/sources.json` も更新。
  - 注意: 非公式エンドポイントのため稀に翻訳が失敗しうる（その場合は英語のまま表示＝記事は消えない）。他の英語サイトを追加しても自動で日本語化される。

## 2026-06-14（追記3）
- **取得を「公開24時間以内」に絞り込み**: `fetch_feeds.fetch_feed()` で、各フィードの最新 `MAX_PER_FEED`(=5) 件のうち、
  公開日時が24時間より前のものは保存しないように変更（`FRESH_HOURS=24`）。基準時刻はRSSのUTC日時に合わせ naive UTC で比較。
  日時不明の記事は判定不能のため従来どおり採用。更新頻度の低いサイトはその日0件になることがある（＝仕様どおりの挙動）。
  ※ ホームの新着フィードは引き続きDB蓄積分（最新100件）を表示。「まとめ/通知」は従来どおり公開24時間以内。

## 2026-06-14（追記2）
- **新機能: ニュース取得元をアプリから追加・削除・オンオフできるように**（仕様書セクション5「設定でオンオフ」を実装）:
  - `fetch_feeds.py`: 初期サイトを `BUILTIN_FEEDS`（`FEEDS` は後方互換エイリアス）に整理し、利用者設定 `web/data/feeds.json`
    （`{custom:[{name,url}], disabled:[url]}`）と統合する `get_effective_feeds()` / `get_active_feeds()` を追加。URL重複は排除。
  - `update.py`・`fetch_feeds.main()` は `get_active_feeds()`（有効な取得元のみ）を使うように変更。`app.py` の `get_sources_payload()` は
    `builtin`/`enabled` フラグ付きの統合一覧を返すように変更（`web/data/sources.json` も同形に更新）。
  - フロント（`web/index.html`）の設定「ニュースの取得元」を編集UIに刷新: 各サイトにオン/オフのトグル、追加サイトには✕削除、
    下部に「サイト名＋RSSのURL＋追加」フォーム。変更は GitHub Contents API で `web/data/feeds.json` を更新（時刻保存と同じトークンを共用）。
    GitHub保存処理を `ghPutJson()` に共通化。URL形式チェック・重複チェック・失敗時ロールバックつき。SWキャッシュ v7。
  - 反映タイミング: 保存後、次の自動更新（最大30分後）から新しい取得元で記事を集める。`web/data/feeds.json` 初期ファイル（空）を追加。
  - **未了の手作業（利用者）**: 追加・オンオフの保存には既存の「GitHub連携（トークン）」が必要（時刻変更と共通）。

## 2026-06-14
- **新機能: 配信時刻をアプリの設定画面から変更できるように**（YAML編集不要）。発展課題「設定の永続化」に着手。
  - `schedule_gate.py` を新設。アプリで選んだ時刻（`web/data/settings.json` の `send_time`／`enabled`）を読み、
    「設定時刻を過ぎていて今日まだ送っていなければ送る」＝1日1回・キャッチアップ方式で判定。重複送信は `web/data/notify_state.json` で防止。
    時刻はJST(UTC+9)で扱う。`web/data/settings.json` を新設（既定 06:47）。
  - `morning.yml` の cron を `*/30 * * * *`（30分おき）に変更。実通知時刻は settings.json で決まるためYAML編集が不要に。
    手動実行(workflow_dispatch)時は `--force` を渡して時刻判定を飛ばし必ず送信。`concurrency` で実行重複を防止、push前に `git pull --rebase`。
  - `update.py`: スナップショット生成後に `schedule_gate` の判定で通知。送信を試みた日は notify_state に記録。
  - フロント（`web/index.html`）の設定画面に、時刻ピッカー＋「この時刻で保存」＋通知オン/オフ＋「GitHub連携」を追加。
    保存時はGitHub Contents APIで `web/data/settings.json` を直接更新（リポジトリ場所はサイトURLから推測）。
    認証は利用者が作成する fine-grained PAT（Contents: Read and write）を localStorage に保存（端末内のみ）。SWキャッシュを v3 に。
  - **未了の手作業（利用者）**: アプリの設定→「GitHubと連携する」からトークンを1回登録すれば、以後スマホだけで時刻変更可。

## 2026-06-13（追記）
- **不具合修正（Discord通知が 403 Forbidden で送れない）**: Secret登録済みでも通知が届かない原因は、`urllib` の既定
  User-Agent（`Python-urllib/3.x`）を Discord（Cloudflare）が機械的にブロックするため。`notify.py` の送信ヘッダに
  独自の User-Agent（`MorningTechBot/1.0`）を明示して回避。HTTPエラー時はDiscordの応答本文の先頭も表示するよう改善。
  （Actions実行ログ `通知の送信に失敗しました: HTTP Error 403: Forbidden` で特定。なお同ログで、前日修正の
  「自動更新→Pages再デプロイ連鎖」が正しく動作しサイトに反映されることも確認済み。）

## 2026-06-13
- **不具合修正（毎朝の自動更新がサイトに反映されない）**: `morning.yml` の自動コミットは `GITHUB_TOKEN` による push のため、
  GitHubの仕様（無限ループ防止）で `deploy-pages` の `on: push` が**発火しない**ことが判明（6/12朝の自動更新はリポジトリに
  コミットされたが、Pagesは初回デプロイのままだった）。対策として、`morning.yml` の最後に `gh workflow run pages.yml` で
  deploy-pages を明示起動するステップを追加（`workflow_dispatch` は GITHUB_TOKEN でも起動できる例外）。`permissions: actions: write` を追加。
- **cron時刻の変更**: `0 22 * * *`（7:00 JST）→ `47 21 * * *`（6:47 JST開始）。毎時0分は混雑で遅延・スキップが起きやすいため
  半端な分にずらす定石を適用（6/13朝はcron実行自体がスキップされていた）。7:00までに通知が届くことを目標に前倒し。
- **通知タブを実装**（「準備中」を解消）: `web/index.html` の通知タブに、まとめ生成（「今朝のまとめができました」）と
  トピック別新着（「興味◯◯に新着」）の通知一覧を実データから自動生成して表示。未読バッジ（タブ上の件数）と既読管理
  （localStorage）付き。通知タップで該当タブへ移動。
- **設定画面の「配信する時刻」を実態に合わせ修正**: 7:00固定のモック表示だった箇所を「毎朝6:47開始（遅延あり）。変更は
  morning.yml の cron を編集」という正直な説明に変更。トグルが表示のみである旨も明記（設定の永続化は発展課題のまま）。
- **Service Worker のキャッシュ版を v2 に**: 土台（index.html）はキャッシュ優先のため、版を上げないと既存PWAに変更が届かない。

## 2026-06-12（本番公開）
- **MVPを本番公開**。GitHub DesktopでローカルをGit化＆初期コミット → 公開リポジトリ `shiba199/morning-tech` に push。
  GitHub Pages（Source=GitHub Actions）を有効化し `deploy-pages` 成功 → ライブURL `https://shiba199.github.io/morning-tech/` 稼働。
  iPhone Safari からホーム画面追加でPWA起動を確認。Pagesは無料プランの制約で private 不可のため public に変更（コードに機密なし／
  Discord webhook は Secrets 管理のため非公開のまま）。Discord通知Secretの登録は任意の残タスク。

## 2026-06-12
- **ステップ8（PWA化）を実装**（GitHub Pages公開は利用者の手作業として残す）。**MVP（ステップ1〜8）完成**:
  - `web/manifest.json`（アプリ名・standalone起動・theme color）、`web/sw.js`（Service Worker：土台はキャッシュ優先でオフライン起動、
    データはネット優先＋失敗時キャッシュ、Web Pushの `push`/`notificationclick` 受け口も用意）を新設。
  - `tools/make_icons.py` を新設。Pillow等を使わず標準ライブラリ（zlib/struct）だけでブランド配色（朝焼け＋朝日）のPNGアイコンを生成し、
    `web/icons/`（512/192/apple-touch-icon 180/favicon 32）を出力。
  - `web/index.html` に manifest・apple-touch-icon・PWA用metaを追加し、Service Worker を登録。
  - `app.py` を拡張し、`web/` 配下の静的ファイル（manifest/sw/icons/data）を配信（パストラバーサル対策つき）。
  - `.github/workflows/pages.yml` を新設。`web/` を GitHub Pages に公開し、main への push（毎朝の自動更新コミット含む）ごとに再デプロイ。
  - iOSはHTTPS必須のため、Pages公開URLをSafariで開き「ホーム画面に追加」して使う。Web Push本体（VAPID/購読/送信）は発展課題として未実装。
  - 動作確認: ローカルで manifest/sw/icons/data/api が正しいContent-Typeで配信、パストラバーサルが404になることを確認。アイコン画像の見た目も確認。
  - 発展課題: 本物のWeb Push、英語記事の翻訳、既読/ブックマーク、設定の永続化、要約のLLM化（Claude API）。

## 2026-06-11（追記5）
- **ステップ7（通知・Discord webhook）を実装**（webhook URL登録は利用者の手作業として残す）:
  - `notify.py` を新設。「今朝のまとめ」をDiscordのwebhookに埋め込みメッセージ（トピック別の記事リンク一覧）として投稿。
    送信は標準ライブラリ `urllib` のみ（追加依存なし）。通知の入口は `send_digest(digest)` の1関数に集約し、将来 Web Push/メールへ差し替え可能。
  - webhook URLは環境変数 `DISCORD_WEBHOOK_URL` から読み、未設定ならスキップ（ローカル実行で誤爆防止）。新着0件の朝は送らない。`--dry-run` で本文確認可。
  - `update.py` がスナップショット生成後に `notify.send_digest()` を呼ぶよう統合。`.github/workflows/morning.yml` は Secrets の
    `DISCORD_WEBHOOK_URL` を当該ステップに環境変数で渡す（未登録でも更新は止まらない）。
  - 動作確認: `notify.py --dry-run` で過去24時間10件・5トピックの埋め込みメッセージが正しく生成されることを確認。Discord側のセットアップ手順は CLAUDE.md に記載。
  - 次の作業: ステップ8（PWA化／希望すれば本物のWeb Push）。

## 2026-06-11（追記4）
- **ステップ6（定期実行・GitHub Actions cron）を実装**（GitHubへのpushは利用者の手作業として残す）:
  - `update.py` を新設。取得→分類→静的スナップショット出力を1コマンドで実行。JSON生成は `app.py` のロジックを再利用し形状を一元化。
  - `.github/workflows/morning.yml` を新設。cron `0 22 * * *`（=7:00 JST、UTC基準で遅延あり）＋手動実行。`update.py` 実行後、
    `articles.db` と `web/data/*.json` の差分があればコミットして push（`GITHUB_TOKEN` + `contents: write`、追加シークレット不要）。
  - ランナーは常駐サーバーを持てないため、`update.py` が `web/data/{articles,topics,sources,digest}.json` を書き出し、リポジトリに
    積み上げて保存する方式に。`web/index.html` を `/api/*`→`./data/*.json` のフォールバック対応にし、ローカル/静的ホスティング双方で動くように（ステップ8 PWAへの布石）。
  - `requirements.txt`（feedparser）と `.gitignore`（.venv等を除外、articles.db と web/data は追跡）を追加。
  - 動作確認: `update.py` がローカルで完走し、`web/data` に4つのJSONを生成することを確認。GitHub側のセットアップ手順は CLAUDE.md に記載。
  - 次の作業: ステップ7（通知）。

## 2026-06-11（追記3）
- **ステップ5（「今朝のまとめ」自動生成・抽出型）を実装**:
  - `summarize.py` を新設。過去24時間の記事をトピック別にまとめ、各記事のRSS概要文の冒頭1〜2文を抜き出して並べる
    **抽出型**（LLM不使用＝無料・全自動。仕様書セクション7の採用方針）。HTMLタグ除去・文単位の切り出しを実装。
    要約の入口は `summarize_topic(label, articles)` の1関数に集約し、将来 Claude API（B案/C案）へ中身だけ差し替え可能。
  - DBに `summary` 列を追加（`db.py` の `_ensure_columns()` でマイグレーション）。`fetch_feeds.py` がRSS概要文を保存し、
    既存記事は再取得時に summary をバックフィルする。期間取得 `get_articles_since()` を追加。
  - `app.py` に `GET /api/digest` を追加。`web/index.html` の「まとめ」タブを、デザイン見本どおり（オレンジのhero＋
    トピック別theme＋記事ミニリスト）に実データで描画。各記事は元リンクを新しいタブで開く。
  - 動作確認: 過去24時間10件を5トピックに整理し、概要文付きで表示できることを確認。
  - 次の作業: ステップ6（GitHub Actions の cron で毎朝自動更新）。

## 2026-06-11（追記2）
- **ステップ4（実データWebアプリのMVP）を実装**:
  - `app.py` を新設。Python標準ライブラリ `http.server` のみで動く簡易サーバー（FastAPI等は入れない＝追加費用・依存なし）。
    `GET /` で `web/index.html` を返し、`/api/articles`・`/api/topics`・`/api/sources` でSQLiteの実データをJSON配信。
    RSS取得・分類はバックエンドで完結させ、フロントは自分のAPIだけを叩く（CORS回避・仕様書セクション4）。
  - `web/index.html` を新設。`docs/morning_tech_briefing.html` のデザインを踏襲しつつ、サンプルデータを廃して
    API由来の実データで描画。ホームの新着フィード、興味チップでの絞り込み、設定のトピック・取得元一覧が実データで動く。
    記事カードは元記事リンクを新しいタブで開く。相対時刻・NEW判定はフロント側で算出。
    まとめ/通知タブはステップ5/7の「準備中」表示に。
  - 取得元のバッジ色分け（aws/dev/news）とトピックタグ色（ai/cloud/sec/data/dev）を実データIDに対応。
  - 動作確認: 4エンドポイントが200応答、実データ15件をホームに表示できることを確認。
  - 次の作業: ステップ5（「今朝のまとめ」自動生成。まず抽出型＝無料・全自動）。

## 2026-06-11（追記）
- **ステップ3（トピック分類・キーワードマッチ）を実装**:
  - `classify.py` を新設。トピック定義 `TOPICS`（id/label/keywords）をコードの一覧データとして管理。
    トピックIDは HTMLデザイン見本に合わせて `ai/cloud/sec/data/dev`。分類の入口は `classify_text()` 1関数に
    集約し、将来 LLM 分類（仕様書セクション6・案2）へ中身だけ差し替え可能な形にした（入出力固定）。
  - `db.py` に `topics` 列を追加（カンマ区切りID）。既存DB向けに `_ensure_topics_column()` で `ALTER TABLE`
    マイグレーションを実装。`set_article_topics()` / `get_articles_for_classification()` を追加。
  - `classify_articles.py` を新設。DBの未分類記事を分類して `topics` 列に書き戻し、トピック別に一覧表示。
    `--all` で全記事の再分類も可能。
  - 動作確認: 既存15件を分類。複数トピック分類（例「生成AI＋開発ツール」）と、再実行で未分類0件になる
    冪等性を確認済み。
  - 次の作業: ステップ4（HTMLを土台にした実データ表示のWebアプリ化）。

## 2026-06-11
- **方針決定（コスト＝完全無料で進める）**:
  - 「今朝のまとめ」の要約は **当面「抽出型」（AIなし・無料・全自動）** を採用（仕様書セクション7）。
    将来は B案=ChatGPTに貼る半自動 / C案=OpenAI or Claude API で全自動、に差し替え可能な形で実装する。
    （ChatGPTの月額サブスクには API 利用は含まれない点に注意）
  - スマホアプリ化は **PWA**（無料・iOSはホーム画面追加で起動）を採用。ネイティブ配信は見送り。
  - 通知は **PWAのWeb Push（iOS16.4以降・無料）**、当面の代替は **Discord/メール**。LINE Notify は終了済み。
  - 定期実行は **GitHub Actions の cron（無料枠）** を採用。
- ステップ2（SQLite保存）を実装。`db.py` を新設し、`fetch_feeds.py` から保存を呼び出すよう更新。
  `link` を UNIQUE キーにして `INSERT OR IGNORE` で重複登録を防止。2回実行で増えないことを確認（`articles.db` 総15件）。
- `docs/` フォルダを新設し、仕様書とデザイン見本を格納（初版）。
  - `docs/朝刊テック_仕様書.md`（チャットに貼られた文字化け版を、内容を保ったまま正しい日本語に復元して保存）
  - `docs/morning_tech_briefing.html`（同上。デザイン見本）
- `docs/CHANGELOG.md` を新設（この更新履歴）。
- ルート直下に `CLAUDE.md` を作成し、ドキュメント更新ルールを明文化。
- 進捗メモ: ステップ1（RSS取得スクリプト `fetch_feeds.py`）は実装・動作確認済み。次はステップ2（SQLite保存）。
