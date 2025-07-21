### テストカバレージ

#### OpenAI API版テスト (`tests/test_openai.py`)
- **QuickTranslatorクラス**: 全メソッドをテスト
- **環境変数取得**: ログインシェルと環境変数の両方をテスト
- **API呼び出し**: 成功・失敗・エラー各種をテスト
- **エラーハンドリング**: 全エラーパターンをテスト
- **macOS連携**: ダイアログ・クリップボード機能をテスト
- **メイン関数**: 標準入力・引数・空入力をテスト

#### Gemini API版テスト (`tests/test_gemini.py`)
- **QuickTranslatorクラス**: 全メソッドをテスト
- **環境変数取得**: ログインシェルと環境変数の両方をテスト
- **API呼び出し**: 成功・失敗・エラー各種をテスト
- **複数認証方式**: ヘッダー認証とURLパラメータ認証のテスト
- **エラーハンドリング**: 全エラーパターンをテスト
- **macOS連携**: ダイアログ・クリップボード機能をテスト
- **メイン関数**: 標準入力・引数・空入力をテスト

#### plamo-translate版テスト (`tests/test_plamo.py`)
- **PlamoTranslatorクラス**: 全メソッドをテスト
- **コマンドパス検索**: シェル別（fish/bash/zsh）・共通パス検索をテスト
- **PATH取得**: ログインシェル経由のPATH取得をテスト
- **plamo-translate呼び出し**: 成功・失敗・タイムアウト各種をテスト
- **エラーハンドリング**: コマンド未発見・実行エラーをテスト
- **macOS連携**: ダイアログ・クリップボード機能をテスト
- **メイン関数**: 標準入力・引数・空入力をテスト

#### 全テスト実行
```fish
# 全テスト実行
uv run pytest

# OpenAI版のみ
uv run pytest tests/test_openai.py

# Gemini版のみ
uv run pytest tests/test_gemini.py

# plamo版のみ
uv run pytest tests/test_plamo.py
```
