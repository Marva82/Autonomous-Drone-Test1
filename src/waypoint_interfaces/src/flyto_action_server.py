import math
import time
import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State
from mavros_msgs.srv import SetMode, CommandBool, CommandTOL

# Import the custom Action we defined in the interfaces package
from waypoint_interfaces.action import FlyTo

TAKEOFF_ALT = 5.0
ARRIVE_RADIUS = 1.0

class FlyToServer(Node):
    def __init__(self):
        super().__init__('flyto_action_server')
        
        # We need a special callback group to allow multiple threads to run at once.
        # Without this, the 'execute' loop would freeze the node, and we could never receive a 'cancel' command.
        self.cb_group = ReentrantCallbackGroup()

        # 1. The Action Server setup
        self._action_server = ActionServer(
            self,
            FlyTo,
            'flyto',
            execute_callback=self.execute_callback,
            callback_group=self.cb_group,
            cancel_callback=self._on_cancel,
            goal_callback=self._on_goal
        )

        self.state = None
        self.pose = None

        # 2. Sensor Subscribers (Listening to MAVROS)
        self.state_sub = self.create_subscription(
            State, '/mavros/state', self.state_callback, qos_profile_sensor_data, callback_group=self.cb_group)
        self.pose_sub = self.create_subscription(
            PoseStamped, '/mavros/local_position/pose', self.pose_callback, qos_profile_sensor_data, callback_group=self.cb_group)

        # 3. Command Clients (Talking to MAVROS)
        self.setpoint_pub = self.create_publisher(PoseStamped, 'mavros/setpoint_position/local', 10)
        self.set_mode = self.create_client(SetMode, '/mavros/set_mode', callback_group=self.cb_group)
        self.arming = self.create_client(CommandBool, '/mavros/cmd/arming', callback_group=self.cb_group)
        self.takeoff = self.create_client(CommandTOL, '/mavros/cmd/takeoff', callback_group=self.cb_group)
        
        self.get_logger().info('FlyTo Action Server is ready.')

    # --- Sensor Callbacks ---
    def state_callback(self, msg):
        self.state = msg

    def pose_callback(self, msg):
        self.pose = msg

    # --- Action Server Contracts ---
    def _on_goal(self, goal_request):
        """Phase 1: The client asks if we can accept the mission."""
        self.get_logger().info(f'Goal received: ({goal_request.x:.1f}, {goal_request.y:.1f}, {goal_request.z:.1f})')
        return GoalResponse.ACCEPT

    def _on_cancel(self, goal_handle):
        """Interrupt: The client sends an emergency stop."""
        self.get_logger().info('Cancel request received!')
        return CancelResponse.ACCEPT

    def execute_callback(self, goal_handle):
        """Phase 2: The actual mission logic. This runs until the drone arrives or is canceled."""
        goal = goal_handle.request
        feedback = FlyTo.Feedback()
        result = FlyTo.Result()

        # Step 1: Arm and Takeoff
        self._arm_and_takeoff()

        # Step 2: Fly to waypoint loop
        while rclpy.ok():
            # Check if the client panicked and hit the stop button
            if goal_handle.is_cancel_requested:
                if self.pose is not None:
                    p = self.pose.pose.position
                    self._publish_setpoint(p.x, p.y, p.z) # Hold current position
                
                goal_handle.canceled()
                result.arrived = False
                result.final_distance = self._distance_to(goal.x, goal.y, goal.z)
                self.get_logger().info(f'CANCELED at {result.final_distance:.1f}m out, holding position.')
                return result

            # Keep sending the target to the flight controller
            self._publish_setpoint(goal.x, goal.y, goal.z)
            dist = self._distance_to(goal.x, goal.y, goal.z)

            # --- THE FEEDBACK STEP ---
            # Publish distance continuously back to the client while flying
            feedback.distance_remaining = dist
            goal_handle.publish_feedback(feedback)

            # Check if we arrived
            if dist < ARRIVE_RADIUS:
                break

            self._sleep(0.5)

        # Step 3: Mission Complete
        goal_handle.succeed()
        result.arrived = True
        result.final_distance = self._distance_to(goal.x, goal.y, goal.z)
        self.get_logger().info(f'Arrived! Final distance {result.final_distance:.2f}m')
        return result

    # --- Helper Methods ---
    def _publish_setpoint(self, x, y, z):
        sp = PoseStamped()
        sp.header.stamp = self.get_clock().now().to_msg()
        sp.pose.position.x = x
        sp.pose.position.y = y
        sp.pose.position.z = float(z)
        sp.pose.orientation.w = 1.0
        self.setpoint_pub.publish(sp)

    def _distance_to(self, x, y, z):
        if self.pose is None:
            return float('inf')
        px = self.pose.pose.position.x
        py = self.pose.pose.position.y
        pz = self.pose.pose.position.z
        return math.sqrt((x-px)**2 + (y-py)**2 + (z-pz)**2)

    def _sleep(self, duration):
        time.sleep(duration)

    def _arm_and_takeoff(self):
        self.get_logger().info('Switching to GUIDED...')
        req = SetMode.Request(custom_mode='GUIDED')
        self.set_mode.call_async(req)
        self._sleep(2.0)

        self.get_logger().info('Arming...')
        arm = CommandBool.Request(value=True)
        self.arming.call_async(arm)
        self._sleep(2.0)

        self.get_logger().info(f'Taking off to {TAKEOFF_ALT}m...')
        to = CommandTOL.Request(altitude=TAKEOFF_ALT)
        self.takeoff.call_async(to)
        self._sleep(5.0) # Wait 5 seconds for the drone to physically gain altitude

def main(args=None):
    rclpy.init(args=args)
    node = FlyToServer()
    
    # CRITICAL: We must use a MultiThreadedExecutor so the execution loop 
    # doesn't block the callback that listens for cancel requests.
    executor = MultiThreadedExecutor()
    rclpy.spin(node, executor=executor)
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()