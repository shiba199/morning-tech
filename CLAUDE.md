# 朝刊テック プロジェクト — Claude Code 向けガイド

自分専用の「毎朝のITニュース秘書」アプリ。複数のRSSからAWS/IT記事を集め、
興味トピックで絞り込み、「今朝のまとめ」を自動生成して通知する。
利用者は中小IT企業のブログ担当者で、AWSの新機能をいち早く把握してブログのネタにする。

## 📌 仕様ドキュメントの管理ルール（重要・チャットをまたいで厳守）

仕様の**正本（source of truth）は `docs/` フォルダ**にある。

- `docs/朝刊テック_仕様書.md` … 仕様書（実装の指示書）
- `docs/morning_tech_briefing.html` … 完成イメージのデザイン見本（ブラウザで開いて操作可能）
- `docs/CHANGELOG.md` … 仕様・ドキュメントの更新履歴

**守ること:**
1. **仕様変更があったら、その都度 `docs/` の該当ファイルを更新する。**
   会話の中だけで仕様を決めて終わりにしない。必ずファイルに反映する。
2. 更新したら必ず **`docs/CHANGELOG.md` の先頭に「日付・変更内容」を1行追記**する。
   → これにより、チャット（セッション）が変わっても変更経緯が分かる。
3. **新しいチャットを始めたら、まず `docs/` 一式と この `CLAUDE.md` と `docs/CHANGELOG.md` を読む。**
   そこに書かれた最新の仕様・進捗を前提に作業する。

## 方針：完全無料で組む（決定済み 2026-06-11）

- **要約（ステップ5）= 抽出型**（AIなし・無料・全自動）。RSS概要文や冒頭文を抜き出して並べる。
  要約ロジックは差し替え可能に作り、将来 ChatGPT貼り付け半自動 or OpenAI/Claude API へ移行可能にする。
  （ChatGPT月額サブスクに API は含まれない＝自動化には別途API課金が必要）
- **アプリ化 = PWA**（無料）。iPhoneは Safari→ホーム画面追加でアプリのように起動。
- **通知 = PWAのWeb Push**（iOS16.4以降・無料）。代替は Discord/メール。LINE Notify は終了済み。
- **定期実行 = GitHub Actions の cron**（無料枠）。

## 実装ステップ（仕様書セクション8）

1. ✅ **ステップ1**: RSS取得スクリプト（コンソール出力で動作確認） → `fetch_feeds.py`（完了）
2. ✅ **ステップ2**: 取得結果をSQLiteに保存（重複登録しない） → `db.py` + `fetch_feeds.py`（完了）
3. ✅ **ステップ3**: 記事をトピック分類（キーワードマッチ） → `classify.py` + `classify_articles.py`（完了）
4. ✅ **ステップ4**: HTMLを土台に、バックエンドの実データを表示するWebアプリ化 → `app.py` + `web/index.html`（完了）
5. ✅ **ステップ5**: 「今朝のまとめ」自動生成（抽出型・無料／将来Claude APIへ差替可） → `summarize.py`（完了）
6. ✅ **ステップ6**: 定期実行（GitHub Actions cron）で毎朝自動更新 → `update.py` + `.github/workflows/morning.yml`（実装完了・push待ち）
7. ✅ **ステップ7**: 通知（Discord webhook） → `notify.py`（実装完了・webhook URL登録待ち）
8. ✅ **ステップ8**: PWA化（ホーム画面追加で起動／オフライン対応／Web Push受け口） → `web/manifest.json` + `web/sw.js` + `web/icons/`（実装完了・Pages公開待ち）

## 現在の進捗

