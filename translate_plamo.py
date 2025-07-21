#!/usr/bin/env python3

import os
import sys
import time
import subprocess
from typing import Optional


class PlamoTranslator:
    def __init__(self):
        self.program_start_time = time.time()
        self.plamo_path, self.path_list = self._find_plamo_translate()

    def _find_plamo_translate(self) -> tuple[Optional[str], list[str]]:
        """plamo-translateのパスを複数の方法で検索"""
        # シェルの種類を検出
        shell_name = os.path.basename(os.environ.get("SHELL", "/bin/sh"))

        # シェル経由でコマンドを探す
        plamo_path, path_list = self._search_via_shell(shell_name)

        return plamo_path, path_list

    def _search_via_shell(self, shell_name: str) -> tuple[Optional[str], list[str]]:
        """ログインシェルから$PATHを取得してplamo-translateを検索"""
        shell_path = os.environ.get("SHELL", "/bin/sh")

        # ログインシェルから$PATHを取得
        path_list = self._get_path_from_shell(shell_path, shell_name)
        if not path_list:
            return None, []

        # 各PATHディレクトリでplamo-translateを検索
        for path_dir in path_list:
            plamo_path = os.path.join(path_dir, "plamo-translate")
            if os.path.isfile(plamo_path) and os.access(plamo_path, os.X_OK):
                return plamo_path, path_list

        return None, path_list

    def _get_path_from_shell(self, shell_path: str, shell_name: str) -> list[str]:
        """ログインシェルから$PATHを取得してパースする"""
        try:
            # ログインシェルから$PATHを取得
            if shell_name == "fish":
                # fishの場合：インタラクティブログインシェルとして実行し、設定ファイルを確実に読み込む
                result = subprocess.run(
                    [shell_path, "-l", "-i", "-c", 'printf "%s\\n" $PATH'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            else:
                # bash/zshの場合
                result = subprocess.run(
                    [shell_path, "-l", "-c", 'echo "$PATH"'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

            if result.returncode != 0:
                return []

            path_output = result.stdout.strip()
            if not path_output:
                return []

            # シェルの種類に応じてPATHをパース
            if shell_name == "fish":
                # fishは改行区切りで出力される（printf "%s\\n"の結果）
                path_list = [p.strip() for p in path_output.split("\n") if p.strip()]
            else:
                # bash/zshはコロン区切り
                path_list = [p.strip() for p in path_output.split(":") if p.strip()]

            # 重要なパスが欠けている場合は手動で追加
            original_count = len(path_list)
            path_list = self._ensure_common_paths(path_list)
            if len(path_list) > original_count:
                print(
                    f"デバッグ: {len(path_list) - original_count}個の重要なパスを追加しました",
                    file=sys.stderr,
                )
            print(f"デバッグ: 最終的なPATH数: {len(path_list)}", file=sys.stderr)

            return path_list

        except (
            subprocess.TimeoutExpired,
            subprocess.SubprocessError,
            FileNotFoundError,
        ):
            return []

    def _ensure_common_paths(self, path_list: list[str]) -> list[str]:
        """重要なパスが欠けている場合は手動で追加"""
        # よく使われる重要なパス
        important_paths = [
            os.path.expanduser("~/.local/bin"),
            "/opt/homebrew/bin",
            "/usr/local/bin",
        ]

        # 既存のパスリストに含まれていない重要なパスを先頭に追加
        for important_path in reversed(important_paths):  # 逆順で追加して優先順位を保つ
            if important_path not in path_list and os.path.isdir(important_path):
                path_list.insert(0, important_path)

        return path_list

    def _escape_for_dialog(self, text: str) -> str:
        """osascriptのダイアログ用にテキストをエスケープ"""
        # ダブルクォートをエスケープし、改行を\\nに変換
        escaped = text.replace('"', '\\"').replace("\n", "\\n")
        return escaped

    def _show_dialog(self, message: str, title: str = "翻訳結果") -> None:
        """macOSのダイアログを表示"""
        escaped_message = self._escape_for_dialog(message)
        script = f'display dialog "{escaped_message}" buttons {{"OK"}} default button 1 with title "{title}"'
        try:
            subprocess.run(["osascript", "-e", script], check=False)
        except subprocess.SubprocessError:
            print(f"{title}: {message}")

    def _copy_to_clipboard(self, text: str) -> None:
        """テキストをクリップボードにコピー"""
        try:
            subprocess.run(["/usr/bin/pbcopy"], input=text.encode("utf-8"), check=True)
        except subprocess.SubprocessError:
            pass  # クリップボードのコピーに失敗しても継続

    def _show_plamo_not_found_error(self, path_list: Optional[list[str]] = None) -> None:
        """plamo-translateが見つからない場合のエラーダイアログ"""
        shell = os.environ.get("SHELL", "unknown")
        shell_name = os.path.basename(shell)

        if path_list:
            # 実際に取得・パースしたPATHを表示
            path_display = "\\n".join([f"- {path}" for path in path_list])
            error_msg = (
                f"plamo-translateが見つかりません\\n\\n"
                f"シェル: {shell} ({shell_name})\\n"
                f"取得した$PATH ({len(path_list)}個):\\n"
                f"{path_display}"
            )
        else:
            # PATHの取得に失敗した場合
            error_msg = (
                f"plamo-translateが見つかりません\\n\\n"
                f"シェル: {shell} ({shell_name})\\n"
                f"$PATHの取得に失敗しました"
            )

        self._show_dialog(error_msg, "エラー")
        # デバッグ用にコンソールにも出力
        console_msg = error_msg.replace("\\n", "\n")
        print(f"エラー: {console_msg}", file=sys.stderr)

    def translate_with_plamo_cli(self, text: str) -> tuple[str, float]:
        """plamo-translate CLIを使ってテキストを翻訳"""
        if not self.plamo_path:
            self._show_plamo_not_found_error(self.path_list)
            raise ValueError("plamo-translateが見つかりません")

        # 翻訳時間の計測開始
        start_time = time.time()

        try:
            # plamo-translate CLIを実行
            result = subprocess.run(
                [self.plamo_path, "--input", text],
                capture_output=True,
                text=True,
                timeout=60,  # plamo-translateは時間がかかる場合があるので長めに設定
            )

            # 翻訳時間の計測終了
            end_time = time.time()
            elapsed_time = end_time - start_time

            # エラーチェック
            if result.returncode != 0:
                error_msg = f"plamo-translateエラー: {result.stderr or result.stdout}"
                raise ValueError(error_msg)

            translated_text = result.stdout.strip()

            if not translated_text:
                raise ValueError("エラー: 翻訳結果が空でした")

            return translated_text, elapsed_time

        except subprocess.TimeoutExpired:
            end_time = time.time()
            elapsed_time = end_time - start_time
            error_msg = (
                "タイムアウトエラー: plamo-translateの実行がタイムアウトしました"
            )
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
            self._show_dialog("テキストが選択されていません", "エラー")
            return False

        # plamo-translateが見つからない場合
        if not self.plamo_path:
            self._show_plamo_not_found_error(self.path_list)
            return False

        try:
            # 翻訳実行
            translated_text, elapsed_time = self.translate_with_plamo_cli(input_text)

            # クリップボードにコピー
            self._copy_to_clipboard(translated_text)

            # プログラム全体の実行時間を計算
            total_time = time.time() - self.program_start_time

            # 翻訳時間をフォーマット（小数点第2位まで）
            formatted_cli_time = f"{elapsed_time:.2f}"
            formatted_total_time = f"{total_time:.2f}"

            # 結果を表示
            time_info = f"\n\nplamo-server時間: {formatted_cli_time}秒\n全体実行時間: {formatted_total_time}秒"
            message = f"{translated_text}{time_info}"
            self._show_dialog(message, "翻訳結果")

            # 結果を出力
            print(translated_text)
            return True

        except ValueError as e:
            self._show_dialog(str(e), "エラー")
            return False
        except Exception as e:
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
    translator = PlamoTranslator()
    success = translator.run(input_text)

    # 終了コードを設定
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
