# CC Task Skills

Claude Codeで段階的な開発ワークフローを支援するカスタムスキル集です。個々の機能追加や改修を「タスク」として管理し、要件定義→詳細設計→ToDoリスト→実装→レビュー→修正→検証を順に進めることで、品質の高いソフトウェア開発を実現します。

## インストール

1. このリポジトリをクローンします：
```bash
git clone https://github.com/tombolo-jp/cc-task-skills.git
```

2. Claude Codeのスキルディレクトリにコピーします：
```bash
cp -r cc-task-skills/skills/* ~/.claude/skills/
```

3. （任意・このリポジトリを編集する場合）整合性チェックの pre-commit フックを有効化します：
```bash
git config core.hooksPath scripts/hooks
```
スキル定義やドキュメントの定型文のズレをコミット時に自動検出できます（詳細は後述「整合性チェック」）。

## 使用方法

> **フロー強制について**: 各スキルは「手順」冒頭のステップ0で自身の全フェーズを Task として登録し、`in_progress` / `completed` で状態遷移させながら進みます。これにより、フェーズのスキップ・実装の早すぎる着手・手順の取りこぼしを構造的に防ぎます（地の文の手順記述だけに頼りません）。Task ツールが使えない環境では地の文チェックリストへ自動的にフォールバックします。

### 基本的なワークフロー

#### 1. **タスク環境準備** `/task-init`
```bash
/task-init your-task-name
/task-init your-task-name 'https://example.com/issue/123'   # URL から内容を自動取得
```
- **機能**: 新しいタスクの環境準備と要件ヒアリング
- **用途**: プロジェクトの新機能開発や、課題対応の開始時
- **作成ファイル**: `.claude/tasks/{your-task-name}/`

コマンド実行後、`init.md`ファイルに要件を簡潔に入力してください。この段階では、まだ詳細な要件定義は不要です。

**URL を指定した場合**（第2引数）: 指定 URL（Backlog / GitHub / Jira / 一般 Web ページ等）から **本文とコメントを改変せず全文転記**し、添付ファイルがあればサブディレクトリ `attachments/` に保存します。`init.md` の末尾には別セクションとして **要約** を付与します。

- **取得方法**: 可能な限り **MCP を優先**し、利用できなければ **ブラウザ優先のフォールバック**（claude-in-chrome → chrome-devtools → Playwright → WebFetch）で取得します。取得手段が一つも利用できない場合は **エラー終了し、`init.md` は作成しません**。
- **URL のクォート**: URL は `?` `&` `#` 等の特殊文字を含むため、**シングルクォートで囲むことを推奨**します（例: `'https://...'`）。シングルクォートは内部を一切展開しないため最も安全です。
- **部分取得時**: 取得方式の制約で一部（添付・コメント等）が取得できない場合でも処理は続行し、取得できなかった項目を `init.md` 内に明記します。

#### 2. **要件定義作成** `/task-req`
```bash
/task-req your-task-name
/task-req your-task-name --team   # Agent Teams モード（市場リサーチ・影響分析を並行実施）
```
- **機能**: 入力された要件から要件定義書を作成
- **用途**: 曖昧な要求を構造化された要件に変換
- **入力ファイル**: `.claude/tasks/{your-task-name}/init.md`
- **作成ファイル**: `.claude/tasks/{your-task-name}/req.md`

要件定義ファイル `req.md` が作成されます。末尾の「要確認事項」セクションに、確認が必要な項目が一問一答可能な箇条書きで一覧化されます。各項目の直下にインデントした子要素（`  - 回答内容`）で回答を追記し、次の `/task-req-update` で本文へ反映できます。

#### 3. **要確認事項の反映** `/task-req-update`
```bash
/task-req-update your-task-name
/task-req-update your-task-name --team   # Agent Teams モード（返信反映・整理確定を並行実施）
```
- **機能**: 「要確認事項」へのユーザー回答を req.md 本文へ反映し、確定版へ整理
- **用途**: 要件定義書の要確認事項を解消し、詳細設計へ進める状態にする
- **入力ファイル**: `.claude/tasks/{your-task-name}/req.md`
- **更新ファイル**: 同 `req.md`（専用報告書は作成せず直接更新）

