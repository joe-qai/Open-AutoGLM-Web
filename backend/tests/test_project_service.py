"""Tests for ProjectService."""

import pytest
from app.services.project_service import ProjectService
from app.schemas.project import ProjectCreate, ProjectUpdate


@pytest.fixture
def service():
    return ProjectService()


@pytest.mark.asyncio
async def test_create_and_get_project(service):
    created = await service.create_project(
        ProjectCreate(name="My Project", description="A test project")
    )
    assert created.project_id is not None
    assert created.name == "My Project"
    assert created.description == "A test project"

    fetched = await service.get_project(created.project_id)
    assert fetched is not None
    assert fetched.name == "My Project"
    assert fetched.project_id == created.project_id


@pytest.mark.asyncio
async def test_get_project_not_found(service):
    project = await service.get_project("nonexistent")
    assert project is None


@pytest.mark.asyncio
async def test_list_projects(service):
    await service.create_project(ProjectCreate(name="P1", description="Project 1"))
    await service.create_project(ProjectCreate(name="P2", description="Project 2"))

    all_projects = await service.list_projects()
    assert len(all_projects) >= 2


@pytest.mark.asyncio
async def test_list_projects_ordered_by_created_at(service):
    p1 = await service.create_project(ProjectCreate(name="First", description="desc"))
    p2 = await service.create_project(ProjectCreate(name="Second", description="desc"))

    all_projects = await service.list_projects()
    assert all_projects[0].name == "Second"
    assert all_projects[1].name == "First"


@pytest.mark.asyncio
async def test_update_project(service):
    created = await service.create_project(
        ProjectCreate(name="Before", description="desc")
    )
    updated = await service.update_project(
        created.project_id,
        ProjectUpdate(name="After")
    )
    assert updated is not None
    assert updated.name == "After"
    assert updated.description == "desc"


@pytest.mark.asyncio
async def test_update_project_not_found(service):
    updated = await service.update_project("nonexistent", ProjectUpdate(name="new"))
    assert updated is None


@pytest.mark.asyncio
async def test_delete_project(service):
    created = await service.create_project(ProjectCreate(name="Delete me", description="desc"))
    deleted = await service.delete_project(created.project_id)
    assert deleted is True
    fetched = await service.get_project(created.project_id)
    assert fetched is None


@pytest.mark.asyncio
async def test_delete_project_not_found(service):
    deleted = await service.delete_project("nonexistent")
    assert deleted is False
