#!/usr/bin/env python3
"""Test suite for QuickTranslator class (Gemini version) and main functionality."""

import json
import os
import sys
import subprocess
from unittest.mock import MagicMock, patch
import pytest

# Add the parent directory to sys.path to import translate_gemini
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from translate_gemini import QuickTranslator, main, MODEL


class TestQuickTranslatorGemini:
    """Test cases for QuickTranslator class (Gemini version)."""

    @pytest.fixture
    def translator(self):
        """Create a QuickTranslator instance for testing."""
        with patch.object(
            QuickTranslator, "_get_api_key", return_value="test-gemini-api-key"
        ):
            return QuickTranslator()

    def test_init(self, mocker):
        """Test QuickTranslator initialization."""
        mock_get_api_key = mocker.patch.object(
            QuickTranslator, "_get_api_key", return_value="test-gemini-api-key"
        )
        mock_time = mocker.patch("time.time", return_value=1234567890.0)

        translator = QuickTranslator()

        assert translator.api_key == "test-gemini-api-key"
        assert translator.program_start_time == 1234567890.0
        mock_get_api_key.assert_called_once()
        mock_time.assert_called_once()

    def test_get_api_key_from_shell(self, mocker):
        """Test API key retrieval from shell."""
        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.stdout = "gemini-shell-key\n"
        mock_subprocess.return_value.returncode = 0
        mocker.patch.dict(os.environ, {"SHELL": "/opt/homebrew/bin/fish"})

        translator = QuickTranslator()

        assert translator.api_key == "gemini-shell-key"
        mock_subprocess.assert_called_once_with(
            ["/opt/homebrew/bin/fish", "-l", "-c", "echo $GEMINI_API_KEY"],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_get_api_key_from_env(self, mocker):
        """Test API key retrieval from environment variable when shell fails."""
        mocker.patch("subprocess.run", side_effect=subprocess.SubprocessError)
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-env-key"})

        translator = QuickTranslator()

        assert translator.api_key == "gemini-env-key"

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
            ["pbcopy"], input=b"Test text", check=True
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
                ValueError, match="環境変数GEMINI_API_KEYが設定されていません"
            ):
                translator.translate_with_api("Hello")

    def test_translate_with_api_success(self, translator, mocker):
        """Test successful API translation."""
        # Mock time for measuring elapsed time
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [1000.0, 1002.5]  # start_time, end_time

        # Mock successful curl response (Gemini format)
        mock_response = {
            "candidates": [{"content": {"parts": [{"text": "  こんにちは、世界！  "}]}}]
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

        # Verify curl command (header method is tried first)
        expected_cmd = [
            "curl",
            "-s",
            "-H",
            "Content-Type: application/json",
            "-H",
            "x-goog-api-key: test-gemini-api-key",
            "-X",
            "POST",
            "-d",
            "@/tmp/test.json",
            f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        ]
        mock_subprocess.assert_called_once_with(
            expected_cmd, capture_output=True, text=True, timeout=30
        )

        # Verify temp file cleanup
        mock_unlink.assert_called_once_with("/tmp/test.json")

    def test_translate_with_api_header_fails_url_succeeds(self, translator, mocker):
        """Test API translation when header method fails but URL parameter method succeeds."""
        # Mock time
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [1000.0, 1002.5]

        # Mock successful response
        mock_response = {
            "candidates": [{"content": {"parts": [{"text": "Translation result"}]}}]
        }

        # Mock subprocess to fail on first call (header method) and succeed on second (URL param method)
        mock_subprocess = mocker.patch("subprocess.run")

        # First call fails
        first_call_result = MagicMock()
        first_call_result.returncode = 1
        first_call_result.stderr = "Auth error"

        # Second call succeeds
        second_call_result = MagicMock()
        second_call_result.returncode = 0
        second_call_result.stdout = json.dumps(mock_response)

        mock_subprocess.side_effect = [first_call_result, second_call_result]

        # Mock tempfile
        mock_tempfile = mocker.patch("tempfile.NamedTemporaryFile")
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.json"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        mocker.patch("os.unlink")

        result_text, elapsed_time = translator.translate_with_api("Hello")

        assert result_text == "Translation result"
        assert elapsed_time == 2.5

        # Verify both curl commands were called
        assert mock_subprocess.call_count == 2

        # First call (header method)
        first_call_args = mock_subprocess.call_args_list[0][0][0]
        assert "-H" in first_call_args
        assert "x-goog-api-key: test-gemini-api-key" in first_call_args

        # Second call (URL parameter method)
        second_call_args = mock_subprocess.call_args_list[1][0][0]
        api_url_with_key = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key=test-gemini-api-key"
        assert api_url_with_key in second_call_args

    def test_translate_with_api_both_methods_fail(self, translator, mocker):
        """Test API translation when both header and URL parameter methods fail."""
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [1000.0, 1002.0, 1003.0]

        # Mock subprocess to fail on both calls
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

        # Verify both methods were tried
        assert mock_subprocess.call_count == 2

    def test_translate_with_api_invalid_json(self, translator, mocker):
        """Test API translation with invalid JSON response."""
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [1000.0, 1002.0, 1003.0]

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
        mock_time.side_effect = [1000.0, 1002.0, 1003.0]

        mock_response = {"error": {"message": "Invalid API key"}}
        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = json.dumps(mock_response)

        mock_tempfile = mocker.patch("tempfile.NamedTemporaryFile")
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.json"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        mocker.patch("os.unlink")

        with pytest.raises(ValueError, match="APIエラー: Invalid API key"):
            translator.translate_with_api("Hello")

    def test_translate_with_api_missing_candidates(self, translator, mocker):
        """Test API translation with missing candidates in response."""
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [1000.0, 1002.0, 1003.0]

        mock_response = {}  # Empty response
        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = json.dumps(mock_response)

        mock_tempfile = mocker.patch("tempfile.NamedTemporaryFile")
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.json"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        mocker.patch("os.unlink")

        with pytest.raises(ValueError, match="翻訳結果が取得できませんでした"):
            translator.translate_with_api("Hello")

    def test_translate_with_api_empty_result(self, translator, mocker):
        """Test API translation with empty translation result."""
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [1000.0, 1002.0, 1003.0]

        mock_response = {"candidates": [{"content": {"parts": [{"text": ""}]}}]}
        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = json.dumps(mock_response)

        mock_tempfile = mocker.patch("tempfile.NamedTemporaryFile")
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.json"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        mocker.patch("os.unlink")

        with pytest.raises(ValueError, match="翻訳結果が空でした"):
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

    def test_translate_with_api_json_data_structure(self, translator, mocker):
        """Test that the JSON data sent to Gemini API has the correct structure."""
        # Mock subprocess to capture the JSON data
        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = json.dumps(
            {"candidates": [{"content": {"parts": [{"text": "Result"}]}}]}
        )

        # Capture what's written to the temp file
        written_data = None

        def mock_write(data):
            nonlocal written_data
            written_data = data

        mock_tempfile = mocker.patch("tempfile.NamedTemporaryFile")
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.json"
        mock_file.write = mock_write
        mock_tempfile.return_value.__enter__.return_value = mock_file

        # Mock json.dump to capture the data
        def mock_json_dump(data, file, **kwargs):
            file.write(json.dumps(data))

        mocker.patch("json.dump", side_effect=mock_json_dump)
        mocker.patch("os.unlink")
        mocker.patch("time.time", side_effect=[1000.0, 1001.0])

        translator.translate_with_api("Test input")

        # Parse the written JSON data
        assert written_data is not None
        json_data = json.loads(written_data)

        # Verify the structure matches Gemini API format
        assert "contents" in json_data
        assert len(json_data["contents"]) == 1
        assert "parts" in json_data["contents"][0]
        assert len(json_data["contents"][0]["parts"]) == 1
        assert "text" in json_data["contents"][0]["parts"][0]

        # Check the prompt content
        prompt_text = json_data["contents"][0]["parts"][0]["text"]
        assert "You are a translator" in prompt_text
        assert "Test input" in prompt_text

        # Check generation config
        assert "generationConfig" in json_data
        assert json_data["generationConfig"]["temperature"] == 0.1
        assert json_data["generationConfig"]["maxOutputTokens"] == 1000
        assert json_data["generationConfig"]["topP"] == 0.1
        assert json_data["generationConfig"]["topK"] == 1

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
            f"Translation result\n\n使用モデル: {MODEL}\n翻訳API時間: 1.50秒\n全体実行時間: 3.00秒"
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

    def test_run_unexpected_error(self, translator, mocker):
        """Test run method when unexpected error occurs."""
        mock_translate = mocker.patch.object(translator, "translate_with_api")
        mock_translate.side_effect = Exception("Unexpected error")

        mock_dialog = mocker.patch.object(translator, "_show_dialog")

        result = translator.run("Hello")

        assert result is False
        mock_dialog.assert_called_once_with(
            "予期しないエラーが発生しました: Unexpected error", "エラー"
        )


class TestMainFunctionGemini:
    """Test cases for main function."""

    def test_main_with_stdin(self, mocker):
        """Test main function with stdin input."""
        mock_stdin = mocker.patch("sys.stdin")
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = "Hello from stdin\n"

        mock_translator = mocker.patch("translate_gemini.QuickTranslator")
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

        mocker.patch("sys.argv", ["translate_gemini.py", "Hello", "World"])

        mock_translator = mocker.patch("translate_gemini.QuickTranslator")
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

        mocker.patch("sys.argv", ["translate_gemini.py"])

        mock_translator = mocker.patch("translate_gemini.QuickTranslator")
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

        mock_translator = mocker.patch("translate_gemini.QuickTranslator")
        mock_instance = MagicMock()
        mock_instance.run.return_value = False
        mock_translator.return_value = mock_instance

        mock_exit = mocker.patch("sys.exit")

        main()

        mock_instance.run.assert_called_once_with("Test input")
        mock_exit.assert_called_once_with(1)
