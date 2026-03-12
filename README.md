# Claude Code Task Commands

Claude Codeでタスクベースの開発を行うためのカスタムスキル集です。要件定義→詳細設計→ToDoリスト→実装→レビュー→修正→検証を段階的に進めることで、品質の高いソフトウェア開発を支援します。

## コンテキストフォーク

各スキルは `context: fork` を使用して独立したサブエージェントコンテキストで実行されます。これにより：

- 前のコマンドの実行履歴がコンテキストウィンドウを圧迫しない
- 各コマンドがフレッシュな状態で実行され、精度が安定する
- 実行結果はサマリーとしてメイン会話に返却される
- ファイルの読み書きやCLAUDE.md参照は従来通り正常に動作

## モデル最適化

各スキルは用途に応じて最適なモデルを自動選択し、コストと精度のバランスを最適化します：

| スキル | モデル | エイリアス | 理由 |
|--------|--------|-----------|------|
| task-init | **Haiku** | `haiku` | ファイル作成のみ、コスト削減 |
| task-req | **Opus** | `opus` | 高精度な要件分析 |
| task-design | **Opus** | `opus` | 高精度な設計 |
| task-todo | **Opus** | `opus` | 高精度な計画・見積もり |
| task-dev | **Sonnet** | `sonnet` | コストと精度のバランスを重視した実装 |
| task-review | **Opus** | `opus` | 高精度なコードレビュー |
| task-fix | **Sonnet** | `sonnet` | コストと精度のバランスを重視した修正 |
| task-verify | **Opus** | `opus` | 高精度な検証手順生成 |

モデルエイリアス（`haiku`, `sonnet`, `opus`）を使用しているため、Anthropicがモデルを更新した際に自動的に最新版に解決されます。

## モデル確認の仕組み

各スキルは、出力する報告書の末尾に「メタ情報」セクションを含めます。`context: fork` で起動されたサブエージェントが自己申告する形で、実際に使用されたモデル名と実行日時が記録されます。

```markdown
## メタ情報
- 実行モデル: Claude Opus 4.6
- 実行日時: 2026-03-12 10:30:00
- コンテキスト: fork
```

## Serena MCP対応

Serena MCPが利用可能な環境では、自動的に検出して優先的に活用し、分析・検証・実装の精度と効率を向上させます。Serena MCPが利用できない環境でも、従来の方法で問題なく動作します。

## インストール

1. このリポジトリをクローンします：
```bash
git clone https://github.com/tombolo-jp/claude-code-task-commands.git
```

2. Claude Codeのスキルディレクトリにコピーします：
```bash
cp -r claude-code-task-commands/skills/* ~/.claude/skills/
```

## 使用方法

### 基本的なワークフロー

#### 1. **タスク環境準備** `/task-init`
```bash
/task-init your-task-name
```
- **機能**: 新しいタスクの環境準備と要件ヒアリング
- **用途**: プロジェクトの新機能開発や、課題対応の開始時
- **作成ファイル**: `.claude/tasks/{your-task-name}/`ディレクトリ構造

コマンド実行後、`init.md`ファイルに要件を簡潔に入力してください。この段階では、まだ詳細な要件定義は不要です。

#### 2. **要件定義作成** `/task-req`
```bash
/task-req your-task-name
```
- **機能**: 入力された要件から要件定義書を作成
- **用途**: 曖昧な要求を構造化された要件に変換
- **入力ファイル**: `.claude/tasks/{your-task-name}/init.md`
- **作成ファイル**: `.claude/tasks/{your-task-name}/req.md`
- **Serena MCP**: 要件分析と文書生成で活用

要件定義ファイル `req.md` が作成されます。必要に応じて修正してください。

#### 3. **詳細設計** `/task-design`
```bash
/task-design your-task-name
```
- **機能**: 既存システムを分析し、詳細設計を作成
- **用途**: 要件定義後の技術的設計
- **作成ファイル**: `.claude/tasks/{your-task-name}/design.md`
- **Serena MCP**: 設計文書の作成・分析・検証で活用

詳細設計ファイル `design.md` が作成されます。内容を確認し、必要に応じて修正してください。