各「要確認事項」項目の直下にインデント子要素で回答が付いていれば「解決済み」とみなし、その内容を本文へ反映して当該項目を削除します。回答のない項目は「未解決」として残置します。全項目が解決すると「要確認事項」セクション自体が削除され、req.md は確定版になります。未解決が残る場合は件数が提示されるので、回答を追記して再実行してください（「回答→再実行」ループ）。

#### 4. **詳細設計** `/task-design`
```bash
/task-design your-task-name
/task-design your-task-name --team   # Agent Teams モード（データ設計・API設計・セキュリティ設計を並行実施）
```
- **機能**: 既存システムを分析し、詳細設計を作成
- **用途**: 要件定義後の技術的設計
- **作成ファイル**: `.claude/tasks/{your-task-name}/design.md`

詳細設計ファイル `design.md` が作成されます。内容を確認し、必要に応じて修正してください。

#### 5. **ToDoリストと工数見積もり作成** `/task-todo`
```bash
/task-todo your-task-name
/task-todo your-task-name --team   # Agent Teams モード（タスク分解・工数見積もりを並行実施）
```
- **機能**: 詳細設計に基づく実装作業のタスクを分解し、リスクの不確実性を考慮した工数見積もりを実施
- **用途**: 開発作業の具体的な計画立案と中級プログラマが手作業で実装する場合の工数算出（最少〜最大の範囲表示）
- **作成ファイル**: `.claude/tasks/{your-task-name}/todo.md`

ToDoリストと工数見積もりを統合したファイル `todo.md` が作成されます。各タスクの見積もり時間、リスク要因（不確実性レベル付き）、最少工数（楽観）・最大工数（悲観）の範囲見積もりを含みます。内容を確認し、必要に応じて修正してください。

#### 6. **開発実行** `/task-dev`
```bash
/task-dev your-task-name
/task-dev your-task-name --team   # Agent Teams モード（独立したタスクを並行実装）
```
- **機能**: ToDoリストに基づく段階的な実装と開発完了報告書の作成
- **用途**: 実際の開発作業の実行
- **作成ファイル**: `.claude/tasks/{your-task-name}/dev-result.md`
- **特徴**:
  - todo.mdのタスクを自動的にdev-result.mdにチェックリスト形式でコピー
  - 各タスク完了時にチェックマーク [x] を付けて進捗を可視化

開発完了後、チェックリスト付きの進捗状況、実装概要、変更ファイル一覧、技術的詳細を含む報告書 `dev-result.md` が作成されます。

#### 7. **コードレビュー** `/task-review`
```bash
/task-review your-task-name
/task-review your-task-name --team   # Agent Teams モード（要件整合性・コード品質・セキュリティを並行レビュー）
```
- **機能**: 要件定義・設計書・ToDoリストと照合し、実装コードの品質を検証
- **用途**: 開発完了後のコードレビュー
- **入力ファイル**: req.md, design.md, todo.md, dev-result.md + 実装コード
- **作成ファイル**: `.claude/tasks/{your-task-name}/review.md`

レビュー報告書 `review.md` が作成されます。総合判定（修正不要/修正推奨/修正必須）、要件・設計との整合性、コード品質チェック、修正方針が含まれます。

#### 8. **修正実行** `/task-fix`
```bash
/task-fix your-task-name
/task-fix your-task-name --team   # Agent Teams モード（独立した修正箇所を並行修正）
```
- **機能**: レビュー指摘に基づいてコードを修正
- **用途**: コードレビュー後の修正作業
- **入力ファイル**: review.md, design.md
- **作成ファイル**: `.claude/tasks/{your-task-name}/fix-result.md`

修正報告書 `fix-result.md` が作成されます。指摘事項ごとの対応内容、変更ファイル一覧、動作確認結果が含まれます。

#### 9. **手動検証** `/task-verify`
```bash
/task-verify your-task-name
/task-verify your-task-name --team   # Agent Teams モード（正常系・異常系・非機能の検証設計を並行実施）
```
- **機能**: 開発成果物に対する手動検証手順書を生成
- **用途**: 開発・修正完了後の手動検証
- **入力ファイル**: req.md, design.md, dev-result.md（+ review.md, fix-result.md が存在する場合）
- **作成ファイル**: `.claude/tasks/{your-task-name}/verify.md`