> **2026-06-12: MVP（ステップ1〜8）本番公開済み。** GitHub Desktop でローカルをGit化＆初期コミット → `shiba199/morning-tech`
> として公開（public）リポジトリに push 済み。GitHub Pages 有効化（Source=GitHub Actions）→ `deploy-pages` 成功で
> **ライブURL `https://shiba199.github.io/morning-tech/`** が稼働。iPhoneのSafariからホーム画面追加でPWA起動を確認。
> 残タスク（任意）: Discord通知のSecret `DISCORD_WEBHOOK_URL` 登録（未確認なら、Discordでwebhook作成→Settings>Secrets>Actions）。
> 発展課題: 本物のWeb Push／英語記事の翻訳／既読・ブックマーク／設定の永続化／要約のLLM化（Claude API）。
>
> **2026-06-13 不具合修正**: ①自動更新コミット（GITHub_TOKEN）では Pages が再デプロイされないGitHub仕様に対応
> （morning.yml から `gh workflow run pages.yml` で明示起動・`actions: write` 追加）。②cron を `47 21 * * *`（6:47 JST）に変更
> （毎時0分は遅延・スキップされやすい。6/13朝はスキップ発生）。③通知タブを実データで実装（まとめ完成＋トピック別新着、
> 未読バッジ・localStorage既読管理）。④設定の「配信する時刻」を実態表記に修正（cron編集で変更する旨を明記）。
> ⑤sw.js のキャッシュ版を v2 に（土台変更時は版を上げないと既存PWAに反映されない）。
>
> **2026-06-14 新機能（配信時刻をアプリから変更）**: `schedule_gate.py` が `web/data/settings.json`（send_time/enabled）を読み、
> 「設定時刻を過ぎ・本日未送信なら送る」判定（notify_state.json で重複防止・JST基準）。cron は `*/30 * * * *` に変更し
> 実時刻は settings.json で決定（手動実行は `--force` で必ず送信）。設定画面に時刻ピッカー＋GitHub連携を追加し、保存時は
> Contents API で settings.json を更新。認証は利用者の fine-grained PAT（Contents:Read and write）を localStorage 保存（端末内のみ）。
> SWキャッシュ v3。**利用者の手作業**: 設定→「GitHubと連携する」でトークンを1回登録（手順は下記「配信時刻の変更（アプリ）」）。

## 配信時刻の変更（アプリから・利用者の手作業）

アプリの**設定タブ**で時刻を選んで保存すると、`web/data/settings.json` が更新され、次回以降その時刻で通知される。
初回だけ「合鍵（トークン）」の登録が必要（GitHubへ保存するため）。
1. アプリの**設定 → 「GitHubと連携する」**をタップ。
2. 開いたGitHubのページで: Repository access=「Only select repositories」→ `morning-tech` を選択／Permissions の **Contents を「Read and write」**／Generate token。
3. 表示された文字列（`github_pat_...`）をコピーし、アプリの入力欄に貼り付け。合鍵は**その端末のブラウザ内だけ**に保存される。
4. 以後は時刻ピッカーで選び「この時刻で保存」を押すだけ。通知のオン/オフも同様に保存される。
- 精度: 自動実行は30分おき＋GitHubの遅延があるため「設定時刻〜+30分程度」で届く。厳密な定刻は仕様上不可。
- トークンを使いたくない場合は、従来どおり `.github/workflows/morning.yml` の cron 直接編集でも変更可（変換表をファイル内に記載）。

- **ステップ1 完了**: `fetch_feeds.py`（日本語フィード3つ＝AWS日本語ブログ・DevelopersIO・Publickey から
  最新記事のタイトル・リンク・日付・取得元を取得しコンソール表示）。動作確認済み。
- **ステップ2 完了**: `db.py`（SQLite保存。`link` を UNIQUE キーにして `INSERT OR IGNORE` で重複登録を防止）。
  `fetch_feeds.py` が取得後に `articles.db` へ保存し、新規/スキップ件数を表示。
  2回実行しても増えない（新規0・スキップ15）ことを確認済み。
- **ステップ3 完了**: `classify.py`（キーワードマッチによるトピック分類。トピック定義 `TOPICS` を
  コードの一覧データとして管理。分類の入口は `classify_text()` 1関数に集約し、将来 LLM 分類へ差し替え可能）。
  `classify_articles.py` がDBの未分類記事を分類し、結果を `articles.db` の `topics` 列（カンマ区切りID）に
  書き戻してトピック別に一覧表示する。1記事が複数トピックに属する分類（例「生成AI＋開発ツール」）と、
  再実行で未分類0件になる冪等性を確認済み。トピックIDは HTML見本に合わせ `ai/cloud/sec/data/dev`。
- **ステップ4 完了**: `app.py`（Python標準ライブラリ `http.server` だけで動く簡易Webサーバー。追加インストール不要）。
  `GET /` で `web/index.html`、`/api/articles`・`/api/topics`・`/api/sources` でDBの実データをJSON配信。
  `web/index.html` は `docs/morning_tech_briefing.html` のデザインを踏襲しつつ、サンプルデータを廃して
  APIから実データを取得して描画（ホームの新着フィード／興味チップでの絞り込み／設定のトピック・取得元一覧）。
  記事カードはリンク先を新しいタブで開く。相対時刻・NEW判定はフロント側で算出。まとめ/通知タブはステップ5/7の準備中表示。
  4エンドポイントの200応答と実データ15件の配信を確認済み。
