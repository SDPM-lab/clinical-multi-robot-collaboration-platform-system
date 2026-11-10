#!/usr/bin/env python3

import json
import os
import sys
import yaml

from ament_index_python.packages import get_package_share_directory


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_robot_registry():
    package_share = get_package_share_directory("my_hospital_rmf")
    config_dir = os.path.join(package_share, "config")

    robot_profiles_path = os.path.join(
        config_dir,
        "robot_profiles.yaml",
    )

    fleet_instances_path = os.path.join(
        config_dir,
        "fleet_instances.yaml",
    )

    robot_profiles = load_yaml(robot_profiles_path)
    fleet_instances = load_yaml(fleet_instances_path)

    robot_types = robot_profiles.get("robot_types", {})
    robot_instances = fleet_instances.get("robots", {})

    registry = []

    for robot_id, instance in robot_instances.items():

        robot_type = instance.get("type")

        if not robot_type:
            raise ValueError(
                f"{robot_id}: missing 'type'"
            )

        if robot_type not in robot_types:
            raise ValueError(
                f"{robot_id}: unknown robot type '{robot_type}'. "
                f"Available types: {list(robot_types.keys())}"
            )

        type_profile = robot_types[robot_type]

        profile_model = type_profile.get("model")
        instance_model = instance.get("model")

        # instance 沒指定 model 時，自動使用 robot profile 的 model
        model = instance_model or profile_model

        # 如果兩邊都有指定但不一致，視為設定錯誤
        if (
            instance_model is not None
            and profile_model is not None
            and instance_model != profile_model
        ):
            raise ValueError(
                f"{robot_id}: model mismatch. "
                f"instance='{instance_model}', "
                f"profile='{profile_model}'"
            )

        capabilities = type_profile.get(
            "capabilities",
            [],
        )

        enabled = instance.get(
            "enabled",
            True,
        )

        spawn = instance.get(
            "spawn",
            {},
        )

        registry.append({
            "robot_id": robot_id,
            "robot_type": robot_type,
            "model": model,
            "capabilities": capabilities,
            "enabled": enabled,
            "spawn": spawn,
        })

    return registry


def main():
    try:
        registry = build_robot_registry()

        output = {
            "robot_count": len(registry),
            "robots": registry,
        }

        print(
            json.dumps(
                output,
                indent=2,
                ensure_ascii=False,
            )
        )

    except Exception as e:
        print(
            json.dumps(
                {
                    "valid": False,
                    "error": str(e),
                },
                indent=2,
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
