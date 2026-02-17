# Claude Code Task Commands

Claude Codeでタスクベースの開発を行うためのカスタムスラッシュコマンド集です。要件定義→詳細設計→ToDoリスト→実装を段階的に進めることで、品質の高いソフトウェア開発を支援します。

## モデル最適化

各コマンドは用途に応じて最適なモデルを自動選択し、コストと精度のバランスを最適化します：

| コマンド | モデル | 理由 |
|---------|--------|------|
| task-init | **Haiku 4.5** | ファイル作成のみ、コスト削減 |
| task-req | **Opus 4.6** | 高精度な要件分析 |
| task-design | **Opus 4.6** | 高精度な設計 |
| task-todo | **Opus 4.6** | 高精度な計画・見積もり |
| task-develop | **Opus 4.6** | 高精度な実装作業 |

## Serena MCP対応

Serena MCPが利用可能な環境では、自動的に検出して優先的に活用し、分析・検証・実装の精度と効率を向上させます。Serena MCPが利用できない環境でも、従来の方法で問題なく動作します。

## インストール

1. このリポジトリをクローンします：
```bash
git clone https://github.com/tombolo-jp/claude-code-task-commands.git
```

2. Claude Codeのコマンドディレクトリにファイルをコピーします：
```bash
cp claude-code-task-commands/*.md ~/.claude/commands/
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
- **作成ファイル**: `.claude/tasks/{your-task-name}/requirements.md`
- **Serena MCP**: 要件分析と文書生成で活用

要件定義ファイル `requirements.md` が作成されます。必要に応じて修正してください。

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

#### 5. **開発実行** `/task-develop`
```bash
/task-develop your-task-name
```
- **機能**: ToDoリストに基づく段階的な実装と開発完了報告書の作成
- **用途**: 実際の開発作業の実行
- **作成ファイル**: `.claude/tasks/{your-task-name}/develop-result.md`
- **Serena MCP**: コード生成・実装・テスト・検証で活用
- **特徴**:
  - todo.mdのタスクを自動的にdevelop-result.mdにチェックリスト形式でコピー
  - 各タスク完了時にチェックマーク [x] を付けて進捗を可視化
  - 2種類の専門サブエージェントが連携して開発を進行：
    - **develop**: 実装担当エージェント
    - **confirm**: 設計書との整合性確認エージェント

開発完了後、チェックリスト付きの進捗状況、実装概要、変更ファイル一覧、技術的詳細を含む報告書 `develop-result.md` が作成されます。

### ファイル構造

各タスクは以下の構造で管理されます：
```
.claude/tasks/{your-task-name}/
├── init.md         # 要件ヒアリング
├── requirements.md  # 要件定義
├── design.md       # 詳細設計
├── todo.md         # ToDoリストと工数見積もり
└── develop-result.md # 開発完了報告書
```

## ライセンス

GPL-3.0 License

## 作者

Yuki Kokubo