- **ステップ5 完了**: `summarize.py`（「今朝のまとめ」を**抽出型**で自動生成。LLM不使用＝無料・全自動）。
  過去24時間の記事を `db.get_articles_since()` で取得し、トピックごとにグループ化、各記事のRSS概要文（`summary`）の
  冒頭1〜2文を抜き出して並べる。要約の入口は `summarize_topic(label, articles)` の1関数に集約し、将来 Claude API へ
  中身だけ差し替え可能。DBに `summary` 列を追加（`fetch_feeds.py` が概要文を保存。既存記事は再取得時にバックフィル）。
  `app.py` に `GET /api/digest` を追加し、`web/index.html` の「まとめ」タブをデザイン見本どおり（hero＋トピック別theme）に
  実データで描画。動作確認: 過去24時間10件を5トピックに整理して表示できることを確認。
- **ステップ6 実装完了（GitHubへのpush待ち）**: `update.py`（取得→分類→静的スナップショット出力を1コマンドで実行）と
  `.github/workflows/morning.yml`（cron `0 22 * * *`＝7:00 JST に毎朝実行。手動実行も可）。`requirements.txt`・`.gitignore` も追加。
  Actionsのランナーは毎回まっさらで常駐サーバーを持てないため、`update.py` が `web/data/*.json`（articles/topics/sources/digest）
  を書き出し、ワークフローが `articles.db` と `web/data` を**リポジトリにコミットし直して**結果を保存する。
  `web/index.html` は `/api/*`（app.py）→ 無ければ `./data/*.json`（静的）にフォールバックするので、ローカルでも静的ホスティングでも同じ画面が動く。
  **未了の手作業（利用者）**: GitHubリポジトリ作成＋push（手順は CLAUDE.md「GitHub Actions のセットアップ」参照）。cronはUTC基準で混雑時に遅延あり。
- **ステップ7 実装完了（webhook URL登録待ち）**: `notify.py`（「今朝のまとめ」をDiscord webhookに投稿。標準ライブラリ `urllib` のみ＝追加依存なし）。
  `update.py` がスナップショット生成後に `notify.send_digest()` を呼ぶ。webhook URLは環境変数 `DISCORD_WEBHOOK_URL` から読み、
  **未設定ならスキップ**（ローカル実行で誤爆しない）。新着0件の朝は送らない。ワークフローは Secrets の `DISCORD_WEBHOOK_URL` を環境変数で渡す。
  スマホのDiscordアプリがOSプッシュ通知を出すので体感は「普通のアプリ通知」。通知の入口は `send_digest()` 1関数で、将来 Web Push（ステップ8）へ差し替え可能。
  `--dry-run` で送らず本文確認可。動作確認: dry-runで埋め込みメッセージ（トピック別リンク）が正しく生成されることを確認。
  **未了の手作業（利用者）**: Discordのwebhook作成＋GitHub Secretsへ `DISCORD_WEBHOOK_URL` 登録（手順は CLAUDE.md「Discord通知のセットアップ」参照）。
- **ステップ8 実装完了（GitHub Pages公開待ち）**: PWA化。`web/manifest.json`（アプリ名・アイコン・standalone起動）、`web/sw.js`
  （Service Worker：土台はキャッシュ優先でオフライン起動、データはネット優先＋失敗時キャッシュ、`push`/`notificationclick` の受け口も用意）、
  `web/icons/`（`tools/make_icons.py` が標準ライブラリのみでブランド配色アイコンを生成。512/192/180/32）。`web/index.html` に manifest・
  apple-touch-icon・各種metaを追加し、Service Worker を登録。`app.py` は `web/` 配下を静的配信するよう拡張（パストラバーサル対策つき）。
  `.github/workflows/pages.yml` で `web/` を GitHub Pages に公開（main への push＝毎朝の自動更新ごとに再デプロイ）。
  iOSはHTTPS必須のため、ローカル(app.py)ではなく Pages のURLをホーム画面に追加して使う。Web Push本体（VAPID鍵・購読・送信）は未実装＝発展課題。
  動作確認: ローカルで manifest/sw/icons/data/api が正しいContent-Typeで配信され、パストラバーサルが404になることを確認。
  **未了の手作業（利用者）**: GitHub Pages を有効化（Settings > Pages > Source = GitHub Actions）→ 公開URLをiPhone Safariで開き「ホーム画面に追加」。
- **MVP（ステップ1〜8）完成**。発展課題: 本物のWeb Push（自分のアイコン通知）、英語記事の翻訳、既読/ブックマーク、設定の永続化、要約のLLM化（Claude API）。

## PWA（ホーム画面アプリ）のセットアップ（ステップ8・利用者の手作業）

