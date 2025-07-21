#!/usr/bin/env python3
"""Test suite for QuickTranslator class and main functionality."""

import json
import os
import sys
import subprocess
from unittest.mock import MagicMock, patch
import pytest

# Add the parent directory to sys.path to import translate-openai
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from translate_openai import QuickTranslator, main


class TestQuickTranslator:
    """Test cases for QuickTranslator class."""

    @pytest.fixture
    def translator(self):
        """Create a QuickTranslator instance for testing."""
        with patch.object(QuickTranslator, "_get_api_key", return_value="sk-test-key"):
            return QuickTranslator()

    def test_init(self, mocker):
        """Test QuickTranslator initialization."""
        mock_get_api_key = mocker.patch.object(
            QuickTranslator, "_get_api_key", return_value="sk-test-key"
        )
        mock_time = mocker.patch("time.time", return_value=1234567890.0)

        translator = QuickTranslator()

        assert translator.api_key == "sk-test-key"
        assert translator.program_start_time == 1234567890.0
        mock_get_api_key.assert_called_once()
        mock_time.assert_called_once()

    def test_get_api_key_from_shell(self, mocker):
        """Test API key retrieval from shell."""
        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.stdout = "sk-shell-key\n"
        mock_subprocess.return_value.returncode = 0
        mocker.patch.dict(os.environ, {"SHELL": "/opt/homebrew/bin/fish"})

        translator = QuickTranslator()

        assert translator.api_key == "sk-shell-key"
        mock_subprocess.assert_called_once_with(
            ["/opt/homebrew/bin/fish", "-l", "-c", "echo $OPENAI_API_KEY"],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_get_api_key_from_env(self, mocker):
        """Test API key retrieval from environment variable when shell fails."""
        mocker.patch("subprocess.run", side_effect=subprocess.SubprocessError)
        mocker.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-key"})

        translator = QuickTranslator()

        assert translator.api_key == "sk-env-key"

    def test_get_api_key_none(self, mocker):
        """Test when no API key is available."""
        mocker.patch("subprocess.run", side_effect=subprocess.SubprocessError)
        mocker.patch.dict(os.environ, {}, clear=True)

        translator = QuickTranslator()

        assert translator.api_key is None

    def test_escape_for_dialog(self, translator):
        """Test dialog text escaping."""
        # Test quote escaping
        result = translator._escape_for_dialog('He said "Hello"')
        assert result == 'He said \\"Hello\\"'

        # Test newline escaping
        result = translator._escape_for_dialog("Line 1\nLine 2")
        assert result == "Line 1\\nLine 2"

        # Test both
        result = translator._escape_for_dialog('Quote: "test"\nNew line')
        assert result == 'Quote: \\"test\\"\\nNew line'

    def test_show_dialog(self, translator, mocker):
        """Test macOS dialog display."""
        mock_subprocess = mocker.patch("subprocess.run")

        translator._show_dialog("Test message", "Test Title")

        expected_script = 'display dialog "Test message" buttons {"OK"} default button 1 with title "Test Title"'
        mock_subprocess.assert_called_once_with(
            ["osascript", "-e", expected_script], check=False
        )

    def test_show_dialog_with_escaping(self, translator, mocker):
        """Test dialog display with text that needs escaping."""
        mock_subprocess = mocker.patch("subprocess.run")

        translator._show_dialog('He said "Hello"\nWorld')

        expected_script = 'display dialog "He said \\"Hello\\"\\nWorld" buttons {"OK"} default button 1 with title "翻訳結果"'
        mock_subprocess.assert_called_once_with(
            ["osascript", "-e", expected_script], check=False
        )

    def test_show_dialog_subprocess_error(self, translator, mocker, capsys):
        """Test dialog display when subprocess fails."""
        mocker.patch("subprocess.run", side_effect=subprocess.SubprocessError)

        translator._show_dialog("Test message", "Test Title")

        captured = capsys.readouterr()
        assert "Test Title: Test message" in captured.out

    def test_copy_to_clipboard(self, translator, mocker):
        """Test clipboard copying."""
        mock_subprocess = mocker.patch("subprocess.run")

        translator._copy_to_clipboard("Test text")

        mock_subprocess.assert_called_once_with(
            ["pbcopy"], input="Test text".encode("utf-8"), check=True
        )

    def test_copy_to_clipboard_error(self, translator, mocker):
        """Test clipboard copying when subprocess fails."""
        mock_subprocess = mocker.patch(
            "subprocess.run", side_effect=subprocess.SubprocessError
        )

        # Should not raise an exception
        translator._copy_to_clipboard("Test text")

        mock_subprocess.assert_called_once()

    def test_translate_with_api_no_key(self, mocker):
        """Test translation when API key is not set."""
        with patch.object(QuickTranslator, "_get_api_key", return_value=None):
            translator = QuickTranslator()

            with pytest.raises(
                ValueError, match="環境変数OPENAI_API_KEYが設定されていません"
            ):
                translator.translate_with_api("Hello")

    def test_translate_with_api_invalid_key(self, mocker):
        """Test translation with invalid API key."""
        with patch.object(QuickTranslator, "_get_api_key", return_value="sk-xxx"):
            translator = QuickTranslator()

            with pytest.raises(ValueError, match="APIキーが設定されていません"):
                translator.translate_with_api("Hello")

    def test_translate_with_api_success(self, translator, mocker):
        """Test successful API translation."""
        # Mock time for measuring elapsed time
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [1000.0, 1002.5]  # start_time, end_time

        # Mock successful curl response
        mock_response = {
            "choices": [{"message": {"content": "  こんにちは、世界！  "}}]
        }
        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = json.dumps(mock_response)

        # Mock tempfile
        mock_tempfile = mocker.patch("tempfile.NamedTemporaryFile")
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.json"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        mock_unlink = mocker.patch("os.unlink")

        result_text, elapsed_time = translator.translate_with_api("Hello, World!")

        assert result_text == "こんにちは、世界！"  # Stripped
        assert elapsed_time == 2.5

        # Verify curl command
        expected_cmd = [
            "curl",
            "-s",
            "-H",
            "Authorization: Bearer sk-test-key",
            "-H",
            "Content-Type: application/json",
            "-d",
            "@/tmp/test.json",
            "https://api.openai.com/v1/chat/completions",
        ]
        mock_subprocess.assert_called_once_with(
            expected_cmd, capture_output=True, text=True, timeout=30
        )

        # Verify temp file cleanup
        mock_unlink.assert_called_once_with("/tmp/test.json")

    def test_translate_with_api_curl_error(self, translator, mocker):
        """Test API translation when curl fails."""
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [
            1000.0,
            1002.0,
            1003.0,
        ]  # Extra time call for error handling

        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Connection failed"

        mock_tempfile = mocker.patch("tempfile.NamedTemporaryFile")
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.json"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        mocker.patch("os.unlink")

        with pytest.raises(ValueError, match="curlエラー: 接続に失敗しました"):
            translator.translate_with_api("Hello")

    def test_translate_with_api_invalid_json(self, translator, mocker):
        """Test API translation with invalid JSON response."""
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [
            1000.0,
            1002.0,
            1003.0,
        ]  # Extra time call for error handling

        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Invalid JSON"

        mock_tempfile = mocker.patch("tempfile.NamedTemporaryFile")
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.json"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        mocker.patch("os.unlink")

        with pytest.raises(ValueError, match="無効なJSONレスポンス"):
            translator.translate_with_api("Hello")

    def test_translate_with_api_api_error(self, translator, mocker):
        """Test API translation with API error response."""
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [
            1000.0,
            1002.0,
            1003.0,
        ]  # Extra time call for error handling

        mock_response = {"error": {"message": "Rate limit exceeded"}}
        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = json.dumps(mock_response)

        mock_tempfile = mocker.patch("tempfile.NamedTemporaryFile")
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.json"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        mocker.patch("os.unlink")

        with pytest.raises(ValueError, match="APIエラー: Rate limit exceeded"):
            translator.translate_with_api("Hello")

    def test_translate_with_api_timeout(self, translator, mocker):
        """Test API translation timeout."""
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [1000.0, 1030.0]

        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd=["curl"], timeout=30
        )

        mock_tempfile = mocker.patch("tempfile.NamedTemporaryFile")
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.json"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        mocker.patch("os.unlink")

        with pytest.raises(ValueError, match="タイムアウトエラー"):
            translator.translate_with_api("Hello")

    def test_run_empty_input(self, translator, mocker):
        """Test run method with empty input."""
        mock_show_dialog = mocker.patch.object(translator, "_show_dialog")

        result = translator.run("")

        assert result is False
        mock_show_dialog.assert_called_once_with(
            "テキストが選択されていません", "エラー"
        )

    def test_run_success(self, translator, mocker):
        """Test successful run."""
        mock_translate = mocker.patch.object(translator, "translate_with_api")
        mock_translate.return_value = ("Translation result", 1.5)

        mock_copy = mocker.patch.object(translator, "_copy_to_clipboard")
        mock_dialog = mocker.patch.object(translator, "_show_dialog")

        # Set program start time and mock time.time() for total time calculation
        translator.program_start_time = 1000.0
        mocker.patch("time.time", return_value=1003.0)

        result = translator.run("Hello")

        assert result is True
        mock_translate.assert_called_once_with("Hello")
        mock_copy.assert_called_once_with("Translation result")

        expected_message = (
            "Translation result\n\n翻訳API時間: 1.50秒\n全体実行時間: 3.00秒"
        )
        mock_dialog.assert_called_once_with(expected_message, "翻訳結果")

    def test_run_translation_error(self, translator, mocker, capsys):
        """Test run method when translation fails."""
        mock_translate = mocker.patch.object(translator, "translate_with_api")
        mock_translate.side_effect = ValueError("API Error")

        mock_dialog = mocker.patch.object(translator, "_show_dialog")

        result = translator.run("Hello")

        assert result is False
        mock_dialog.assert_called_once_with("API Error", "エラー")


