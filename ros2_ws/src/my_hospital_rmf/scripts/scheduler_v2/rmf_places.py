#!/usr/bin/env python3

from pathlib import Path

import yaml

from scheduler_v2.runtime import Place


def load_places_from_nav_graph(
    nav_graph_path: str | Path,
    level_name: str = "L1",
) -> dict[str, Place]:
    """
    從 RMF nav graph 讀取所有有 name 的 vertex，
    轉成 Scheduler v2 使用的 Place。

    例如：

        pharmacy
        lab
        nurse_station
        ward_a
        ward_b
        storage
        charging_station
    """

    nav_graph_path = Path(
        nav_graph_path
    )

    if not nav_graph_path.exists():

        raise FileNotFoundError(
            f"Nav graph not found: "
            f"{nav_graph_path}"
        )

    with nav_graph_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = yaml.safe_load(
            file
        )

    levels = data.get(
        "levels",
        {},
    )

    if level_name not in levels:

        raise ValueError(
            "Level not found in nav graph: "
            f"{level_name}"
        )

    vertices = (
        levels[
            level_name
        ]
        .get(
            "vertices",
            [],
        )
    )

    places: dict[
        str,
        Place,
    ] = {}

    for vertex in vertices:

        if len(vertex) < 3:

            continue

        x = float(
            vertex[0]
        )

        y = float(
            vertex[1]
        )

        params = (
            vertex[2]
            if isinstance(
                vertex[2],
                dict,
            )
            else {}
        )

        name = str(
            params.get(
                "name",
                "",
            )
        ).strip()

        if not name:

            continue

        if name in places:

            raise ValueError(
                "Duplicate waypoint name "
                f"in nav graph: {name}"
            )

        places[
            name
        ] = Place(
            place_id=name,
            x=x,
            y=y,
            map_name=(
                level_name
            ),
        )

    if not places:

        raise RuntimeError(
            "No named waypoints found "
            "in nav graph"
        )

    return places


def require_places(
    places: dict[str, Place],
    place_ids,
) -> None:
    """
    確認正式 Task 會使用的地點
    全部存在 RMF nav graph。
    """

    missing = [
        place_id
        for place_id
        in place_ids
        if place_id not in places
    ]

    if missing:

        raise ValueError(
            "Required RMF places "
            "not found: "
            f"{missing}"
        )
