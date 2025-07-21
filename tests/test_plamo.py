#!/usr/bin/env python3
"""Test suite for PlamoTranslator class and main functionality."""

import os
import sys
import subprocess
from unittest.mock import MagicMock, patch
import pytest

# Add the parent directory to sys.path to import translate_plamo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from translate_plamo import PlamoTranslator, main


class TestPlamoTranslator:
    """Test cases for PlamoTranslator class."""

    @pytest.fixture
    def translator(self):
        """Create a PlamoTranslator instance for testing."""
        with patch.object(
            PlamoTranslator,
            "_find_plamo_translate",
            return_value=(
                "/usr/local/bin/plamo-translate",
                ["/usr/local/bin", "/usr/bin"],
            ),
        ):
            return PlamoTranslator()

    def test_init(self, mocker):
        """Test PlamoTranslator initialization."""
        mock_find_plamo = mocker.patch.object(
            PlamoTranslator,
            "_find_plamo_translate",
            return_value=(
                "/usr/local/bin/plamo-translate",
                ["/usr/local/bin", "/usr/bin"],
            ),
        )
        mock_time = mocker.patch("time.time", return_value=1234567890.0)

        translator = PlamoTranslator()

        assert translator.plamo_path == "/usr/local/bin/plamo-translate"
        assert translator.path_list == ["/usr/local/bin", "/usr/bin"]
        assert translator.program_start_time == 1234567890.0
        mock_find_plamo.assert_called_once()
        mock_time.assert_called_once()

    def test_get_path_from_shell_fish(self, mocker):
        """Test PATH retrieval from fish shell."""
        with patch.object(
            PlamoTranslator,
            "_find_plamo_translate",
            return_value=("/usr/local/bin/plamo-translate", []),
        ):
            translator = PlamoTranslator()

        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "/usr/local/bin\n/usr/bin\n/bin\n"

        mock_ensure_common = mocker.patch.object(
            translator,
            "_ensure_common_paths",
            return_value=["/usr/local/bin", "/usr/bin", "/bin"],
        )

        result = translator._get_path_from_shell("/opt/homebrew/bin/fish", "fish")

        assert result == ["/usr/local/bin", "/usr/bin", "/bin"]

        # Check that fish command was called with -l -i flags
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert call_args == [
            "/opt/homebrew/bin/fish",
            "-l",
            "-i",
            "-c",
            'printf "%s\\n" $PATH',
        ]
        mock_ensure_common.assert_called_once()

    def test_get_path_from_shell_bash(self, mocker):
        """Test PATH retrieval from bash shell."""
        with patch.object(
            PlamoTranslator,
            "_find_plamo_translate",
            return_value=("/usr/local/bin/plamo-translate", []),
        ):
            translator = PlamoTranslator()

        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "/usr/local/bin:/usr/bin:/bin"

        mock_ensure_common = mocker.patch.object(
            translator,
            "_ensure_common_paths",
            return_value=["/usr/local/bin", "/usr/bin", "/bin"],
        )

        result = translator._get_path_from_shell("/bin/bash", "bash")

        assert result == ["/usr/local/bin", "/usr/bin", "/bin"]

        # Check that bash command was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert call_args == ["/bin/bash", "-l", "-c", 'echo "$PATH"']
        mock_ensure_common.assert_called_once()

    def test_get_path_from_shell_error(self, mocker):
        """Test PATH retrieval when subprocess fails."""
        with patch.object(
            PlamoTranslator,
            "_find_plamo_translate",
            return_value=("/usr/local/bin/plamo-translate", []),
        ):
            translator = PlamoTranslator()

        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 1

        result = translator._get_path_from_shell("/bin/bash", "bash")

        assert result == []

    def test_get_path_from_shell_timeout(self, mocker):
        """Test PATH retrieval when subprocess times out."""
        with patch.object(
            PlamoTranslator,
            "_find_plamo_translate",
            return_value=("/usr/local/bin/plamo-translate", []),
        ):
            translator = PlamoTranslator()

        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd=["bash"], timeout=10
        )

        result = translator._get_path_from_shell("/bin/bash", "bash")

        assert result == []

    def test_ensure_common_paths(self, mocker):
        """Test ensuring common paths are included."""
        with patch.object(
            PlamoTranslator,
            "_find_plamo_translate",
            return_value=("/usr/local/bin/plamo-translate", []),
        ):
            translator = PlamoTranslator()

        # Mock os.path.isdir to return True for important paths
        mock_isdir = mocker.patch("os.path.isdir")
        mock_isdir.side_effect = lambda path: path in [
            "/usr/local/bin",
            os.path.expanduser("~/.local/bin"),
        ]

        # Mock os.path.expanduser
        mock_expanduser = mocker.patch("os.path.expanduser")
        mock_expanduser.return_value = "/Users/test/.local/bin"

        # Test with incomplete path list
        input_paths = ["/usr/bin", "/bin"]
        result = translator._ensure_common_paths(input_paths)

        # Should add missing important paths at the beginning
        expected = ["/Users/test/.local/bin", "/usr/local/bin", "/usr/bin", "/bin"]
        assert result == expected

    def test_ensure_common_paths_already_present(self, mocker):
        """Test ensuring common paths when they're already present."""
        with patch.object(
            PlamoTranslator,
            "_find_plamo_translate",
            return_value=("/usr/local/bin/plamo-translate", []),
        ):
            translator = PlamoTranslator()

        # Test with complete path list
        input_paths = [
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            os.path.expanduser("~/.local/bin"),
        ]
        result = translator._ensure_common_paths(input_paths)

        # Should not add duplicates
        assert result == input_paths

    def test_search_via_shell_found(self, mocker):
        """Test plamo-translate search when found."""
        with patch.object(
            PlamoTranslator,
            "_find_plamo_translate",
            return_value=("/usr/local/bin/plamo-translate", []),
        ):
            translator = PlamoTranslator()

        mock_get_path = mocker.patch.object(translator, "_get_path_from_shell")
        mock_get_path.return_value = ["/usr/local/bin", "/usr/bin"]

        # Mock os.path.isfile and os.access
        mock_isfile = mocker.patch("os.path.isfile")
        mock_access = mocker.patch("os.access")
        mock_isfile.side_effect = lambda path: path == "/usr/local/bin/plamo-translate"
        mock_access.side_effect = (
            lambda path, mode: path == "/usr/local/bin/plamo-translate"
        )

        result_path, result_paths = translator._search_via_shell("bash")

        assert result_path == "/usr/local/bin/plamo-translate"
        assert result_paths == ["/usr/local/bin", "/usr/bin"]

    def test_search_via_shell_not_found(self, mocker):
        """Test plamo-translate search when not found."""
        with patch.object(
            PlamoTranslator,
            "_find_plamo_translate",
            return_value=("/usr/local/bin/plamo-translate", []),
        ):
            translator = PlamoTranslator()

        mock_get_path = mocker.patch.object(translator, "_get_path_from_shell")
        mock_get_path.return_value = ["/usr/local/bin", "/usr/bin"]

        # Mock os.path.isfile to return False (not found)
        mocker.patch("os.path.isfile", return_value=False)

        result_path, result_paths = translator._search_via_shell("bash")

        assert result_path is None
        assert result_paths == ["/usr/local/bin", "/usr/bin"]

    def test_search_via_shell_no_paths(self, mocker):
        """Test plamo-translate search when no paths retrieved."""
        with patch.object(
            PlamoTranslator,
            "_find_plamo_translate",
            return_value=("/usr/local/bin/plamo-translate", []),
        ):
            translator = PlamoTranslator()

        mock_get_path = mocker.patch.object(translator, "_get_path_from_shell")
        mock_get_path.return_value = []

        result_path, result_paths = translator._search_via_shell("bash")

        assert result_path is None
        assert result_paths == []

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
            ["/usr/bin/pbcopy"], input="Test text".encode("utf-8"), check=True
        )

    def test_copy_to_clipboard_error(self, translator, mocker):
        """Test clipboard copying when subprocess fails."""
        mock_subprocess = mocker.patch(
            "subprocess.run", side_effect=subprocess.SubprocessError
        )

        # Should not raise an exception
        translator._copy_to_clipboard("Test text")

        mock_subprocess.assert_called_once()

    def test_show_plamo_not_found_error_with_paths(self, translator, mocker, capsys):
        """Test plamo-translate not found error dialog with path list."""
        mock_show_dialog = mocker.patch.object(translator, "_show_dialog")
        mocker.patch.dict(os.environ, {"SHELL": "/bin/bash"})

        path_list = ["/usr/local/bin", "/usr/bin", "/bin"]
        translator._show_plamo_not_found_error(path_list)

        # Check dialog was called
        mock_show_dialog.assert_called_once()
        args = mock_show_dialog.call_args[0]
        message = args[0]
        title = args[1]

        assert "plamo-translateが見つかりません" in message
        assert "/bin/bash (bash)" in message
        assert "取得した$PATH (3個)" in message
        assert "- /usr/local/bin" in message
        assert "- /usr/bin" in message
        assert "- /bin" in message
        assert title == "エラー"

        # Check console output
        captured = capsys.readouterr()
        assert "エラー:" in captured.err

    def test_show_plamo_not_found_error_no_paths(self, translator, mocker, capsys):
        """Test plamo-translate not found error dialog without path list."""
        mock_show_dialog = mocker.patch.object(translator, "_show_dialog")
        mocker.patch.dict(os.environ, {"SHELL": "/bin/bash"})

        translator._show_plamo_not_found_error(None)

        # Check dialog was called
        mock_show_dialog.assert_called_once()
        args = mock_show_dialog.call_args[0]
        message = args[0]

        assert "plamo-translateが見つかりません" in message
        assert "/bin/bash (bash)" in message
        assert "$PATHの取得に失敗しました" in message

    def test_translate_with_plamo_cli_no_path(self, mocker):
        """Test translation when plamo-translate path is not found."""
        with patch.object(
            PlamoTranslator, "_find_plamo_translate", return_value=(None, [])
        ):
            translator = PlamoTranslator()

            # Mock the _show_plamo_not_found_error method to prevent dialog display
            mock_show_error = mocker.patch.object(
                translator, "_show_plamo_not_found_error"
            )

            with pytest.raises(ValueError, match="plamo-translateが見つかりません"):
                translator.translate_with_plamo_cli("Hello")

            # Verify that the error dialog method was called with path list
            mock_show_error.assert_called_once_with([])

    def test_translate_with_plamo_cli_success(self, translator, mocker):
        """Test successful plamo-translate execution."""
        # Mock time for measuring elapsed time
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [1000.0, 1002.5]  # start_time, end_time

        # Mock successful plamo-translate response
        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "  こんにちは、世界！  \n"
        mock_subprocess.return_value.stderr = ""

        result_text, elapsed_time = translator.translate_with_plamo_cli("Hello, World!")

        assert result_text == "こんにちは、世界！"  # Stripped
        assert elapsed_time == 2.5

        # Verify plamo-translate command
        mock_subprocess.assert_called_once_with(
            ["/usr/local/bin/plamo-translate", "--input", "Hello, World!"],
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_translate_with_plamo_cli_error(self, translator, mocker):
        """Test plamo-translate execution error."""
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [1000.0, 1002.0, 1003.0]

        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = "Translation failed"

        with pytest.raises(
            ValueError, match="plamo-translateエラー: Translation failed"
        ):
            translator.translate_with_plamo_cli("Hello")

    def test_translate_with_plamo_cli_timeout(self, translator, mocker):
        """Test plamo-translate timeout."""
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [1000.0, 1060.0]

        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd=["plamo-translate"], timeout=60
        )

        with pytest.raises(ValueError, match="タイムアウトエラー"):
            translator.translate_with_plamo_cli("Hello")

    def test_translate_with_plamo_cli_empty_result(self, translator, mocker):
        """Test when plamo-translate returns empty result."""
        mock_time = mocker.patch("time.time")
        mock_time.side_effect = [1000.0, 1002.0, 1003.0]

        mock_subprocess = mocker.patch("subprocess.run")
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "   \n"
        mock_subprocess.return_value.stderr = ""

        with pytest.raises(ValueError, match="翻訳結果が空でした"):
            translator.translate_with_plamo_cli("Hello")

    def test_run_empty_input(self, translator, mocker):
        """Test run method with empty input."""
        # Mock _show_dialog to prevent actual dialog display
        mock_show_dialog = mocker.patch.object(translator, "_show_dialog")

        result = translator.run("")

        assert result is False
        mock_show_dialog.assert_called_once_with(
            "テキストが選択されていません", "エラー"
        )

    def test_run_plamo_not_found(self, mocker):
        """Test run method when plamo-translate is not found."""
        with patch.object(
            PlamoTranslator,
            "_find_plamo_translate",
            return_value=(None, ["/usr/bin", "/bin"]),
        ):
            translator = PlamoTranslator()
            # Mock the error dialog method to prevent actual dialog display
            mock_show_error = mocker.patch.object(
                translator, "_show_plamo_not_found_error"
            )

            result = translator.run("Hello")

            assert result is False
            mock_show_error.assert_called_once_with(["/usr/bin", "/bin"])

    def test_run_success(self, translator, mocker):
        """Test successful run."""
        # Mock all methods to prevent actual system calls
        mock_translate = mocker.patch.object(translator, "translate_with_plamo_cli")
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
            "Translation result\n\nplamo-server時間: 1.50秒\n全体実行時間: 3.00秒"
        )
        mock_dialog.assert_called_once_with(expected_message, "翻訳結果")

    def test_run_translation_error(self, translator, mocker):
        """Test run method when translation fails."""
        # Mock methods to prevent actual system calls
        mock_translate = mocker.patch.object(translator, "translate_with_plamo_cli")
        mock_translate.side_effect = ValueError("Plamo Error")

        mock_dialog = mocker.patch.object(translator, "_show_dialog")

        result = translator.run("Hello")

        assert result is False
        mock_dialog.assert_called_once_with("Plamo Error", "エラー")

    def test_run_unexpected_error(self, translator, mocker):
        """Test run method when unexpected error occurs."""
        # Mock methods to prevent actual system calls
        mock_translate = mocker.patch.object(translator, "translate_with_plamo_cli")
        mock_translate.side_effect = Exception("Unexpected error")

        mock_dialog = mocker.patch.object(translator, "_show_dialog")

        result = translator.run("Hello")

        assert result is False
        mock_dialog.assert_called_once_with(
            "予期しないエラーが発生しました: Unexpected error", "エラー"
        )


class TestMainFunctionPlamo:
    """Test cases for main function."""

    def test_main_with_stdin(self, mocker):
        """Test main function with stdin input."""
        mock_stdin = mocker.patch("sys.stdin")
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = "Hello from stdin\n"

        mock_translator = mocker.patch("translate_plamo.PlamoTranslator")
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

        mocker.patch("sys.argv", ["translate_plamo.py", "Hello", "World"])

        mock_translator = mocker.patch("translate_plamo.PlamoTranslator")
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

        mocker.patch("sys.argv", ["translate_plamo.py"])

        mock_translator = mocker.patch("translate_plamo.PlamoTranslator")
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

        mock_translator = mocker.patch("translate_plamo.PlamoTranslator")
        mock_instance = MagicMock()
        mock_instance.run.return_value = False
        mock_translator.return_value = mock_instance

        mock_exit = mocker.patch("sys.exit")

        main()

        mock_instance.run.assert_called_once_with("Test input")
        mock_exit.assert_called_once_with(1)