#### 4. **ToDoリストと工数見積もり作成** `/task-todo`
```bash
/task-todo your-task-name
```
- **機能**: 詳細設計に基づく実装作業のタスクを分解し、リスクの不確実性を考慮した工数見積もりを実施
- **用途**: 開発作業の具体的な計画立案と中級プログラマが手作業で実装する場合の工数算出（最少〜最大の範囲表示）
- **作成ファイル**: `.claude/tasks/{your-task-name}/todo.md`
- **Serena MCP**: タスク分析・工数見積もり・文書生成で活用

ToDoリストと工数見積もりを統合したファイル `todo.md` が作成されます。各タスクの見積もり時間、リスク要因（不確実性レベル付き）、最少工数（楽観）・最大工数（悲観）の範囲見積もりを含みます。内容を確認し、必要に応じて修正してください。

#### 5. **開発実行** `/task-dev`
```bash
/task-dev your-task-name
```
- **機能**: ToDoリストに基づく段階的な実装と開発完了報告書の作成
- **用途**: 実際の開発作業の実行
- **作成ファイル**: `.claude/tasks/{your-task-name}/dev-result.md`
- **Serena MCP**: コード生成・実装・テスト・検証で活用
- **特徴**:
  - todo.mdのタスクを自動的にdev-result.mdにチェックリスト形式でコピー
  - 各タスク完了時にチェックマーク [x] を付けて進捗を可視化

開発完了後、チェックリスト付きの進捗状況、実装概要、変更ファイル一覧、技術的詳細を含む報告書 `dev-result.md` が作成されます。

#### 6. **コードレビュー** `/task-review`
```bash
/task-review your-task-name
```
- **機能**: 要件定義・設計書・ToDoリストと照合し、実装コードの品質を検証
- **用途**: 開発完了後のコードレビュー
- **入力ファイル**: req.md, design.md, todo.md, dev-result.md + 実装コード
- **作成ファイル**: `.claude/tasks/{your-task-name}/review.md`
- **Serena MCP**: コード分析・レビューで活用

レビュー報告書 `review.md` が作成されます。総合判定（修正不要/修正推奨/修正必須）、要件・設計との整合性、コード品質チェック、修正方針が含まれます。

#### 7. **修正実行** `/task-fix`
```bash
/task-fix your-task-name
```
- **機能**: レビュー指摘に基づいてコードを修正
- **用途**: コードレビュー後の修正作業
- **入力ファイル**: review.md, design.md
- **作成ファイル**: `.claude/tasks/{your-task-name}/fix-result.md`
- **Serena MCP**: コード修正・検証で活用

修正報告書 `fix-result.md` が作成されます。指摘事項ごとの対応内容、変更ファイル一覧、動作確認結果が含まれます。

#### 8. **手動検証** `/task-verify`
```bash
/task-verify your-task-name
```
- **機能**: 開発成果物に対する手動検証手順書を生成
- **用途**: 開発・修正完了後の手動検証
- **入力ファイル**: req.md, design.md, dev-result.md（+ review.md, fix-result.md が存在する場合）
- **作成ファイル**: `.claude/tasks/{your-task-name}/verify.md`
- **Serena MCP**: コード分析・検証手順生成で活用

検証手順書 `verify.md` が作成されます。チェックボックス形式の手順で、コピペ可能なコマンドや具体的な期待結果が含まれます。簡単なQuick Winから始まる構成で、検証を始めやすくしています。

### ファイル構造

スキルのディレクトリ構造：
```
skills/
├── task-init/
│   └── SKILL.md
├── task-req/
│   └── SKILL.md
├── task-design/
│   └── SKILL.md
├── task-todo/
│   ├── SKILL.md
│   └── templates/
│       └── todo-template.md
├── task-dev/
│   ├── SKILL.md
│   └── templates/
│       └── dev-result-template.md
├── task-review/
│   ├── SKILL.md
│   └── templates/
│       └── review-template.md
├── task-fix/
│   ├── SKILL.md
│   └── templates/
│       └── fix-result-template.md
└── task-verify/
    ├── SKILL.md
    └── templates/
        └── verify-template.md
```

各タスクの出力は以下の構造で管理されます：
```
.claude/tasks/{your-task-name}/
├── init.md         # 要件ヒアリング
├── req.md  # 要件定義
├── design.md       # 詳細設計
├── todo.md         # ToDoリストと工数見積もり
├── dev-result.md   # 開発完了報告書
├── review.md       # コードレビュー報告書
├── fix-result.md   # 修正完了報告書
└── verify.md       # 手動検証手順書
```

## ライセンス

GPL-3.0 License

## 作者

Yuki Kokubo