iOSは「HTTPSで配信されたサイト」でないとPWAとして正しく動かない。GitHub Pagesで公開して使う。
1. リポジトリを push 済みにする（「GitHub Actions のセットアップ」参照）。
2. GitHubリポジトリの **Settings > Pages** → **Source** を「**GitHub Actions**」に設定。
3. `deploy-pages` ワークフローが走り、公開URL（例 `https://<ユーザー名>.github.io/<リポジトリ名>/`）が発行される。
4. iPhoneの **Safari** でそのURLを開く → 共有ボタン → **「ホーム画面に追加」** → 「朝刊テック」アイコンで起動できる。
5. 毎朝の自動更新（morning-update）が push するたびに Pages も再デプロイされ、最新のまとめが反映される。
- アイコンを変えたいとき: `tools/make_icons.py` を編集して再実行（`web/icons/` を再生成）。
- 補足: ローカルの `app.py` でもPWAファイルは配信されるが、`http://localhost` 以外のHTTPだとiOSはインストール不可。確認用途は Pages を使う。

## Discord通知のセットアップ（ステップ7・利用者の手作業）

1. Discordで通知を受けたいサーバー（自分専用でOK）→ チャンネルの「⚙️ 編集」→「連携サービス」→「ウェブフックを作成」→ URLをコピー。
2. GitHubリポジトリの **Settings > Secrets and variables > Actions** →「New repository secret」→
   名前 `DISCORD_WEBHOOK_URL`、値にコピーしたURLを登録。
3. Actionsの `morning-update` を手動実行（または毎朝の自動実行）すると、スマホのDiscordに「今朝のまとめ」が届く。
- ローカルで試したいとき: PowerShellで `$env:DISCORD_WEBHOOK_URL="<URL>"` を設定してから `.venv\Scripts\python.exe notify.py`。
  送らず本文だけ見たいときは `.venv\Scripts\python.exe notify.py --dry-run`。

## GitHub Actions のセットアップ（ステップ6・利用者の手作業）

ローカルにファイルは用意済み。GitHubに上げると毎朝自動で動く。
1. ローカルをGit化: `git init` → `git add -A` → `git commit -m "朝刊テック 初期コミット"`
2. GitHubで空リポジトリを作成（例 `morning-tech`、privateでよい）。
3. リモート登録して push: `git remote add origin <作ったリポジトリのURL>` → `git branch -M main` → `git push -u origin main`
4. GitHubの **Actions** タブで `morning-update` を開き、`Run workflow` で手動実行して動作確認。
5. 以後は毎朝 6:47 JST 開始（GitHubの混雑により数分〜数十分遅延あり）で自動実行され、`articles.db` と `web/data/*.json` が更新コミットされる。
- 補足: ワークフローは `permissions: contents: write` で標準の `GITHUB_TOKEN` を使って push する（追加のシークレット不要）。
- 補足2: GITHUB_TOKEN の push では他ワークフローが発火しない（GitHubの仕様）ため、morning.yml の最後に
  `gh workflow run pages.yml` で Pages 再デプロイを明示起動している（`permissions: actions: write` が必要）。
- 配信時刻を変えたい場合は `.github/workflows/morning.yml` の cron を編集（UTC表記。例 21:47 UTC = 翌6:47 JST。
  毎時0分ちょうどは混雑で遅延・スキップされやすいため、半端な分を推奨）。

## Webアプリの起動

- 手順: ① `fetch_feeds.py`（取得＋保存）→ ② `classify_articles.py`（分類）→ ③ `app.py`（サーバー起動）。
- 実行: `.venv\Scripts\python.exe app.py` → ブラウザで `http://localhost:8000` を開く（停止は Ctrl+C）。
- フロントは自分のAPI（`/api/*`）だけを叩く。RSS直叩きはCORSで失敗するため取得・分類はバックエンドで完結させる。

## データベース

- ファイル: `articles.db`（SQLite、`db.py` の `DB_PATH`）。Git管理する場合は `.gitignore` 推奨。
- テーブル `articles`: `id, source, title, link(UNIQUE), published(ISO文字列), fetched_at(ISO), topics(カンマ区切りID/未分類はNULL), summary(RSS概要文/NULL)`。
  `topics` はステップ3、`summary` はステップ5で追加。既存DBには `init_db()` 内の `_ensure_columns()` が `ALTER TABLE` で後付けする。

## 開発メモ

- 環境: Windows / PowerShell。Python仮想環境は `.venv`。
- 実行例: `.venv\Scripts\python.exe fetch_feeds.py`
- RSS取得は必ずサーバー側（バックエンド）で行う（ブラウザ直叩きはCORSでブロックされる）。
- 取得元・興味トピックはコードに一覧データとして持ち、設定でオンオフできるようにする。
- LLMでの要約・分類はステップ5以降（Anthropic API / Claude）。
