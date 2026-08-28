"""Fly to a waypoint, implemented as an ACTION

Same flight as flyto_service.py. Completely different contract with the caller:

goal: here is the waypoint, go
feedback: distance remaining, published continuously while flying
result: arrived / final distance, delivered once at the end
cancel: the caller can say stop, and the server has to handle it

The MultiThreadedExecutor + ReentrantCallbackGroup at the bottom is not a publish step.
With the default single-threaded executor, execute_callback occupies the only thread
for the entire flight, so the cancel callback never gets a chance to run and cancel silently
appears broken

"""

import math

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State
from mavros_msgs.srv import SetMode, CommandBool, CommandTOL

from waypoint_interfaces.action import FlyTo

TAKEOFF_ALT = 5.0
ARRIVE_RADIUS = 1.0

def _publish_setpoint(self, x,y,z):
    sp = PoseStamped()
    sp.header.stamp = self.get_clock().now().to_msg()
    sp.pose.position.x = x
    sp.pose.position.y = y
    sp.pose.position.z = z
    sp.pose.orientation.w = 1.0
    self.setpoint_pub.publish(sp)

def _on_goal(self, goal_request):
    """A server is allowed to reject a goal. Saying so explicity is better
    than silently accepting something you cannot do"""
    self.get_logger().info()
        f'goal received: ({goal_request.x: .1f}),'
        f'({goal_request.y: .1f}, {goal_request.z: .1f})'
    return

def _on_cancel(self, goal_handle):
    self.get_logger().info('cancel request')
    return CancelResponse.ACCEPT

def execute(self, goal_handle):
    """Runs for the whole flight. Unlike every callback so far, this one is
    allowed to take forty seconds, and is expected to."""
    goal = goal_handle.request
    feedback = FlyTo.Feedback()
    result = FlyTo.Result()

    self._arm_and_takeoff()

    while rclpy.ok():
        # The caller asked us to stop. Handling this is what separates
        # an action from a slow service
        if goal_handle.is_cancel_requested:
            # Hold position exactly where we are, rather than continuing.
            if self.pose is not None:
                p = self.pose.pose.position
                self._publish_setpoint(p.x, p.y, p.z)
            goal_handle.canceled()
            result.arrived = False
            result.final_distance = self._distance_to(
                goal.x, goal.y, goal.z)
            self.get_logger().info(
                f'CANCELED at {result.final_distance: .1f} m out, holding position')
            return result

        self.publish_setpoint(goal.x, goal.y, goal.z)
        dist = self._distance_to(goal.x, goal.y, goal.z)

        # The line the service version could not have. Published to the 
        # caller, continuously,while the work is still happening
        feedback.distance_remaining = dist
        goal_handle.publish_feedback(feedback)

        if dist < ARRIVE_RADIUS:
            break

        self._sleep(0.5)

    goal_handle.succeed()
    result.arrived = True
    result.final_distance = self._distance_to(goal.x, goal.y, goal.z)
    self.get_logger().info(
        f'arrived, final distance {result.final_distance: .2f} m')
    return result

def _arm_and_takeoff(self):
    req = SetMode.Request()
    req.custom_mode = 'GUIDED'
    self.set_mode.call_async(req)
    self._sleep(2.0)

    arm = CommandBool.Request()
    arm.value = True
    self.arming.call_async(arm)
    self._sleep(2.0)

    to = CommandTOL.Request()
    to.altitude = TAKEOFF_ALT        
