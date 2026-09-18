#!/usr/bin/env python3

import time

from scheduler_v2.models import Task
from scheduler_v2.runtime import Place

from scheduler_v2.capabilities import (
    VALID_TASK_TYPES,
    VALID_CAPABILITIES,
)


def build_scheduler_task(
    *,
    task_id: str,
    task_type: str,
    source: str,
    destination: str,
    priority: int,
    required_capabilities: list[str] | set[str],
    places: dict[str, Place],
    created_at: float | None = None,
) -> Task:
    """
    將 Backend / ROS Bridge 的 Task Payload
    轉成 scheduler_v2.models.Task。

    此處負責：
    - Task type validation
    - source / destination validation
    - capability validation
    - priority validation 交給 Task model
    """

    task_id = str(task_id).strip()
    task_type = str(task_type).strip()
    source = str(source).strip()
    destination = str(destination).strip()

    if not task_id:

        raise ValueError(
            "task_id cannot be empty"
        )

    if task_type not in VALID_TASK_TYPES:

        raise ValueError(
            "Unsupported task_type: "
            f"{task_type}"
        )

    if source not in places:

        raise ValueError(
            "Unknown source place: "
            f"{source}"
        )

    if destination not in places:

        raise ValueError(
            "Unknown destination place: "
            f"{destination}"
        )

    capabilities = {
        str(capability).strip()
        for capability
        in required_capabilities
    }

    invalid_capabilities = (
        capabilities
        -
        VALID_CAPABILITIES
    )

    if invalid_capabilities:

        raise ValueError(
            "Unsupported capabilities: "
            + ", ".join(
                sorted(
                    invalid_capabilities
                )
            )
        )

    if created_at is None:

        created_at = time.time()

    return Task(
        task_id=task_id,
        task_type=task_type,
        source=source,
        destination=destination,
        priority=int(priority),
        required_capabilities=(
            capabilities
        ),
        status="pending",
        assigned_robot=None,
        created_at=float(
            created_at
        ),
    )
