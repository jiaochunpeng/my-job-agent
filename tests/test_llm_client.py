import pytest
from src.llm_client import get_llm_client

def test_get_llm_client_defaults(mock_env_vars):
    client = get_llm_client()
    assert client.model == "gpt-4o"
    assert client.api_key == "test-key"

def test_get_llm_client_custom():
    client = get_llm_client(model="gpt-4o-mini", api_key="custom-key")
    assert client.model == "gpt-4o-mini"
    assert client.api_key == "custom-key"
