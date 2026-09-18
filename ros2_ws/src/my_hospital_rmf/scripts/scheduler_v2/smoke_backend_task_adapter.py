#!/usr/bin/env python3

from scheduler_v2.backend_task_adapter import (
    build_scheduler_task,
)

from scheduler_v2.rmf_places import (
    load_places_from_nav_graph,
)


NAV_GRAPH = "../nav_graphs/0.yaml"


def main():

    places = (
        load_places_from_nav_graph(
            NAV_GRAPH
        )
    )

    # 模擬 .NET Backend 真正送出的 payload
    task = (
        build_scheduler_task(
            task_id="test-task-001",
            task_type="medicine_delivery",
            source="pharmacy",
            destination="ward_a",
            priority=2,
            required_capabilities=[
                "navigation",
                "medicine_delivery",
            ],
            places=places,
        )
    )

    print(
        "=" * 80
    )

    print(
        "BACKEND TASK -> SCHEDULER TASK"
    )

    print(
        "=" * 80
    )

    print(
        "Task ID       :",
        task.task_id,
    )

    print(
        "Task Type     :",
        task.task_type,
    )

    print(
        "Source        :",
        task.source,
    )

    print(
        "Destination   :",
        task.destination,
    )

    print(
        "Priority      :",
        task.priority,
    )

    print(
        "Capabilities  :",
        sorted(
            task.required_capabilities
        ),
    )

    print(
        "Status        :",
        task.status,
    )

    print(
        "Created At    :",
        task.created_at,
    )

    assert (
        task.task_type
        ==
        "medicine_delivery"
    )

    assert (
        task.source
        ==
        "pharmacy"
    )

    assert (
        task.destination
        ==
        "ward_a"
    )

    assert (
        task.required_capabilities
        ==
        {
            "navigation",
            "medicine_delivery",
        }
    )

    print()

    print(
        "=" * 80
    )

    print(
        "BACKEND -> SCHEDULER TASK: PASS"
    )

    print(
        "=" * 80
    )


if __name__ == "__main__":

    main()
