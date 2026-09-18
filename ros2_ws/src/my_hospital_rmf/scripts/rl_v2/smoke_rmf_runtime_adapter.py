#!/usr/bin/env python3

import time

import rclpy

from rclpy.node import Node

from rmf_fleet_msgs.msg import (
    FleetState,
)

from rl_v2.rmf_runtime_adapter import (
    RMFFleetStateAggregator,
)


class RMFRuntimeSmokeNode(
    Node
):

    def __init__(
        self,
    ):

        super().__init__(
            "rmf_runtime_adapter_smoke"
        )

        self.aggregator = (
            RMFFleetStateAggregator()
        )

        self.create_subscription(
            FleetState,
            "/fleet_states",
            self._fleet_state_callback,
            20,
        )


    def _fleet_state_callback(
        self,
        message: FleetState,
    ) -> None:

        self.aggregator.ingest(
            message
        )


def main():

    rclpy.init()

    node = (
        RMFRuntimeSmokeNode()
    )

    print(
        "=" * 100
    )

    print(
        "RMF RUNTIME ADAPTER SMOKE TEST"
    )

    print(
        "=" * 100
    )

    print(
        "Waiting for /fleet_states ..."
    )

    start = time.monotonic()

    timeout_seconds = 10.0

    while (
        rclpy.ok()
        and
        (
            time.monotonic()
            -
            start
        )
        <
        timeout_seconds
    ):

        rclpy.spin_once(
            node,
            timeout_sec=0.1,
        )

        if (
            node
            .aggregator
            .ready()
        ):

            break

    aggregator = (
        node.aggregator
    )

    print()

    if not aggregator.ready():

        print(
            "RESULT: FAIL"
        )

        print(
            "Missing Robots:",
            aggregator
            .missing_robot_ids(),
        )

        node.destroy_node()

        rclpy.shutdown()

        raise SystemExit(
            1
        )

    print(
        "All expected Robots received."
    )

    print()

    print(
        f"{'Robot':<20}"
        f"{'Fleet Source':<24}"
        f"{'Status':<12}"
        f"{'Available':<12}"
        f"{'Battery':<10}"
        f"{'X':>10}"
        f"{'Y':>10}"
        f"{'Map':>8}"
    )

    print(
        "-" * 110
    )

    for robot_id in sorted(
        aggregator.latest_states
    ):

        state = (
            aggregator
            .latest_states[
                robot_id
            ]
        )

        source = (
            aggregator
            .latest_source_fleet[
                robot_id
            ]
        )

        print(
            f"{robot_id:<20}"
            f"{source:<24}"
            f"{state.status:<12}"
            f"{str(state.available):<12}"
            f"{state.battery:<10.3f}"
            f"{state.x:>10.3f}"
            f"{state.y:>10.3f}"
            f"{state.map_name:>8}"
        )

    print()

    print(
        "Capabilities:"
    )

    for robot_id in sorted(
        aggregator.latest_states
    ):

        state = (
            aggregator
            .latest_states[
                robot_id
            ]
        )

        print(
            f"  {robot_id}: "
            f"{sorted(state.capabilities)}"
        )

    # ======================================================
    # Build RuntimeStateManager
    # ======================================================

    manager = (
        aggregator
        .create_runtime_manager(
            robot_speed_mps=1.0
        )
    )

    print()

    manager.print_state()

    assert (
        len(
            manager.get_runtimes()
        )
        ==
        3
    )

    print()

    print(
        "=" * 100
    )

    print(
        "RMF -> RobotState "
        "-> RuntimeStateManager: PASS"
    )

    print(
        "=" * 100
    )

    node.destroy_node()

    rclpy.shutdown()


if __name__ == "__main__":

    main()
