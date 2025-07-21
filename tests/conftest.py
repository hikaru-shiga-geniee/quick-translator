#!/usr/bin/env python3
"""Common test configuration and fixtures."""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_environment():
    """Auto-use fixture to mock environment variables for all tests."""
    with patch.dict('os.environ', {}, clear=True):
        yield


@pytest.fixture
def mock_api_key():
    """Fixture providing a mock API key."""
    return 'sk-test-api-key-12345'


@pytest.fixture
def mock_translation_response():
    """Fixture providing a mock OpenAI API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": "Mock translation result"
                }
            }
        ]
    }


@pytest.fixture
def mock_api_error_response():
    """Fixture providing a mock OpenAI API error response."""
    return {
        "error": {
            "message": "Mock API error",
            "type": "invalid_request_error"
        }
    } 
