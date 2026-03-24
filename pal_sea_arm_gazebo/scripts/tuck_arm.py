#!/usr/bin/env python3
# Copyright (c) 2026 PAL Robotics S.L. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from play_motion2_msgs.action import PlayMotion2
from play_motion2_msgs.srv import IsMotionReady


class PlayMotionActionClient(Node):
    def __init__(self):
        super().__init__("arm_starter")
        self._play_motion_client = ActionClient(
            self, PlayMotion2, "play_motion2")
        self._is_ready_client = self.create_client(
            IsMotionReady, "/play_motion2/is_motion_ready"
        )
        self._is_successful = None

    def wait_for_server(self, motion_name):
        self.get_logger().info("Waiting for play_motion2 server...")
        self._play_motion_client.wait_for_server()

        while not self._is_ready_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error("is_ready service not ready, waiting...")

        request = IsMotionReady.Request()
        request.motion_key = motion_name

        is_ready = False
        while rclpy.ok() and not is_ready:
            self.get_logger().info(
                f"Checking if motion '{motion_name}' is ready...")
            future = self._is_ready_client.call_async(request)
            rclpy.spin_until_future_complete(self, future)

            response = future.result()
            if response and response.is_ready:
                is_ready = True
                self.get_logger().info(
                    f"Motion '{motion_name}' is ready to go!")
            else:
                self.get_logger().warn(
                    f"Motion '{motion_name}' not ready yet. Retrying in 2s...")
                time.sleep(2.0)

    def send_goal(self, motion_name, skip_planning):
        self._is_successful = None
        goal_msg = PlayMotion2.Goal()
        goal_msg.motion_name = motion_name
        goal_msg.skip_planning = skip_planning

        self.get_logger().info(f"Sending goal for motion: {motion_name}")
        send_goal_future = self._play_motion_client.send_goal_async(goal_msg)

        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()

        if not goal_handle.accepted:
            self.get_logger().error("Goal rejected by server")
            self._is_successful = False
            return

        self.get_logger().info("Goal accepted, waiting for result...")
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result = result_future.result().result
        if result.error == "":
            self._is_successful = True
            self.get_logger().info("Motion succeeded!")
        else:
            self._is_successful = False
            self.get_logger().error(
                f"Motion failed with error: {result.error}")


def main(args=None):
    rclpy.init(args=args)
    action_client = PlayMotionActionClient()

    MOTION = "start_arm"

    action_client.wait_for_server(MOTION)

    action_client.get_logger().info(f"Starting execution of {MOTION}...")
    action_client.send_goal(MOTION, True)

    if action_client._is_successful:
        action_client.get_logger().info("Robot is in START position.")
    else:
        action_client.get_logger().error("Failed to move robot to START position.")

    time.sleep(2.0)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
