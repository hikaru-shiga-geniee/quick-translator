#!/usr/bin/env python3
"""Run tests across multiple Python versions using uv."""

import re
import subprocess
import sys


def get_installed_python_versions() -> list[str]:
    """Get list of installed Python versions from uv."""
    try:
        result = subprocess.run(
            ["uv", "python", "list", "--only-installed"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print(f"Warning: Failed to get installed Python versions: {result.stderr}")
            return []

        # Parse the output to extract version numbers
        versions: set[str] = set()
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue

            # Extract version from lines like "cpython-3.12.8-macos-aarch64-none"
            match = re.search(r"cpython-(\d+\.\d+)", line)
            if match:
                version = match.group(1)
                versions.add(version)

        # Sort versions
        version_list = sorted(
            list(versions), key=lambda x: tuple(map(int, x.split(".")))
        )

        if not version_list:
            print("Warning: No Python versions found. Using fallback versions.")
            return ["3.10", "3.11", "3.12"]  # Fallback versions

        print(f"Found installed Python versions: {', '.join(version_list)}")
        return version_list

    except Exception as e:
        print(f"Error getting installed Python versions: {e}")
        print("Using fallback versions.")
        return ["3.10", "3.11", "3.12"]  # Fallback versions


def run_tests_for_version(python_version: str) -> tuple[bool, str]:
    """Run tests for a specific Python version."""
    print(f"\n{'=' * 60}")
    print(f"Running tests for Python {python_version}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(
            ["uv", "run", "--python", python_version, "pytest"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        success = result.returncode == 0
        output = result.stdout + result.stderr

        if success:
            print(f"✅ Python {python_version}: PASSED")
        else:
            print(f"❌ Python {python_version}: FAILED")
            print("Error output:")
            print(result.stderr)

        return success, output

    except subprocess.TimeoutExpired:
        print(f"⏰ Python {python_version}: TIMEOUT")
        return False, "Test execution timed out"
    except Exception as e:
        print(f"💥 Python {python_version}: ERROR - {e}")
        return False, str(e)


def main():
    """Run tests for all installed Python versions."""
    print("🧪 Running tests across multiple Python versions")
    print("🔍 Detecting installed Python versions...")

    python_versions = get_installed_python_versions()

    if not python_versions:
        print("❌ No Python versions found. Exiting.")
        sys.exit(1)

    print(f"📋 Versions to test: {', '.join(python_versions)}")

    results: list[tuple[str, bool, str]] = []

    # Run tests for each Python version
    for version in python_versions:
        success, output = run_tests_for_version(version)
        results.append((version, success, output))

    # Summary
    print(f"\n{'=' * 60}")
    print("TEST SUMMARY")
    print(f"{'=' * 60}")

    passed = 0
    failed = 0

    for version, success, _ in results:
        status = "PASSED" if success else "FAILED"
        icon = "✅" if success else "❌"
        print(f"{icon} Python {version}: {status}")

        if success:
            passed += 1
        else:
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")

    # Exit with appropriate code
    if failed > 0:
        print("\n❌ Some tests failed. See output above for details.")
        sys.exit(1)
    else:
        print("\n🎉 All tests passed across all Python versions!")
        sys.exit(0)


if __name__ == "__main__":
    main()
