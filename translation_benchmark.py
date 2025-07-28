#!/usr/bin/env python3
"""
翻訳モデルの性能比較テストプログラム
各モデルで4種類の翻訳を10回実行し、時間を計測する
"""

import os
import sys
import time
import json
import subprocess
import tempfile
import argparse
from typing import Dict, List, Tuple, Optional
import statistics

# テストケース
TEST_CASES = {
    "short_jp_to_en": {
        "text": "こんにちは、今日はいい天気ですね。",
        "name": "短い日本語→英語"
    },
    "long_jp_to_en": {
        "text": "日本の伝統的な茶道は、単なる飲み物を楽しむ行為を超えて、精神的な修練と美的感覚を追求する総合芸術です。茶室における一期一会の精神は、その瞬間の出会いを大切にし、主人と客が心を通わせる貴重な時間を演出します。四季折々の道具や花、掛け軸などを通じて、日本人の美意識と自然観が表現されています。",
        "name": "長い日本語→英語"
    },
    "short_en_to_jp": {
        "text": "Hello, how are you doing today?",
        "name": "短い英語→日本語"
    },
    "long_en_to_jp": {
        "text": "Artificial intelligence has rapidly evolved in recent years, transforming various industries and reshaping how we interact with technology. From natural language processing to computer vision, AI systems are becoming increasingly sophisticated in their ability to understand and respond to human needs. This technological revolution promises both exciting opportunities and complex challenges that society must address thoughtfully.",
        "name": "長い英語→日本語"
    }
}

# モデル設定
MODELS = {
    "openai": [
        {"name": "gpt-4.1-nano", "model": "gpt-4.1-nano"},
        {"name": "gpt-4.1-mini", "model": "gpt-4.1-mini"},
        {"name": "o4-mini", "model": "o4-mini"}
    ],
    "gemini": [
        {"name": "gemini-2.0-flash-lite", "model": "gemini-2.0-flash-lite"},
        {"name": "gemini-2.5-flash-lite", "model": "gemini-2.5-flash-lite"},
        {"name": "gemini-2.5-flash", "model": "gemini-2.5-flash"}
    ],
    "plamo": [
        {"name": "plamo-translate", "model": "plamo-translate"}
    ]
}


