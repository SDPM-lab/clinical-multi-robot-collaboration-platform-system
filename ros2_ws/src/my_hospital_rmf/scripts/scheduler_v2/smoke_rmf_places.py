#!/usr/bin/env python3

from scheduler_v2.rmf_places import (
    load_places_from_nav_graph,
    require_places,
)


NAV_GRAPH = (
    "../nav_graphs/0.yaml"
)


def main():

    places = (
        load_places_from_nav_graph(
            NAV_GRAPH
        )
    )

    required = (
        "pharmacy",
        "lab",
        "nurse_station",
        "ward_a",
        "ward_b",
        "ward_c",
        "ward_d",
        "storage",
        "charging_station",
    )

    require_places(
        places,
        required,
    )

    print(
        "=" * 80
    )

    print(
        "RMF PLACE MAPPING"
    )

    print(
        "=" * 80
    )

    for place_id in required:

        place = places[
            place_id
        ]

        print(
            f"{place_id:<20}"
            f"x={place.x:>9.3f} "
            f"y={place.y:>9.3f} "
            f"map={place.map_name}"
        )

    print()

    print(
        "Named waypoints loaded:",
        len(places),
    )

    print()

    print(
        "=" * 80
    )

    print(
        "RMF NAV GRAPH "
        "-> SCHEDULER PLACES: PASS"
    )

    print(
        "=" * 80
    )


if __name__ == "__main__":

    main()
