"""Tests for ApkService."""

import pytest
from app.services.apk_service import ApkService


@pytest.fixture
def service():
    return ApkService()


@pytest.mark.asyncio
async def test_list_apks_empty(service):
    apks = await service.list_apks()
    assert apks == []


@pytest.mark.asyncio
async def test_get_apk_not_found(service):
    apk = await service.get_apk("nonexistent")
    assert apk is None


@pytest.mark.asyncio
async def test_delete_apk_not_found(service):
    result = await service.delete_apk("nonexistent")
    assert result.success is False
    assert "not found" in result.message.lower()


@pytest.mark.asyncio
async def test_delete_apk_batch_empty(service):
    result = await service.delete_apk_batch([])
    assert result.success is True


@pytest.mark.asyncio
async def test_delete_apk_batch_all_non_existent(service):
    result = await service.delete_apk_batch(["nope1", "nope2"])
    assert result.success is True


class FakeFile:
    def __init__(self, content: bytes):
        self._content = content

    async def read(self):
        return self._content


@pytest.mark.asyncio
async def test_upload_apk(service):
    fake_file = FakeFile(b"fake_apk_content")
    result = await service.upload_apk(fake_file, "test.apk")
    assert result.success is True
    assert result.apk is not None
    assert result.apk.name == "test.apk"
    assert result.apk.file_size == len(b"fake_apk_content")
    assert result.apk.id is not None

    fetched = await service.get_apk(result.apk.id)
    assert fetched is not None
    assert fetched.name == "test.apk"


@pytest.mark.asyncio
async def test_upload_and_delete_apk(service):
    fake_file = FakeFile(b"delete_me")
    upload = await service.upload_apk(fake_file, "delete_me.apk")
    apk_id = upload.apk.id

    result = await service.delete_apk(apk_id)
    assert result.success is True

    fetched = await service.get_apk(apk_id)
    assert fetched is None
