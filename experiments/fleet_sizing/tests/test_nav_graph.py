from pathlib import Path
import sys

# 讓 tests 可以 import 上一層的 nav_graph.py
CURRENT_DIR = Path(__file__).resolve().parent
FLEET_SIZING_DIR = CURRENT_DIR.parent

if str(FLEET_SIZING_DIR) not in sys.path:
    sys.path.insert(0, str(FLEET_SIZING_DIR))

from nav_graph import NavGraph


def test_load_nav_graph():
    graph = NavGraph()

    # Codex 已確認正式 0.yaml 有 49 個 named waypoints
    assert len(graph.waypoints_by_name) == 49


def test_known_waypoints_exist():
    graph = NavGraph()

    assert graph.has_waypoint("pharmacy")
    assert graph.has_waypoint("lab")
    assert graph.has_waypoint("ward_a_2")
    assert graph.has_waypoint("ward_b_2")
    assert graph.has_waypoint("nurse_station")
    assert graph.has_waypoint("charging_station_2")


def test_charging_station():
    graph = NavGraph()

    chargers = graph.get_chargers()

    assert "charging_station_2" in chargers


def test_waypoint_position():
    graph = NavGraph()

    x, y = graph.get_waypoint_position("pharmacy")

    assert isinstance(x, float)
    assert isinstance(y, float)

    # Codex 讀到的 pharmacy 座標約為 (31.830, -24.441)
    assert abs(x - 31.830) < 0.01
    assert abs(y - (-24.441)) < 0.01


def test_same_source_destination_distance_is_zero():
    graph = NavGraph()

    distance = graph.shortest_path_distance(
        "pharmacy",
        "pharmacy",
    )

    assert distance == 0.0


def test_pharmacy_to_ward_a_has_path():
    graph = NavGraph()

    path = graph.shortest_path(
        "pharmacy",
        "ward_a_2",
    )

    assert len(path) >= 2
    assert path[0] == "pharmacy"
    assert path[-1] == "ward_a_2"


def test_pharmacy_to_ward_a_distance_positive():
    graph = NavGraph()

    distance = graph.shortest_path_distance(
        "pharmacy",
        "ward_a_2",
    )

    assert distance > 0


def test_bidirectional_route():
    graph = NavGraph()

    distance_ab = graph.shortest_path_distance(
        "pharmacy",
        "ward_a_2",
    )

    distance_ba = graph.shortest_path_distance(
        "ward_a_2",
        "pharmacy",
    )

    assert distance_ab > 0
    assert distance_ba > 0

    # 目前 0.yaml 所有 lanes 都有 reverse pair，
    # 因此在純距離模型下正反方向距離應相同。
    assert abs(distance_ab - distance_ba) < 1e-6


def test_unknown_waypoint_raises_error():
    graph = NavGraph()

    try:
        graph.shortest_path_distance(
            "not_a_real_waypoint",
            "pharmacy",
        )
    except KeyError:
        return

    raise AssertionError(
        "Unknown waypoint should raise KeyError"
    )