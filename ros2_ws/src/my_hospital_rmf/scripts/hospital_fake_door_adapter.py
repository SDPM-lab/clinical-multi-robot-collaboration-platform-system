#!/usr/bin/env python3

import rclpy

from rclpy.node import Node

from rmf_door_msgs.msg import (
    DoorRequest,
    DoorState,
)


class HospitalFakeDoorAdapter(Node):

    def __init__(self):

        super().__init__(
            "hospital_fake_door_adapter"
        )

        self.state_pub = (
            self.create_publisher(
                DoorState,
                "/door_states",
                10,
            )
        )

        self.create_subscription(
            DoorRequest,
            "/door_requests",
            self.door_request_cb,
            10,
        )

        # door_name -> current mode
        self.door_modes: dict[
            str,
            int,
        ] = {}

        # RMF door controllers are expected to
        # publish DoorState periodically.
        self.state_timer = (
            self.create_timer(
                1.0,
                self.publish_all_states,
            )
        )

        self.get_logger().info(
            "Hospital Fake Door Adapter started"
        )

        self.get_logger().info(
            "Subscribed: /door_requests"
        )

        self.get_logger().info(
            "Publishing: /door_states"
        )

        self.get_logger().info(
            "Door state heartbeat: 1.0 Hz"
        )


    def publish_state(
        self,
        *,
        door_name: str,
        mode: int,
        log: bool = False,
    ):

        state = DoorState()

        state.door_time = (
            self.get_clock()
            .now()
            .to_msg()
        )

        state.door_name = (
            door_name
        )

        state.current_mode.value = (
            mode
        )

        self.state_pub.publish(
            state
        )

        if log:

            self.get_logger().info(
                "Door state published: "
                f"door={door_name}, "
                f"mode={mode}"
            )


    def door_request_cb(
        self,
        msg: DoorRequest,
    ):

        door_name = (
            msg.door_name
        )

        requested_mode = (
            msg.requested_mode.value
        )

        self.get_logger().info(
            "Door request: "
            f"door={door_name}, "
            f"mode={requested_mode}"
        )

        self.door_modes[
            door_name
        ] = requested_mode

        # Request 到達時立即回報一次。
        self.publish_state(
            door_name=door_name,
            mode=requested_mode,
            log=True,
        )


    def publish_all_states(
        self,
    ):

        # 定期 heartbeat。
        #
        # 不額外印 INFO，
        # 避免每秒污染 terminal log。
        for (
            door_name,
            mode,
        ) in self.door_modes.items():

            self.publish_state(
                door_name=door_name,
                mode=mode,
                log=False,
            )


def main(
    args=None,
):

    rclpy.init(
        args=args
    )

    node = (
        HospitalFakeDoorAdapter()
    )

    try:

        rclpy.spin(
            node
        )

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":

    main()