検証手順書 `verify.md` が作成されます。チェックボックス形式の手順で、コピペ可能なコマンドや具体的な期待結果が含まれます。簡単なQuick Winから始まる構成で、検証を始めやすくしています。

### ファイル構造

各タスクの出力は以下の構造で管理されます：
```
.claude/tasks/{your-task-name}/
├── init.md         # 要件ヒアリング（URL 指定時は取得内容を転記）
├── attachments/    # URL から取得した添付ファイル（添付がある場合のみ）
├── req.md          # 要件定義
├── design.md       # 詳細設計
├── todo.md         # ToDoリストと工数見積もり
├── dev-result.md   # 開発完了報告書
├── review.md       # コードレビュー報告書
├── fix-result.md   # 修正完了報告書
└── verify.md       # 手動検証手順書
```

**注意**: タスクファイルは常に**プロジェクトルート**配下の `.claude/tasks/` に作成されます（`~/.claude/tasks/` ではありません）。各スキルは実行時に `pwd` でプロジェクトルートの絶対パスを取得し、すべてのファイル操作に使用します。

## Agent Teams オプション

task-init を除く全スキルは `--team` オプションに対応しています。このオプションを使うと、Claude Code の `Agent` ツールで複数のチームメイトを spawn し、並行して作業させます。`--team` を付けるだけで並列実行は起動します（環境変数の事前設定は不要）。トークン消費が増えますので、必要なときに限って `--team` を指定してください。

### （任意）SendMessage ライブ協調の有効化

チームメイト間の**ライブ通信**（`SendMessage`）を使いたい場合のみ、`~/.claude/settings.json` に以下を追加してください。これは **任意設定** であり、未設定でも `--team` による並列実行は問題なく起動します（`SendMessage` が使えない場合は各チームメイトの戻り値で成果を収集します）。

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

> 環境変数 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` がゲートするのは `SendMessage`（teammate 間ライブ通信）のみです。`Agent` による spawn と `TaskCreate` / `TaskUpdate` による共有タスク管理はこの変数なしでも動作します。

### 使用例

```bash
/task-req my-task --team          # 市場リサーチ・影響分析を並行実施
/task-req-update my-task --team   # 返信反映・整理確定を並行実施
/task-design my-task --team   # データ設計・API設計・セキュリティ設計を並行実施
/task-todo my-task --team     # タスク分解・工数見積もりを並行実施
/task-dev my-task --team      # 独立したタスクを並行実装
/task-review my-task --team   # 要件整合性・コード品質・セキュリティを並行レビュー
/task-fix my-task --team      # 独立した修正箇所を並行修正
/task-verify my-task --team   # 正常系・異常系・非機能の検証設計を並行実施
```

### コストに関する注意

Agent Teams はトークン消費が大幅に増加します（通常の2〜5倍）。必要な場合にのみ使用してください。

## 整合性チェック

このスキル集は include 機構を持たないため、Agent Teams 共通ブロックやフォールバック文言などの定型文が複数のファイルに重複しています。`scripts/check_consistency.py`（Python 3 標準ライブラリのみ）は、これらの重複箇所のズレを機械的に検出します。

```bash
python3 scripts/check_consistency.py        # 不一致のみ表示
python3 scripts/check_consistency.py -v     # 全6検査の結果を表示
bash scripts/test/run_consistency_tests.sh  # 検査自体の回帰テスト
```

検査内容は frontmatter / Agent Teams 共通ブロック / フォールバック文言 / メタ情報フォーマット / 環境変数 JSON / テンプレート参照の6種です。終了コードは `0`=整合 / `1`=不整合 / `2`=実行エラー。

- **ローカルフック**: `git config core.hooksPath scripts/hooks` で pre-commit フックを有効化すると、対象ファイル変更時に自動でチェックが走ります（対象外の変更は高速スキップ、緊急時は `git commit --no-verify` でバイパス可能）。整合性チェックはこのローカルフックで担保します（GitHub Actions による CI は使用していません）。

## ライセンス

GPL-3.0 License

## 作者

Yuki Kokubo
