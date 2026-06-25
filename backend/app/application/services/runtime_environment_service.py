import json
from typing import Any, Dict, Optional

from app.domain.common.exceptions import (
    RuntimeEnvironmentConflictError,
    RuntimeEnvironmentNotFoundError,
    RuntimeEnvironmentValidationError,
)
from app.infrastructure.db.models import RuntimeEnvironmentModel
from app.infrastructure.repositories import RuntimeEnvironmentRepository

SUPPORTED_ENV_TYPES = {"python", "conda", "docker"}


def _serialize_runtime_environment(runtime_environment: RuntimeEnvironmentModel) -> Dict[str, Any]:
    return {
        "id": runtime_environment.id,
        "code": runtime_environment.code,
        "name": runtime_environment.name,
        "description": runtime_environment.description,
        "env_type": runtime_environment.env_type,
        "python_path": runtime_environment.python_path,
        "working_dir": runtime_environment.working_dir,
        "docker_image": runtime_environment.docker_image,
        "extra_env": json.loads(runtime_environment.extra_env_json),
        "is_active": runtime_environment.is_active,
        "created_at": runtime_environment.created_at.isoformat()
        if runtime_environment.created_at
        else None,
        "updated_at": runtime_environment.updated_at.isoformat()
        if runtime_environment.updated_at
        else None,
    }