class TestMainFunction:
    """Test cases for main function."""

    def test_main_with_stdin(self, mocker):
        """Test main function with stdin input."""
        mock_stdin = mocker.patch("sys.stdin")
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = "Hello from stdin\n"

        mock_translator = mocker.patch("translate_openai.QuickTranslator")
        mock_instance = MagicMock()
        mock_instance.run.return_value = True
        mock_translator.return_value = mock_instance

        mock_exit = mocker.patch("sys.exit")

        main()

        mock_instance.run.assert_called_once_with("Hello from stdin")
        mock_exit.assert_called_once_with(0)

    def test_main_with_args(self, mocker):
        """Test main function with command line arguments."""
        mock_stdin = mocker.patch("sys.stdin")
        mock_stdin.isatty.return_value = True

        mocker.patch("sys.argv", ["translate_openai.py", "Hello", "World"])

        mock_translator = mocker.patch("translate_openai.QuickTranslator")
        mock_instance = MagicMock()
        mock_instance.run.return_value = True
        mock_translator.return_value = mock_instance

        mock_exit = mocker.patch("sys.exit")

        main()

        mock_instance.run.assert_called_once_with("Hello World")
        mock_exit.assert_called_once_with(0)

    def test_main_empty_input(self, mocker):
        """Test main function with empty input."""
        mock_stdin = mocker.patch("sys.stdin")
        mock_stdin.isatty.return_value = True

        mocker.patch("sys.argv", ["translate_openai.py"])

        mock_translator = mocker.patch("translate_openai.QuickTranslator")
        mock_instance = MagicMock()
        mock_instance.run.return_value = False
        mock_translator.return_value = mock_instance

        mock_exit = mocker.patch("sys.exit")

        main()

        mock_instance.run.assert_called_once_with("")
        mock_exit.assert_called_once_with(1)

    def test_main_translation_failure(self, mocker):
        """Test main function when translation fails."""
        mock_stdin = mocker.patch("sys.stdin")
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = "Test input"

        mock_translator = mocker.patch("translate_openai.QuickTranslator")
        mock_instance = MagicMock()
        mock_instance.run.return_value = False
        mock_translator.return_value = mock_instance

        mock_exit = mocker.patch("sys.exit")

        main()

        mock_instance.run.assert_called_once_with("Test input")
        mock_exit.assert_called_once_with(1)
