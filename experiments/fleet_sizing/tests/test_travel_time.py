from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
FLEET_SIZING_DIR = CURRENT_DIR.parent

if str(FLEET_SIZING_DIR) not in sys.path:
    sys.path.insert(0, str(FLEET_SIZING_DIR))

from travel_time import TravelTimeModel


def test_load_empirical_routes():
    model = TravelTimeModel()

    assert len(model.route_stats) == 31


def test_effective_speed_is_valid():
    model = TravelTimeModel()

    assert model.effective_speed_mps is not None
    assert model.effective_speed_mps > 0
    assert model.effective_speed_mps < 0.35


def test_known_empirical_route():
    model = TravelTimeModel()

    assert model.has_empirical_route(
        "pharmacy",
        "ward_a_2",
    )

    travel_time = model.get_travel_time_mean(
        "pharmacy",
        "ward_a_2",
    )

    assert abs(travel_time - 168.302) < 0.01

    assert model.get_route_source(
        "pharmacy",
        "ward_a_2",
    ) == "empirical"


def test_reverse_route_uses_fallback():
    model = TravelTimeModel()

    # 目前只有 pharmacy -> ward_a_2 實測，
    # 反方向沒有直接量測。
    assert not model.has_empirical_route(
        "ward_a_2",
        "pharmacy",
    )

    travel_time = model.get_travel_time_mean(
        "ward_a_2",
        "pharmacy",
    )

    assert travel_time > 0

    assert model.get_route_source(
        "ward_a_2",
        "pharmacy",
    ) == "nav_graph_fallback"


def test_charging_to_pharmacy_uses_fallback():
    model = TravelTimeModel()

    travel_time = model.get_travel_time_mean(
        "charging_station_2",
        "pharmacy",
    )

    assert travel_time > 0

    assert model.get_route_source(
        "charging_station_2",
        "pharmacy",
    ) == "nav_graph_fallback"


def test_same_waypoint_has_zero_time():
    model = TravelTimeModel()

    travel_time = model.get_travel_time_mean(
        "pharmacy",
        "pharmacy",
    )

    assert travel_time == 0.0


def test_empirical_stats():
    model = TravelTimeModel()

    stats = model.get_empirical_stats(
        "ward_a_2",
        "waste_return_2",
    )

    assert stats.n == 5
    assert abs(stats.mean_s - 163.22) < 0.01
    assert abs(stats.sd_s - 6.867) < 0.01
    assert abs(stats.mean_actual_distance_m - 43.297) < 0.01


def test_unknown_empirical_route_raises_keyerror():
    model = TravelTimeModel()

    try:
        model.get_empirical_stats(
            "charging_station_2",
            "pharmacy",
        )
    except KeyError:
        return

    raise AssertionError(
        "Missing empirical route should raise KeyError"
    )