class RuntimeEnvironmentService:
    def __init__(
        self,
        *,
        runtime_environment_repository: RuntimeEnvironmentRepository,
    ) -> None:
        self._runtime_environment_repository = runtime_environment_repository

    def list_runtime_environments(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        code: Optional[str] = None,
        name: Optional[str] = None,
        env_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        items, total = self._runtime_environment_repository.list_paginated(
            page=page,
            page_size=page_size,
            code=code.strip() if isinstance(code, str) and code.strip() else None,
            name=name.strip() if isinstance(name, str) and name.strip() else None,
            env_type=env_type.strip() if isinstance(env_type, str) and env_type.strip() else None,
            is_active=is_active,
        )
        return {
            "items": [_serialize_runtime_environment(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_runtime_environment(self, runtime_environment_id: int) -> Dict[str, Any]:
        runtime_environment = self._runtime_environment_repository.get_by_id(runtime_environment_id)
        if runtime_environment is None:
            raise RuntimeEnvironmentNotFoundError(
                "Runtime environment '%s' was not found" % runtime_environment_id
            )
        return _serialize_runtime_environment(runtime_environment)

    def create_runtime_environment(
        self,
        *,
        code: str,
        name: str,
        description: Optional[str],
        env_type: str,
        python_path: Optional[str],
        working_dir: Optional[str],
        docker_image: Optional[str],
        extra_env: Optional[dict[str, str]],
        is_active: bool,
    ) -> Dict[str, Any]:
        normalized = self._validate_payload(
            code=code,
            name=name,
            description=description,
            env_type=env_type,
            python_path=python_path,
            working_dir=working_dir,
            docker_image=docker_image,
            extra_env=extra_env,
            is_active=is_active,
        )
        self._assert_unique_code(normalized["code"])
        saved = self._runtime_environment_repository.add(
            RuntimeEnvironmentModel(
                code=normalized["code"],
                name=normalized["name"],
                description=normalized["description"],
                env_type=normalized["env_type"],
                python_path=normalized["python_path"],
                working_dir=normalized["working_dir"],
                docker_image=normalized["docker_image"],
                extra_env_json=json.dumps(normalized["extra_env"], ensure_ascii=True, sort_keys=True),
                is_active=normalized["is_active"],
            )
        )
        self._runtime_environment_repository.commit()
        return _serialize_runtime_environment(saved)

    def update_runtime_environment(
        self,
        runtime_environment_id: int,
        *,
        code: str,
        name: str,
        description: Optional[str],
        env_type: str,
        python_path: Optional[str],
        working_dir: Optional[str],
        docker_image: Optional[str],
        extra_env: Optional[dict[str, str]],
        is_active: bool,
    ) -> Dict[str, Any]:
        existing = self._runtime_environment_repository.get_by_id(runtime_environment_id)
        if existing is None:
            raise RuntimeEnvironmentNotFoundError(
                "Runtime environment '%s' was not found" % runtime_environment_id
            )
        normalized = self._validate_payload(
            code=code,
            name=name,
            description=description,
            env_type=env_type,
            python_path=python_path,
            working_dir=working_dir,
            docker_image=docker_image,
            extra_env=extra_env,
            is_active=is_active,
        )
        self._assert_unique_code(normalized["code"], exclude_id=runtime_environment_id)
        existing.code = normalized["code"]
        existing.name = normalized["name"]
        existing.description = normalized["description"]
        existing.env_type = normalized["env_type"]
        existing.python_path = normalized["python_path"]
        existing.working_dir = normalized["working_dir"]
        existing.docker_image = normalized["docker_image"]
        existing.extra_env_json = json.dumps(
            normalized["extra_env"],
            ensure_ascii=True,
            sort_keys=True,
        )
        existing.is_active = normalized["is_active"]
        saved = self._runtime_environment_repository.save(existing)
        self._runtime_environment_repository.commit()
        return _serialize_runtime_environment(saved)

    def delete_runtime_environment(self, runtime_environment_id: int) -> bool:
        existing = self._runtime_environment_repository.get_by_id(runtime_environment_id)
        if existing is None:
            raise RuntimeEnvironmentNotFoundError(
                "Runtime environment '%s' was not found" % runtime_environment_id
            )
        self._runtime_environment_repository.delete(existing)
        self._runtime_environment_repository.commit()
        return True

    def _assert_unique_code(self, code: str, exclude_id: Optional[int] = None) -> None:
        existing = self._runtime_environment_repository.get_by_code(code)
        if existing is not None and existing.id != exclude_id:
            raise RuntimeEnvironmentConflictError(
                "Runtime environment code '%s' already exists" % code
            )

    def _validate_payload(
        self,
        *,
        code: str,
        name: str,
        description: Optional[str],
        env_type: str,
        python_path: Optional[str],
        working_dir: Optional[str],
        docker_image: Optional[str],
        extra_env: Optional[dict[str, str]],
        is_active: bool,
    ) -> Dict[str, Any]:
        normalized_code = code.strip()
        if not normalized_code:
            raise RuntimeEnvironmentValidationError("Runtime environment code must not be empty")

        normalized_name = name.strip()
        if not normalized_name:
            raise RuntimeEnvironmentValidationError("Runtime environment name must not be empty")

        normalized_env_type = env_type.strip().lower()
        if normalized_env_type not in SUPPORTED_ENV_TYPES:
            raise RuntimeEnvironmentValidationError(
                "Runtime environment env_type must be one of: conda, docker, python"
            )

        normalized_python_path = self._normalize_optional_string(python_path)
        normalized_working_dir = self._normalize_optional_string(working_dir)
        normalized_docker_image = self._normalize_optional_string(docker_image)
        normalized_description = self._normalize_optional_string(description)

        if normalized_env_type in {"python", "conda"} and not normalized_python_path:
            raise RuntimeEnvironmentValidationError(
                "Runtime environment python_path is required for python/conda env_type"
            )
        if normalized_env_type == "docker" and not normalized_docker_image:
            raise RuntimeEnvironmentValidationError(
                "Runtime environment docker_image is required for docker env_type"
            )

        if extra_env is None:
            normalized_extra_env: dict[str, str] = {}
        else:
            if not isinstance(extra_env, dict):
                raise RuntimeEnvironmentValidationError(
                    "Runtime environment extra_env must be an object when provided"
                )
            normalized_extra_env = {}
            for raw_key, raw_value in extra_env.items():
                if not isinstance(raw_key, str) or not raw_key.strip():
                    raise RuntimeEnvironmentValidationError(
                        "Runtime environment extra_env keys must be non-empty strings"
                    )
                if not isinstance(raw_value, str):
                    raise RuntimeEnvironmentValidationError(
                        "Runtime environment extra_env values must be strings"
                    )
                normalized_extra_env[raw_key.strip()] = raw_value

        return {
            "code": normalized_code,
            "name": normalized_name,
            "description": normalized_description,
            "env_type": normalized_env_type,
            "python_path": normalized_python_path,
            "working_dir": normalized_working_dir,
            "docker_image": normalized_docker_image,
            "extra_env": normalized_extra_env,
            "is_active": bool(is_active),
        }

    def _normalize_optional_string(self, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None
