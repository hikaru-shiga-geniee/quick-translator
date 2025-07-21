#!/usr/bin/env python3
"""
Gemini APIを使用した高速翻訳ツール
"""

import os
import sys
import time
import json
import subprocess
import tempfile
from typing import Optional, Tuple


class QuickTranslator:
    def __init__(self):
        self.program_start_time = time.time()
        self.api_key = self._get_api_key()
        
    def _get_api_key(self) -> Optional[str]:
        """環境変数からAPIキーを取得"""
        # ログインシェルを経由して環境変数を取得
        try:
            result = subprocess.run(
                [os.environ.get('SHELL', '/bin/sh'), '-l', '-c', 'echo $GEMINI_API_KEY'],
                capture_output=True,
                text=True,
                timeout=10
            )
            api_key = result.stdout.strip()
            return api_key if api_key else None
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return os.environ.get('GEMINI_API_KEY')
    
    def _escape_for_dialog(self, text: str) -> str:
        """osascriptのダイアログ用にテキストをエスケープ"""
        # ダブルクォートをエスケープし、改行を\\nに変換
        escaped = text.replace('"', '\\"').replace('\n', '\\n')
        return escaped
    
    def _show_dialog(self, message: str, title: str = "翻訳結果") -> None:
        """macOSのダイアログを表示"""
        escaped_message = self._escape_for_dialog(message)
        script = f'display dialog "{escaped_message}" buttons {{"OK"}} default button 1 with title "{title}"'
        try:
            subprocess.run(['osascript', '-e', script], check=False)
        except subprocess.SubprocessError:
            print(f"{title}: {message}")
    
    def _copy_to_clipboard(self, text: str) -> None:
        """テキストをクリップボードにコピー"""
        try:
            subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
        except subprocess.SubprocessError:
            pass  # クリップボードのコピーに失敗しても継続
    
    def translate_with_api(self, text: str) -> Tuple[str, float]:
        """Gemini APIを使ってテキストを翻訳"""
        if not self.api_key:
            raise ValueError("エラー: 環境変数GEMINI_API_KEYが設定されていません")
        
        # プロンプトの作成
        system_prompt = """You are a translator. Your task:
- Japanese text → Translate to English
- Non-Japanese text → Translate to Japanese
- Output ONLY the translation, no explanations"""
        
        # JSONデータの準備
        json_data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{system_prompt}\n\nText to translate: {text}"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1000,
                "topP": 0.1,
                "topK": 1
            }
        }
        
        # 翻訳時間の計測開始
        start_time = time.time()
        
        try:
            # JSONデータを一時ファイルに書き込み
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(json_data, temp_file, ensure_ascii=False)
                temp_file_path = temp_file.name
            
            try:
                # Gemini APIのエンドポイント
                # gemini-1.5-flashまたはgemini-1.5-flash-latestを使用
                api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"
                
                # curlでAPIを呼び出す（2つの方法を提供）
                
                # 方法1: APIキーをURLパラメータとして使用
                curl_cmd_url_param = [
                    'curl', '-s',
                    '-H', 'Content-Type: application/json',
                    '-X', 'POST',
                    '-d', f'@{temp_file_path}',
                    f'{api_url}?key={self.api_key}'
                ]
                
                # 方法2: APIキーをヘッダーとして使用（よりセキュア）
                curl_cmd_header = [
                    'curl', '-s',
                    '-H', 'Content-Type: application/json',
                    '-H', f'x-goog-api-key: {self.api_key}',
                    '-X', 'POST',
                    '-d', f'@{temp_file_path}',
                    api_url
                ]
                
                # ヘッダー方式を優先的に使用
                result = subprocess.run(
                    curl_cmd_header,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # 翻訳時間の計測終了
                end_time = time.time()
                elapsed_time = end_time - start_time
                
                # curlのエラーチェック
                if result.returncode != 0:
                    # ヘッダー方式が失敗した場合、URLパラメータ方式を試す
                    result = subprocess.run(
                        curl_cmd_url_param,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode != 0:
                        error_msg = f"curlエラー: 接続に失敗しました (exit code: {result.returncode})"
                        if result.stderr:
                            error_msg += f"\n詳細: {result.stderr}"
                        raise ValueError(error_msg)
                
                response_data = result.stdout
                
            finally:
                # 一時ファイルを削除
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass
            
            # JSONレスポンスをパース
            try:
                response_json = json.loads(response_data)
            except json.JSONDecodeError:
                raise ValueError(f"エラー: 無効なJSONレスポンス\n{response_data}")
            
            # APIエラーチェック
            if 'error' in response_json:
                error_msg = response_json['error'].get('message', '不明なエラー')
                raise ValueError(f"APIエラー: {error_msg}")
            
            # 翻訳結果の抽出
            if ('candidates' not in response_json or 
                not response_json['candidates'] or
                'content' not in response_json['candidates'][0] or
                'parts' not in response_json['candidates'][0]['content'] or
                not response_json['candidates'][0]['content']['parts']):
                raise ValueError("エラー: 翻訳結果が取得できませんでした")
            
            translated_text = response_json['candidates'][0]['content']['parts'][0]['text']
            
            if not translated_text:
                raise ValueError("エラー: 翻訳結果が空でした")
            
            # 前後の空白を削除
            translated_text = translated_text.strip()
            
            return translated_text, elapsed_time
            
        except subprocess.TimeoutExpired:
            end_time = time.time()
            elapsed_time = end_time - start_time
            error_msg = "タイムアウトエラー: API呼び出しがタイムアウトしました"
            raise ValueError(error_msg)
        except subprocess.SubprocessError as e:
            end_time = time.time()
            elapsed_time = end_time - start_time
            error_msg = f"プロセスエラー: {str(e)}"
            raise ValueError(error_msg)
        except Exception as e:
            end_time = time.time()
            elapsed_time = end_time - start_time
            error_msg = f"予期しないエラー: {str(e)}"
            raise ValueError(error_msg)
    
    def run(self, input_text: str) -> bool:
        """メイン処理を実行"""
        if not input_text:
            total_time = time.time() - self.program_start_time
            self._show_dialog("テキストが選択されていません", "エラー")
            return False
        
        try:
            # 翻訳実行
            translated_text, elapsed_time = self.translate_with_api(input_text)
            
            # クリップボードにコピー
            self._copy_to_clipboard(translated_text)
            
            # プログラム全体の実行時間を計算
            total_time = time.time() - self.program_start_time
            
            # 翻訳時間をフォーマット（小数点第2位まで）
            formatted_api_time = f"{elapsed_time:.2f}"
            formatted_total_time = f"{total_time:.2f}"
            
            # 結果を表示
            time_info = f"\n\n翻訳API時間: {formatted_api_time}秒\n全体実行時間: {formatted_total_time}秒"
            message = f"{translated_text}{time_info}"
            self._show_dialog(message, "翻訳結果")
            
            # 結果を出力
            print(translated_text)
            return True
            
        except ValueError as e:
            total_time = time.time() - self.program_start_time
            self._show_dialog(str(e), "エラー")
            return False
        except Exception as e:
            total_time = time.time() - self.program_start_time
            error_msg = f"予期しないエラーが発生しました: {str(e)}"
            self._show_dialog(error_msg, "エラー")
            return False


def main():
    """メイン関数"""
    # 入力テキストを取得
    input_text = ""
    
    # 標準入力からテキストを読み取る
    if not sys.stdin.isatty():
        input_text = sys.stdin.read()
    elif len(sys.argv) > 1:
        input_text = " ".join(sys.argv[1:])
    
    # 先頭と末尾の空白を削除
    input_text = input_text.strip()
    
    # 翻訳器を初期化して実行
    translator = QuickTranslator()
    success = translator.run(input_text)
    
    # 終了コードを設定
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
