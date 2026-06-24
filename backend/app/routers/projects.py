import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.config import Settings, get_settings
from app.schemas import (
    ApiEnvelope,
    ProjectCreateRequest,
    ProjectUpdateRequest,
)
from app.storage import ProjectStorage

router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_storage(settings: Settings = Depends(get_settings)) -> ProjectStorage:
    return ProjectStorage(settings)


@router.post("", response_model=ApiEnvelope)
def create_project(
    request: ProjectCreateRequest,
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    project = storage.create_project(request)
    return ApiEnvelope(data=project.model_dump(mode="json"))


@router.get("", response_model=ApiEnvelope)
def list_projects(storage: ProjectStorage = Depends(get_storage)) -> ApiEnvelope:
    projects = [project.model_dump(mode="json") for project in storage.list_projects()]
    return ApiEnvelope(data={"projects": projects})


@router.get("/{project_id}", response_model=ApiEnvelope)
def get_project(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    try:
        project = storage.get_project(project_id)
        return ApiEnvelope(data=project.model_dump(mode="json"))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{project_id}", response_model=ApiEnvelope)
def update_project(
    project_id: str,
    request: ProjectUpdateRequest,
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    try:
        project = storage.update_project(project_id, request)
        return ApiEnvelope(data=project.model_dump(mode="json"))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{project_id}", response_model=ApiEnvelope)
def delete_project(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> ApiEnvelope:
    try:
        storage.delete_project(project_id)
        return ApiEnvelope(data={"deleted": True, "project_id": project_id})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{project_id}/scenes.json")
def export_scenes_json(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> Response:
    try:
        payload = storage.scenes_export(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="scenes.json"'},
    )


@router.get("/{project_id}/export.zip")
def export_project_zip(
    project_id: str,
    storage: ProjectStorage = Depends(get_storage),
) -> Response:
    try:
        zip_bytes = storage.build_export_zip(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="project-{project_id[:8]}.zip"'},
    )
