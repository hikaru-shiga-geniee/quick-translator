# Quick Translator

日本語⇔英語の翻訳を行うPythonスクリプト集です。

## 翻訳エンジン

このプロジェクトでは3つの翻訳エンジンを提供します：

- **`translate_openai.py`**: OpenAI API（GPT-4.1-nano）を使用した翻訳
- **`translate_gemini.py`**: Google Gemini API（Gemini 2.5 Flash Lite）を使用した翻訳  
- **`translate_plamo.py`**: plamo-translateを使用したローカル翻訳

## 動作環境

- Python 3.9, 3.10, 3.11, 3.12, 3.13
- macOS (osascriptとpbcopyを使用)
- curl コマンド（macOSには標準でインストールされています）
- 標準ライブラリのみ使用（外部依存なし）

## セットアップ

### 1. 翻訳エンジンの設定

#### OpenAI API版 (`translate_openai.py`)

fishシェルの場合、`~/.config/fish/config.fish`に以下を追加：

```fish
set -gx OPENAI_API_KEY "sk-your-api-key-here"
```

bashの場合、`~/.bashrc`または`~/.bash_profile`に以下を追加：

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

#### Gemini API版 (`translate_gemini.py`)

fishシェルの場合、`~/.config/fish/config.fish`に以下を追加：

```fish
set -gx GEMINI_API_KEY "your-gemini-api-key-here"
```

bashの場合、`~/.bashrc`または`~/.bash_profile`に以下を追加：

```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

#### plamo-translate版 (`translate_plamo.py`)

[plamo-translate](https://github.com/pfnet/plamo-translate)をインストール：

```fish
pip install plamo-translate
```

または、uvを使用：

```fish
uv tool install -p 3.12 plamo-translate
```

### 2. macOSクイックアクションの設定

これらのスクリプトは選択したテキストを翻訳するクイックアクションとして使用できます。

#### Automatorでのセットアップ手順

1. **Automatorを開く**
   - アプリケーション > Automator を起動

2. **新規クイックアクション作成**
   - 「新規書類」→「クイックアクション」を選択

3. **ワークフローの設定**
   - 上部の設定で以下を選択：
     - 「ワークフローが受け取る対象」: **テキスト**
     - 「検索対象」: **すべてのアプリケーション**

4. **Run Shell Scriptアクション追加**
   - 左側のアクション一覧から「シェルスクリプトを実行」をドラッグ＆ドロップ
   - 以下の設定に変更：
     - 「シェル」: **/usr/bin/python3**
     - 「入力の引き渡し方法」: **標準入力として**

5. **Pythonスクリプト内容をコピペ**
   - 使用したい翻訳エンジンのスクリプト内容（`translate_openai.py`、`translate_gemini.py`、または`translate_plamo.py`）を全てコピー＆ペースト

6. **保存**
   - `⌘+S` で保存
   - 名前: 「Quick Translator (OpenAI)」、「Quick Translator (Gemini)」、または「Quick Translator (Plamo)」など

## 使用方法

### クイックアクションで翻訳（推奨）

1. **テキストを選択**
   - ブラウザ、エディタ、PDFなど任意のアプリでテキストを選択

2. **右クリック**
   - 選択したテキストを右クリック

3. **クイックアクション実行**
   - コンテキストメニューから作成したクイックアクションを選択
   - または、**サービス** から選択

4. **結果確認**
   - 翻訳結果がダイアログで表示
   - 同時にクリップボードにもコピー



## 機能

### 共通機能
- **自動言語判定**: 日本語テキストは英語に、それ以外は日本語に翻訳
- **クリップボード連携**: 翻訳結果を自動でクリップボードにコピー
- **ダイアログ表示**: macOSのダイアログで翻訳結果と実行時間を表示
- **時間測定**: 翻訳処理時間とプログラム全体の実行時間を表示
- **エラーハンドリング**: 包括的なエラー処理とユーザーフレンドリーなメッセージ

### 翻訳エンジン別特徴

#### OpenAI API版 (`translate_openai.py`)
- **高品質翻訳**: GPT-4.1-nanoによる高精度翻訳
- **インターネット必須**: API通信が必要
- **従量課金**: 使用量に応じた料金
- **高速**: 通常1-3秒で応答

#### Gemini API版 (`translate_gemini.py`)
- **高品質翻訳**: Gemini 2.5 Flash Liteによる高精度翻訳
- **インターネット必須**: API通信が必要
- **従量課金**: 使用量に応じた料金
- **高速**: 通常1-3秒で応答

#### plamo-translate版 (`translate_plamo.py`)
- **ローカル処理**: インターネット不要で動作
- **無料**: ランニングコスト無し
- **プライバシー**: テキストが外部に送信されない
- **自動パス検出**: 複数のシェル環境（fish、bash、zsh）に対応した plamo-translate 検索
- **処理時間**: 初回起動時は時間がかかる場合があります
  - 事前に`plamo-translate server`を起動することでモデルロード時間を短縮可能

## 性能比較・ベンチマーク

### ベンチマークツール

`translation_benchmark.py`を使用して各翻訳エンジンの性能を比較できます：

```fish
python3 translation_benchmark.py
```

このツールは以下のテストを実行します：

- **OpenAI モデル**: gpt-4.1-nano, gpt-4.1-mini, o4-mini
- **Gemini モデル**: gemini-2.0-flash-lite, gemini-2.5-flash-lite-preview-06-17, gemini-2.5-flash
- **Plamo**: plamo-translate（サーバー事前起動なし/あり）

各モデルで4種類の翻訳（短い日本語→英語、長い日本語→英語、短い英語→日本語、長い英語→日本語）を10回実行し、以下の統計を表示：

- 成功率
- 平均応答時間
- 最小/最大応答時間
- 標準偏差

## テスト実行

### 単一バージョンでのテスト

```fish
uv run pytest
```

### 複数バージョンでのテスト

Python 3.9, 3.10, 3.11, 3.12, 3.13 すべてでテストを実行：

```fish
python3 test_all_versions.py
```

または個別にバージョンを指定：

```fish
uv run --python 3.9 pytest
uv run --python 3.10 pytest
uv run --python 3.11 pytest
uv run --python 3.12 pytest
uv run --python 3.13 pytest
```

## 翻訳対象

- 日本語テキスト → 英語に翻訳
- 英語その他の言語 → 日本語に翻訳

翻訳には説明や注釈は含まれず、翻訳結果のみが出力されます。

## プロジェクト構成

```
quick-translator/
├── translate_openai.py      # OpenAI API翻訳スクリプト
├── translate_gemini.py      # Gemini API翻訳スクリプト
├── translate_plamo.py       # plamo-translate翻訳スクリプト
├── translation_benchmark.py # 性能比較ベンチマークツール
├── test_all_versions.py     # 全Pythonバージョンテスト実行
├── tests/
│   ├── TEST.MD              # テストの詳細
│   ├── test_openai.py       # OpenAI版テスト
│   ├── test_gemini.py       # Gemini版テスト
│   ├── test_plamo.py        # plamo版テスト
│   └── conftest.py          # テスト共通設定
├── pyproject.toml           # プロジェクト設定
└── README.md                # このファイル
```

## 開発者向け情報

### 依存関係
- 実行時: 標準ライブラリのみ（外部依存なし）
- 開発時: pytest, pytest-mock, ruff, ty

### コード品質
- 型ヒント完全対応
- 包括的なテストカバレージ
- Ruffによるリンティング
- 複数Pythonバージョン対応（3.9-3.13）
