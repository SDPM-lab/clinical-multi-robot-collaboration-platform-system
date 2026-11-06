from pathlib import Path
import random
import sys

CURRENT_DIR = Path(__file__).resolve().parent
FLEET_SIZING_DIR = CURRENT_DIR.parent

if str(FLEET_SIZING_DIR) not in sys.path:
    sys.path.insert(0, str(FLEET_SIZING_DIR))

from service_time import ServiceTimeModel
from config import (
    TASK_WASTE,
    TASK_CLOTHES,
    TASK_MEDICATION,
    TASK_SPECIMEN,
    TASK_WARD,
)


def test_waste_service_time():
    rng = random.Random(42)
    model = ServiceTimeModel()

    for _ in range(1000):
        sample = model.sample(TASK_WASTE, rng)

        assert 1 <= sample.item_count <= 10
        assert sample.detect_s >= 5
        assert sample.detect_s <= 10

        # 每件最少 8+5 = 13 秒
        # 每件最多 15+10 = 25 秒
        min_total = 5 + sample.item_count * 13
        max_total = 10 + sample.item_count * 25

        assert min_total <= sample.total_s <= max_total


def test_clothes_service_time():
    rng = random.Random(42)
    model = ServiceTimeModel()

    for _ in range(1000):
        sample = model.sample(TASK_CLOTHES, rng)

        assert 1 <= sample.item_count <= 8
        assert 5 <= sample.detect_s <= 10

        # 每件最少 12+8 = 20 秒
        # 每件最多 20+15 = 35 秒
        min_total = 5 + sample.item_count * 20
        max_total = 10 + sample.item_count * 35

        assert min_total <= sample.total_s <= max_total


def test_medication_service_time():
    rng = random.Random(42)
    model = ServiceTimeModel()

    for _ in range(1000):
        sample = model.sample(TASK_MEDICATION, rng)

        assert 20 <= sample.load_s <= 40
        assert 10 <= sample.handoff_s <= 30
        assert 30 <= sample.total_s <= 70


def test_specimen_service_time():
    rng = random.Random(42)
    model = ServiceTimeModel()

    for _ in range(1000):
        sample = model.sample(TASK_SPECIMEN, rng)

        assert 25 <= sample.load_verify_s <= 45
        assert 15 <= sample.receive_s <= 30
        assert 40 <= sample.total_s <= 75


def test_ward_service_time():
    rng = random.Random(42)
    model = ServiceTimeModel()

    for _ in range(1000):
        sample = model.sample(TASK_WARD, rng)

        assert 212 <= sample.vital_sign_s <= 238
        assert 212 <= sample.total_s <= 238


def test_same_seed_is_reproducible():
    model = ServiceTimeModel()

    rng1 = random.Random(12345)
    rng2 = random.Random(12345)

    sample1 = model.sample(TASK_WASTE, rng1)
    sample2 = model.sample(TASK_WASTE, rng2)

    assert sample1 == sample2


def test_different_seed_can_change_result():
    model = ServiceTimeModel()

    rng1 = random.Random(1)
    rng2 = random.Random(2)

    sample1 = model.sample(TASK_MEDICATION, rng1)
    sample2 = model.sample(TASK_MEDICATION, rng2)

    assert sample1 != sample2


def test_invalid_task_type_raises_error():
    rng = random.Random(42)
    model = ServiceTimeModel()

    try:
        model.sample("not_a_real_task", rng)
    except ValueError:
        return

    raise AssertionError(
        "Invalid task type should raise ValueError"
    )