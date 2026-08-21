from pathlib import Path
from typing import Any

import yaml

from tickets.repository import (
    EPICS_DIR_NAME,
    TASKS_DIR_NAME,
    TICKETS_DIR_NAME,
    YAML_FILE_PATTERN,
    RepositoryError,
    TicketRepository,
    read_yaml_file,
)

TICKETS_ROOT_DIR_NAME = ".tickets"
DEPENDS_ON_FIELD_NAME = "depends_on"
DEFAULT_DEPENDS_ON_VALUE: list[str] = []


def upgrade_repository_metadata(root_path: Path) -> list[str]:
    update_messages: list[str] = []

    repository = TicketRepository(root_path)

    update_messages.extend(
        add_default_depends_on_to_directory(
            root_path / TICKETS_ROOT_DIR_NAME / TASKS_DIR_NAME,
        )
    )
    update_messages.extend(
        add_default_depends_on_to_directory(
            root_path / TICKETS_ROOT_DIR_NAME / EPICS_DIR_NAME,
        )
    )
    update_messages.extend(
        add_default_depends_on_to_directory(
            root_path / TICKETS_ROOT_DIR_NAME / TICKETS_DIR_NAME,
        )
    )

    # Ensure upgraded metadata still satisfies repository validation rules.
    repository.load_all()

    return update_messages


def add_default_depends_on_to_directory(entity_directory_path: Path) -> list[str]:
    if not entity_directory_path.exists():
        return []

    update_messages: list[str] = []
    entity_file_paths = sorted(entity_directory_path.glob(YAML_FILE_PATTERN))

    for entity_file_path in entity_file_paths:
        entity_data = read_yaml_file(entity_file_path)
        if not isinstance(entity_data, dict):
            raise RepositoryError(f"Expected mapping in file: {entity_file_path}")

        if DEPENDS_ON_FIELD_NAME in entity_data:
            continue

        entity_id = entity_data.get("id")
        if not isinstance(entity_id, str):
            raise RepositoryError(f"Missing or invalid 'id' field in file: {entity_file_path}")

        entity_data[DEPENDS_ON_FIELD_NAME] = DEFAULT_DEPENDS_ON_VALUE.copy()
        write_yaml_mapping(entity_file_path, entity_data)
        update_messages.append(
            f'{entity_id}: Added default "depends_on" with value "[]"'
        )

    return update_messages


def write_yaml_mapping(file_path: Path, data: dict[str, Any]) -> None:
    with file_path.open("w", encoding="utf-8") as file_handle:
        yaml.safe_dump(data, file_handle, sort_keys=False)