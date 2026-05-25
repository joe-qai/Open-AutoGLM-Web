"""Tests for model config test endpoint."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.schemas.model_config import ModelConfigCreate
from app.services.model_config_service import ModelConfigService


@pytest.fixture
def service():
    return ModelConfigService()


def _mock_response(status=200, text='{"choices":[{"message":{"content":"OK"}}]}', content_type="application/json"):
    m = MagicMock()
    m.status_code = status
    m.text = text
    m.headers = {"content-type": content_type}
    m.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
    return m


@pytest.mark.asyncio
async def test_test_openai_success(service):
    config = ModelConfigCreate(
        name="test", provider="openai",
        base_url="https://api.openai.com/v1", api_key="sk-test", model_name="gpt-4o",
    )
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=_mock_response())

        result = await service.test_config(config)

    assert result.success is True
    assert result.message == "连接成功"
    assert result.response_time_ms is not None


@pytest.mark.asyncio
async def test_test_openai_auth_error(service):
    config = ModelConfigCreate(
        name="test", provider="openai",
        base_url="https://api.openai.com/v1", api_key="sk-bad", model_name="gpt-4o",
    )
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=_mock_response(status=401, text='{"detail":"Invalid API key"}'))

        result = await service.test_config(config)

    assert result.success is False
    assert "API Key" in result.message


@pytest.mark.asyncio
async def test_test_openai_model_not_found(service):
    config = ModelConfigCreate(
        name="test", provider="openai",
        base_url="https://api.openai.com/v1", api_key="sk-test", model_name="nonexistent",
    )
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=_mock_response(status=404, text='{"error":"not found"}'))

        result = await service.test_config(config)

    assert result.success is False
    assert "不存在" in result.message


@pytest.mark.asyncio
async def test_test_openai_timeout(service):
    config = ModelConfigCreate(
        name="test", provider="openai",
        base_url="https://api.openai.com/v1", api_key="sk-test", model_name="gpt-4o",
    )
    with patch("httpx.AsyncClient") as mock_cls:
        import httpx
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        result = await service.test_config(config)

    assert result.success is False
    assert "超时" in result.message


@pytest.mark.asyncio
async def test_test_openai_connection_error(service):
    config = ModelConfigCreate(
        name="test", provider="openai",
        base_url="https://invalid-url.com", api_key="sk-test", model_name="gpt-4o",
    )
    with patch("httpx.AsyncClient") as mock_cls:
        import httpx
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        result = await service.test_config(config)

    assert result.success is False
    assert "服务器" in result.message


@pytest.mark.asyncio
async def test_test_openai_sse_response(service):
    config = ModelConfigCreate(
        name="test", provider="openai",
        base_url="https://api.openai.com/v1", api_key="sk-test", model_name="glm-5.1",
    )
    sse_body = (
        'data: {"id":"x","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":"1"}}]}\n'
        'data: {"id":"x","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"2"}}]}\n'
        'data: [DONE]\n'
    )
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=_mock_response(status=200, text=sse_body, content_type="text/event-stream"))

        result = await service.test_config(config)

    assert result.success is True
    assert result.message == "连接成功"


@pytest.mark.asyncio
async def test_test_openai_json_no_content(service):
    config = ModelConfigCreate(
        name="test", provider="openai",
        base_url="https://api.openai.com/v1", api_key="sk-test", model_name="gpt-4o",
    )
    resp = _mock_response(text='{"choices":[{"message":{"content":""}}]}')
    resp.json.return_value = {"choices": [{"message": {"content": ""}}]}
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.post = AsyncMock(return_value=resp)

        result = await service.test_config(config)

    assert result.success is False


@pytest.mark.asyncio
async def test_test_anthropic_sdk_not_installed(service):
    config = ModelConfigCreate(
        name="test", provider="anthropic",
        base_url="https://api.anthropic.com", api_key="sk-ant-test", model_name="claude-3-5-sonnet-20240620",
    )

    result = await service.test_config(config)

    assert result.success is False


@pytest.mark.asyncio
async def test_classify_error_redacts_api_key(service):
    safe = ModelConfigService._classify_error(
        Exception("some error with key sk-12345 inside"),
        api_key="sk-12345",
    )
    assert "sk-12345" not in safe
    assert "***" in safe


@pytest.mark.asyncio
async def test_classify_error_unknown_error(service):
    safe = ModelConfigService._classify_error(Exception("weird error"))
    assert "连接失败" in safe
    assert "weird error" in safe