class TranslationBenchmark:
    def __init__(self):
        self.openai_key = self._get_api_key("OPENAI_API_KEY")
        self.gemini_key = self._get_api_key("GEMINI_API_KEY")
        self.results = {}
        
    def _get_api_key(self, env_name: str) -> Optional[str]:
        """環境変数からAPIキーを取得"""
        try:
            result = subprocess.run(
                [os.environ.get("SHELL", "/bin/sh"), "-l", "-c", f"echo ${env_name}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            api_key = result.stdout.strip()
            return api_key if api_key else os.environ.get(env_name)
        except:
            return os.environ.get(env_name)
    
    def _translate_openai(self, text: str, model: str) -> Tuple[Optional[str], float]:
        """OpenAI APIで翻訳を実行"""
        if not self.openai_key:
            return None, 0.0
            
        json_data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a translator. Your task:\n- Japanese text → Translate to English\n- Non-Japanese text → Translate to Japanese\n- Output ONLY the translation, no explanations"
                },
                {"role": "user", "content": text}
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        start_time = time.time()
        
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
                json.dump(json_data, temp_file, ensure_ascii=False)
                temp_file_path = temp_file.name
            
            try:
                curl_cmd = [
                    "curl", "-s",
                    "-H", f"Authorization: Bearer {self.openai_key}",
                    "-H", "Content-Type: application/json",
                    "-d", f"@{temp_file_path}",
                    "https://api.openai.com/v1/chat/completions"
                ]
                
                result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
                elapsed_time = time.time() - start_time
                
                if result.returncode != 0:
                    return None, elapsed_time
                    
                response_json = json.loads(result.stdout)
                
                if "error" in response_json:
                    return None, elapsed_time
                    
                if "choices" in response_json and response_json["choices"]:
                    translated_text = response_json["choices"][0]["message"]["content"].strip()
                    return translated_text, elapsed_time
                    
                return None, elapsed_time
                
            finally:
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            elapsed_time = time.time() - start_time
            return None, elapsed_time
    
    def _translate_gemini(self, text: str, model: str) -> Tuple[Optional[str], float]:
        """Gemini APIで翻訳を実行"""
        if not self.gemini_key:
            return None, 0.0
            
        system_prompt = """You are a translator. Your task:
- Japanese text → Translate to English
- Non-Japanese text → Translate to Japanese
- Output ONLY the translation, no explanations"""
        
        json_data = {
            "contents": [
                {"parts": [{"text": f"{system_prompt}\n\nText to translate: {text}"}]}
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1000,
                "topP": 0.1,
                "topK": 1
            }
        }
        
        start_time = time.time()
        
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
                json.dump(json_data, temp_file, ensure_ascii=False)
                temp_file_path = temp_file.name
            
            try:
                api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                
                curl_cmd = [
                    "curl", "-s",
                    "-H", "Content-Type: application/json",
                    "-H", f"x-goog-api-key: {self.gemini_key}",
                    "-X", "POST",
                    "-d", f"@{temp_file_path}",
                    api_url
                ]
                
                result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
                elapsed_time = time.time() - start_time
                
                if result.returncode != 0:
                    return None, elapsed_time
                    
                response_json = json.loads(result.stdout)
                
                if "error" in response_json:
                    return None, elapsed_time
                    
                if "candidates" in response_json and response_json["candidates"]:
                    translated_text = response_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return translated_text, elapsed_time
                    
                return None, elapsed_time
                
            finally:
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            elapsed_time = time.time() - start_time
            return None, elapsed_time
    
    def _translate_plamo(self, text: str, server_prestart: bool = False) -> Tuple[Optional[str], float]:
        """plamo-translateで翻訳を実行"""
        # plamo-translateのパスを探す
        plamo_path = None
        
        # シェル経由でPATHを取得
        try:
            result = subprocess.run(
                [os.environ.get("SHELL", "/bin/sh"), "-l", "-c", "which plamo-translate"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                plamo_path = result.stdout.strip()
        except:
            pass
        
        if not plamo_path:
            # 一般的なパスを確認
            common_paths = [
                os.path.expanduser("~/.local/bin/plamo-translate"),
                "/usr/local/bin/plamo-translate",
                "/opt/homebrew/bin/plamo-translate"
            ]
            for path in common_paths:
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    plamo_path = path
                    break
        
        if not plamo_path:
            return None, 0.0
        
        if server_prestart:
            # サーバーを事前に起動する場合のロジック
            # 実際の実装では、plamo-translateサーバーの起動方法に応じて調整が必要
            pass
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                [plamo_path, "--input", text],
                capture_output=True,
                text=True,
                timeout=60
            )
            elapsed_time = time.time() - start_time
            
            if result.returncode != 0:
                return None, elapsed_time
                
            translated_text = result.stdout.strip()
            
            if translated_text:
                return translated_text, elapsed_time
                
            return None, elapsed_time
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            return None, elapsed_time
    
    def run_benchmark(self, iterations: int = 10, models_to_test: Optional[List[str]] = None):
        """ベンチマークを実行"""
        print("翻訳ベンチマークを開始します...")
        print(f"各テストケースを{iterations}回実行します\n")
        
        # テストするモデルを決定
        if models_to_test is None:
            models_to_test = ["openai", "gemini", "plamo"]
        
        print(f"テスト対象モデル: {', '.join(models_to_test)}\n")
        
        # OpenAIモデルのテスト
        if "openai" in models_to_test:
            for model_info in MODELS["openai"]:
                model_name = model_info["name"]
                model_id = model_info["model"]
                print(f"\n=== {model_name} のテスト ===")
                
                for test_key, test_info in TEST_CASES.items():
                    print(f"\n{test_info['name']}:")
                    times = []
                    success_count = 0
                    
                    for i in range(iterations):
                        translated, elapsed = self._translate_openai(test_info["text"], model_id)
                        if translated:
                            times.append(elapsed)
                            success_count += 1
                            print(f"  試行{i+1}: {elapsed:.3f}秒")
                        else:
                            print(f"  試行{i+1}: 失敗")
                    
                    if times:
                        avg_time = statistics.mean(times)
                        min_time = min(times)
                        max_time = max(times)
                        std_dev = statistics.stdev(times) if len(times) > 1 else 0
                        
                        print(f"  成功: {success_count}/{iterations}")
                        print(f"  平均: {avg_time:.3f}秒")
                        print(f"  最小: {min_time:.3f}秒")
                        print(f"  最大: {max_time:.3f}秒")
                        print(f"  標準偏差: {std_dev:.3f}秒")
        
        # Geminiモデルのテスト
        if "gemini" in models_to_test:
            for model_info in MODELS["gemini"]:
                model_name = model_info["name"]
                model_id = model_info["model"]
                print(f"\n=== {model_name} のテスト ===")
                
                for test_key, test_info in TEST_CASES.items():
                    print(f"\n{test_info['name']}:")
                    times = []
                    success_count = 0
                    
                    for i in range(iterations):
                        translated, elapsed = self._translate_gemini(test_info["text"], model_id)
                        if translated:
                            times.append(elapsed)
                            success_count += 1
                            print(f"  試行{i+1}: {elapsed:.3f}秒")
                        else:
                            print(f"  試行{i+1}: 失敗")
                    
                    if times:
                        avg_time = statistics.mean(times)
                        min_time = min(times)
                        max_time = max(times)
                        std_dev = statistics.stdev(times) if len(times) > 1 else 0
                        
                        print(f"  成功: {success_count}/{iterations}")
                        print(f"  平均: {avg_time:.3f}秒")
                        print(f"  最小: {min_time:.3f}秒")
                        print(f"  最大: {max_time:.3f}秒")
                        print(f"  標準偏差: {std_dev:.3f}秒")
        
        # Plamoのテスト（サーバー事前起動なし）
        if "plamo" in models_to_test:
            print(f"\n=== plamo-translate (サーバー事前起動なし) のテスト ===")
            
            for test_key, test_info in TEST_CASES.items():
                print(f"\n{test_info['name']}:")
                times = []
                success_count = 0
                
                for i in range(iterations):
                    translated, elapsed = self._translate_plamo(test_info["text"], server_prestart=False)
                    if translated:
                        times.append(elapsed)
                        success_count += 1
                        print(f"  試行{i+1}: {elapsed:.3f}秒")
                    else:
                        print(f"  試行{i+1}: 失敗")
                
                if times:
                    avg_time = statistics.mean(times)
                    min_time = min(times)
                    max_time = max(times)
                    std_dev = statistics.stdev(times) if len(times) > 1 else 0
                    
                    print(f"  成功: {success_count}/{iterations}")
                    print(f"  平均: {avg_time:.3f}秒")
                    print(f"  最小: {min_time:.3f}秒")
                    print(f"  最大: {max_time:.3f}秒")
                    print(f"  標準偏差: {std_dev:.3f}秒")
            
            # Plamoのテスト（サーバー事前起動あり）
            print(f"\n=== plamo-translate (サーバー事前起動あり) のテスト ===")
            print("※注意: 実際のサーバー事前起動の実装は、plamo-translateの仕様に応じて調整が必要です")
            
            # サーバーをバックグラウンドで起動
            server_process = None
            try:
                print("plamo-translateサーバーを起動中...")
                server_process = subprocess.Popen(
                    ["plamo-translate", "server"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                # サーバーの起動を少し待つ
                import time
                time.sleep(20)
                print("サーバー起動完了")
                
            except Exception as e:
                print(f"サーバー起動エラー: {e}")
                return
            
            for test_key, test_info in TEST_CASES.items():
                print(f"\n{test_info['name']}:")
                times = []
                success_count = 0
                
                for i in range(iterations):
                    translated, elapsed = self._translate_plamo(test_info["text"], server_prestart=True)
                    if translated:
                        times.append(elapsed)
                        success_count += 1
                        print(f"  試行{i+1}: {elapsed:.3f}秒")
                    else:
                        print(f"  試行{i+1}: 失敗")
                
                if times:
                    avg_time = statistics.mean(times)
                    min_time = min(times)
                    max_time = max(times)
                    std_dev = statistics.stdev(times) if len(times) > 1 else 0
                    
                    print(f"  成功: {success_count}/{iterations}")
                    print(f"  平均: {avg_time:.3f}秒")
                    print(f"  最小: {min_time:.3f}秒")
                    print(f"  最大: {max_time:.3f}秒")
                    print(f"  標準偏差: {std_dev:.3f}秒")
            
            # サーバープロセスのクリーンアップ
            if server_process:
                try:
                    print("\nplamo-translateサーバーを終了中...")
                    server_process.terminate()
                    server_process.wait(timeout=5)
                    print("サーバー終了完了")
                except subprocess.TimeoutExpired:
                    print("サーバーの強制終了を実行中...")
                    server_process.kill()
                    server_process.wait()
                    print("サーバー強制終了完了")
                except Exception as e:
                    print(f"サーバー終了エラー: {e}")

def main():
    """メイン関数"""
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="翻訳モデルの性能比較テスト")
    parser.add_argument(
        "--models", 
        nargs="+", 
        choices=["openai", "gemini", "plamo"],
        default=["openai", "gemini", "plamo"],
        help="テストするモデルを指定 (デフォルト: すべて)"
    )
    parser.add_argument(
        "--iterations", 
        type=int, 
        default=10,
        help="各テストケースの実行回数 (デフォルト: 10)"
    )
    
    args = parser.parse_args()
    
    benchmark = TranslationBenchmark()
    
    # APIキーの確認
    if "openai" in args.models and not benchmark.openai_key:
        print("警告: OPENAI_API_KEYが設定されていません")
    if "gemini" in args.models and not benchmark.gemini_key:
        print("警告: GEMINI_API_KEYが設定されていません")
    
    # ベンチマークを実行
    benchmark.run_benchmark(iterations=args.iterations, models_to_test=args.models)


if __name__ == "__main__":
    main()
