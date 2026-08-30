import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
import time

from mavros_msgs.srv import SetMode, CommandBool, CommandTOL
from geometry_msgs.msg import PoseStamped

class MavrosTakeoffNode(Node):
    def __init__(self):
        super().__init__('mavros_takeoff_node')
        
        self.get_logger().info("--- MAVROS Takeoff Script ---")

        # 1. Setup Service Clients
        self.mode_client = self.create_client(SetMode, '/mavros/set_mode')
        self.arm_client = self.create_client(CommandBool, '/mavros/cmd/arming')
        self.takeoff_client = self.create_client(CommandTOL, '/mavros/cmd/takeoff')

        # 2. Setup Subscriber with Sensor Data QoS
        self.pose_sub = self.create_subscription(
            PoseStamped, '/mavros/local_position/pose', self.pose_callback, qos_profile_sensor_data)

        self.target_altitude = 5.0
        self.reached_target = False

        # 3. Delay execution until rclpy.spin() has started the event loop
        self.timer = self.create_timer(1.0, self.run_mission_once)
        self.mission_started = False

    def run_mission_once(self):
        if self.mission_started:
            return
        self.mission_started = True
        self.timer.cancel() # Execute only once

        # Wait for MAVROS services to be ready on the network
        self.get_logger().info("Waiting for MAVROS services...")
        self.mode_client.wait_for_service()
        self.arm_client.wait_for_service()
        self.takeoff_client.wait_for_service()

        # Step 1: Switch to GUIDED mode
        self.get_logger().info("Switching to GUIDED mode...")
        mode_req = SetMode.Request()
        mode_req.custom_mode = 'GUIDED'
        self.mode_client.call_async(mode_req)

        # Step 2: Arm the motors
        time.sleep(1.0)
        self.get_logger().info("Arming motors...")
        arm_req = CommandBool.Request()
        arm_req.value = True
        self.arm_client.call_async(arm_req)

        # Step 3: Command Takeoff
        time.sleep(2.0)
        self.get_logger().info("Initiating Takeoff to 5.0m...")
        takeoff_req = CommandTOL.Request()
        takeoff_req.altitude = self.target_altitude
        self.takeoff_client.call_async(takeoff_req)

    def pose_callback(self, msg):
        current_alt = msg.pose.position.z
        self.get_logger().info(f"Current Altitude: {current_alt:.2f} m")

        if current_alt >= 4.8 and not self.reached_target:
            self.get_logger().info("Target altitude reached! Mission Complete.")
            self.reached_target = True
            raise SystemExit

def main(args=None):
    rclpy.init(args=args)
    node = MavrosTakeoffNode()
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()