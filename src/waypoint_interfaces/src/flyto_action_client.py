"""Action client for FlyTo.

Three callbacks, one flight, none of them blocking:

    send_goal_async --> future --> goal handle (did the server accept?)
    get_result_async --> future --> result (how did it end?)
    feedback_callback (how is it going, right now?)
    
Run with --cancel after N to send a cancel N seconds into the flight """

import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from waypoint_interfaces.action import FlyTo

class FlyToClient(Node):

    def __init__(self, x, y, z, cancel_after=None):
        super().__init__('flyto_action_client')
        self._client = ActionClient(self, FlyTo, 'flyto')
        self._x, self._y, self._z = x, y, z
        self._cancel_after = cancel_after
        self._goal_handle = None
        self._cancel_timer = None

    def send_goal(self):
        self.get_logger().info('waiting for action server...')
        self._client.wait_for_server()

        