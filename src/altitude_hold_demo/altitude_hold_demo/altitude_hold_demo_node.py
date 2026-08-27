import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

# The exact message structures MAVROS needs
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool, CommandTOL, SetMode, StreamRate

class AltitudeHoldDemo(Node):
    def __init__(self):
        # 1. Initialize the ROS 2 node
        super().__init__('altitude_hold_demo')

        # 2. Setup Variables (These were missing in the original snippet)
        self.state = None
        self.local_z = 0.0
        self.target_alt = 5.0  # We start at 5 meters
        self.takeoff_confirmed_ticks = 0
        self.phase = 'SETUP'   # Helps us track what the drone is currently doing

        # 3. Declare a ROS 2 Parameter
        # This is brilliant from your instructor: it allows us to change the altitude 
        # dynamically from the terminal while the drone is flying!
        self.declare_parameter('target_alt', 5.0)

        # 4. Subscribers (We need BEST_EFFORT to read the drone's sensors)
        best_effort_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        
        self.create_subscription(State, '/mavros/state', self.state_callback, best_effort_qos)
        self.create_subscription(PoseStamped, '/mavros/local_position/pose', self.pose_callback, best_effort_qos)

        # 5. Publishers & Clients (From the instructor's snippet)
        self.setpoint_pub = self.create_publisher(PoseStamped, 'mavros/setpoint_position/local', 10)
        self.set_mode_client = self.create_client(SetMode, '/mavros/set_mode')
        self.arming_client = self.create_client(CommandBool, '/mavros/cmd/arming')
        self.takeoff_client = self.create_client(CommandTOL, '/mavros/cmd/takeoff')
        self.stream_rate_client = self.create_client(StreamRate, '/mavros/set_stream_rate')
        
        self.stream_rate_requested = False

        # 6. Timers
        # The publisher runs very fast (20 times a second / 0.05s) to keep the drone stable.
        # The step function runs slowly (once a second) to handle commands.
        self.create_timer(0.05, self.publish_setpoint)
        self.create_timer(1.0, self.step)
        self.add_on_set_parameters_callback(self.on_param_change)

        self.get_logger().info('altitude_hold_demo up, waiting for FCU connection')

    # --- CALLBACKS ---
    def on_param_change(self, params):
        from rcl_interfaces.msg import SetParametersResult
        for p in params:
            if p.name == 'target_alt':
                self.target_alt = p.value
                self.get_logger().info(f'Target altitude successfully changed to: {self.target_alt}m')
        return SetParametersResult(successful=True)

    def state_callback(self, msg):
        self.state = msg

    def pose_callback(self, msg):
        self.local_z = msg.pose.position.z

    def publish_setpoint(self):
        # Wait 3 seconds (60 ticks at 20Hz) before taking control, so takeoff can finish.
        if self.takeoff_confirmed_ticks < 60:
            return

        # Tell the drone exactly where it should be in 3D space
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.pose.position.x = 0.0
        msg.pose.position.y = 0.0
        msg.pose.position.z = float(self.target_alt)
        msg.pose.orientation.w = 1.0
        self.setpoint_pub.publish(msg)

    # --- MAIN LOGIC LOOP (Runs 1x per second) ---
    def step(self):
        # Check connection
        if self.state is None or not self.state.connected:
            self.get_logger().info('waiting on FCU connection...')
            return

        # STATE MACHINE: This sequence safely gets the drone into the air
        if self.phase == 'SETUP':
            if self.state.mode != 'GUIDED':
                self.get_logger().info('Switching to GUIDED mode...')
                req = SetMode.Request(custom_mode='GUIDED')
                self.set_mode_client.call_async(req)
            
            elif not self.state.armed:
                self.get_logger().info('Arming motors...')
                req = CommandBool.Request(value=True)
                self.arming_client.call_async(req)
            
            else:
                self.get_logger().info(f'Taking off to {self.target_alt}m...')
                req = CommandTOL.Request(altitude=self.target_alt)
                self.takeoff_client.call_async(req)
                self.phase = 'TAKING_OFF'

        elif self.phase == 'TAKING_OFF':
            # Increase ticks to eventually unlock the setpoint publisher
            self.takeoff_confirmed_ticks += 20 
            
            if self.local_z > (self.target_alt - 0.5):
                self.get_logger().info('Target reached. Holding position.')
                self.phase = 'HOLDING'

        elif self.phase == 'HOLDING':
            self.get_logger().info(f'Holding at {self.target_alt}m (Current alt: {self.local_z:.1f}m)')

# --- BOILERPLATE EXECUTION ---
def main(args=None):
    rclpy.init(args=args)
    node = AltitudeHoldDemo()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()