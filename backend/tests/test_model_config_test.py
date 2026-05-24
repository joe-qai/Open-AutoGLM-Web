"""Tests for model config test endpoint."""

import pytest
from unittest.mock import patch, MagicMock
from app.schemas.model_config import ModelConfigCreate, ModelConfigTestResponse
from app.services.model_config_service import ModelConfigService


@pytest.fixture
def service():
    return ModelConfigService()


@pytest.mark.asyncio
async def test_test_openai_success(service):
    config = ModelConfigCreate(
        name="test",
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_name="gpt-4o",
    )
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "OK"

    with patch("app.services.model_config_service.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        result = await service.test_config(config)

    assert result.success is True
    assert result.message == "连接成功"
    assert result.response_time_ms is not None


@pytest.mark.asyncio
async def test_test_openai_auth_error(service):
    config = ModelConfigCreate(
        name="test",
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-bad",
        model_name="gpt-4o",
    )

    with patch("app.services.model_config_service.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        from openai import AuthenticationError
        mock_client.chat.completions.create.side_effect = AuthenticationError(
            "Invalid API key provided",
            response=MagicMock(),
            body=None,
        )

        result = await service.test_config(config)

    assert result.success is False
    assert "API Key" in result.message


@pytest.mark.asyncio
async def test_test_openai_model_not_found(service):
    config = ModelConfigCreate(
        name="test",
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_name="nonexistent-model",
    )

    with patch("app.services.model_config_service.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        from openai import NotFoundError
        mock_client.chat.completions.create.side_effect = NotFoundError(
            "Model not found",
            response=MagicMock(),
            body=None,
        )

        result = await service.test_config(config)

    assert result.success is False
    assert "不存在" in result.message


@pytest.mark.asyncio
async def test_test_openai_timeout(service):
    config = ModelConfigCreate(
        name="test",
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_name="gpt-4o",
    )

    with patch("app.services.model_config_service.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        from openai import APITimeoutError
        mock_client.chat.completions.create.side_effect = APITimeoutError("Request timed out")

        result = await service.test_config(config)

    assert result.success is False
    assert "超时" in result.message


@pytest.mark.asyncio
async def test_test_openai_connection_error(service):
    config = ModelConfigCreate(
        name="test",
        provider="openai",
        base_url="https://invalid-url.com",
        api_key="sk-test",
        model_name="gpt-4o",
    )

    with patch("app.services.model_config_service.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        from openai import APIConnectionError
        import httpx
        mock_request = httpx.Request("POST", "https://invalid-url.com/v1/chat/completions")
        mock_client.chat.completions.create.side_effect = APIConnectionError(
            message="Connection refused", request=mock_request
        )

        result = await service.test_config(config)

    assert result.success is False
    assert "服务器" in result.message


@pytest.mark.asyncio
async def test_test_unsupported_provider(service):
    config = ModelConfigCreate(
        name="test",
        provider="anthropic",
        base_url="https://api.anthropic.com",
        api_key="sk-ant-test",
        model_name="claude-3-5-sonnet-20240620",
    )

    result = await service.test_config(config)

    assert result.success is False
