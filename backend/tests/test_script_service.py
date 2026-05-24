"""Tests for ScriptService."""

import pytest
from app.services.script_service import ScriptService
from app.schemas.script import ScriptType, ScriptUpdate


@pytest.fixture
def service():
    return ScriptService()


@pytest.mark.asyncio
async def test_create_and_get_script(service):
    script_id = await service.create_script(
        name="test_script",
        content="print('hello')",
        script_type="ai_generated",
        platform="android",
        description="A test script",
    )
    assert script_id.startswith("script_")

    script = await service.get_script(script_id)
    assert script is not None
    assert script.name == "test_script"
    assert script.content == "print('hello')"
    assert script.script_type == ScriptType.AI_GENERATED
    assert script.platform == "android"
    assert script.description == "A test script"
    assert script.version == 1


@pytest.mark.asyncio
async def test_get_script_not_found(service):
    script = await service.get_script("nonexistent")
    assert script is None


@pytest.mark.asyncio
async def test_update_script_content(service):
    script_id = await service.create_script(
        name="update_test", content="v1", script_type="manual", platform="ios"
    )
    updated = await service.update_script(
        script_id, ScriptUpdate(content="v2")
    )
    assert updated is not None
    assert updated.content == "v2"
    assert updated.version == 2


@pytest.mark.asyncio
async def test_update_script_not_found(service):
    updated = await service.update_script("nonexistent", ScriptUpdate(name="new"))
    assert updated is None


@pytest.mark.asyncio
async def test_delete_script(service):
    script_id = await service.create_script(
        name="del_test", content="delete me", script_type="manual", platform="android"
    )
    await service.delete_script(script_id)
    script = await service.get_script(script_id)
    assert script is None


@pytest.mark.asyncio
async def test_list_scripts(service):
    await service.create_script(name="a", content="1", script_type="ai_generated", platform="android")
    await service.create_script(name="b", content="2", script_type="manual", platform="ios")

    all_scripts = await service.list_scripts()
    assert len(all_scripts) >= 2

    ios_scripts = await service.list_scripts(platform="ios")
    assert len(ios_scripts) == 1
    assert ios_scripts[0].name == "b"


@pytest.mark.asyncio
async def test_list_scripts_with_pagination(service):
    for i in range(5):
        await service.create_script(name=f"s{i}", content=str(i), script_type="ai_generated", platform="android")

    page = await service.list_scripts(skip=0, limit=2)
    assert len(page) == 2
    next_page = await service.list_scripts(skip=2, limit=2)
    assert len(next_page) == 2
    assert next_page[0].name != page[0].name


@pytest.mark.asyncio
async def test_save_script_version(service):
    script_id = await service.create_script(
        name="vers", content="v1", script_type="manual", platform="android"
    )
    version_label = await service.save_script_version(script_id, "v2")
    assert version_label == "v2"
    script = await service.get_script(script_id)
    assert script.content == "v2"
    assert script.version == 2


@pytest.mark.asyncio
async def test_get_script_versions(service):
    script_id = await service.create_script(
        name="vers_test", content="v1", script_type="manual", platform="android"
    )
    versions = await service.get_script_versions(script_id)
    assert len(versions) == 1
    assert versions[0]["content"] == "v1"

    await service.save_script_version(script_id, "v2")
    versions = await service.get_script_versions(script_id)
    assert len(versions) == 1
    assert versions[0]["version_number"] == 2


@pytest.mark.asyncio
async def test_derive_script(service):
    original_id = await service.create_script(
        name="original", content="orig", script_type="ai_generated",
        platform="android", description="test derive"
    )
    derived_id = await service.derive_script(original_id, "ios")
    assert derived_id != ""

    derived = await service.get_script(derived_id)
    assert derived is not None
    assert derived.platform == "ios"
    assert derived.name == "original (ios)"


@pytest.mark.asyncio
async def test_generate_script_creates_ai_generated(service):
    script_id = await service.generate_script(
        task_description="Open app and click button",
        platform="android"
    )
    script = await service.get_script(script_id)
    assert script is not None
    assert script.script_type == ScriptType.AI_GENERATED
    assert "Open app and click button" in script.content


@pytest.mark.asyncio
async def test_generate_script_content_android(service):
    content = service._generate_script_content("Test task", "android")
    assert "uiautomator2" in content
    assert "Test task" in content


@pytest.mark.asyncio
async def test_generate_script_content_ios(service):
    content = service._generate_script_content("iOS task", "ios")
    assert "XCTest" in content
    assert "iOS task" in content


@pytest.mark.asyncio
async def test_generate_script_content_harmonyos(service):
    content = service._generate_script_content("Harmony test", "harmonyos")
    assert "Hypium" in content
    assert "Harmony test" in content


@pytest.mark.asyncio
async def test_generate_script_content_unknown(service):
    content = service._generate_script_content("generic", "unknown")
    assert "Generic Script" in content


@pytest.mark.asyncio
async def test_execute_script_creates_task(service):
    script_id = await service.create_script(
        name="exec_test", content="print('ok')", script_type="manual", platform="android"
    )
    task_id = await service.execute_script(script_id, device_id="dev-1")
    assert task_id != ""
    assert task_id.startswith("task_")
