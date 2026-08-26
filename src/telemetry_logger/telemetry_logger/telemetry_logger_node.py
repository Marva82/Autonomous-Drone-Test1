# --- IMPORTS ---
# rclpy is the ROS 2 Python library. It lets Python talk to the ROS 2 network.
import rclpy
from rclpy.node import Node  
from rclpy.qos import QoSProfile, ReliabilityPolicy

# We have to import the exact "message types" that MAVROS is sending.
# Think of these as the specific shapes of the envelopes the data comes in.
from sensor_msgs.msg import NavSatFix, Imu, BatteryState

# --- NODE DEFINITION ---
# By passing (Node) into our class, we inherit all of ROS 2's built-in node powers.
class TelemetryLogger(Node):
    def __init__(self):
        # This names our node 'telemetry_logger' on the ROS 2 network so other nodes can see it.
        super().__init__('telemetry_logger')

        # --- THE MAILBOXES ---
        # We start with empty variables. They will eventually hold the latest message.
        self.last_fix = None
        self.last_imu = None
        self.last_battery = None

        # --- QUALITY OF SERVICE (QoS) ---
        # Sensor data over a network can be spotty. MAVROS sends data as "BEST_EFFORT" 
        # (it doesn't guarantee delivery, it just fires it off as fast as possible). 
        # We MUST match that policy here, otherwise ROS 2 will refuse to connect them.
        best_effort_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)

        # --- THE SUBSCRIBERS ---
        # We tell ROS 2: "Listen to this topic. When data arrives, run this callback function."
        
        # 1. GPS Subscriber
        self.create_subscription(
            NavSatFix,                          # The message type (envelope shape)
            '/mavros/global_position/raw/fix',  # The exact topic name to listen to
            self.fix_callback,                  # The function to run when data arrives
            best_effort_qos)                    # The QoS rules

        # 2. IMU Subscriber (Orientation/Acceleration)
        self.create_subscription(
            Imu,
            '/mavros/imu/data',
            self.imu_callback,
            best_effort_qos)

        # 3. Battery Subscriber
        self.create_subscription(
            BatteryState,
            '/mavros/battery',
            self.battery_callback,
            best_effort_qos
        )

        # --- THE TIMER (The Mail Carrier) ---
        # Instead of printing data the exact millisecond it arrives, we create a timer
        # that runs the 'self.report' function exactly once every 1.0 seconds.
        self.create_timer(1.0, self.report)

        # Print a startup message so we know the program didn't crash immediately.
        self.get_logger().info('telemetry_logger up, waiting on GPS, IMU, and Battery Level')

    # --- CALLBACK FUNCTIONS ---
    # These functions run invisibly in the background. Their ONLY job is to take the 
    # incoming message ('msg') and save it into our class variables ('self.last_fix', etc.)
    def fix_callback(self, msg):
        self.last_fix = msg

    def imu_callback(self, msg):
        self.last_imu = msg

    def battery_callback(self, msg):
        self.last_battery = msg

    # --- THE REPORTER ---
    # This is triggered by our timer every 1.0 seconds.
    def report(self):
        # SAFETY CHECK: If even one of our mailboxes is still 'None' (empty), 
        # we abort and try again next second. We can't print data that doesn't exist yet!
        if not (self.last_fix and self.last_imu and self.last_battery):
            self.get_logger().info('still waiting on all three topics...')
            return

        # EXTRACTING THE DATA:
        # We dive into the message structures to pull out the specific numbers we want.
        lat = self.last_fix.latitude
        lon = self.last_fix.longitude
        alt = self.last_fix.altitude
        gz = self.last_imu.linear_acceleration.z # Gravity / vertical acceleration
        volts = self.last_battery.voltage
        pct = self.last_battery.percentage * 100.0

        # PRINTING:
        # The 'f' before the string allows us to inject our Python variables directly into the text.
        # The ':.6f' formats the number to show exactly 6 decimal places (crucial for GPS precision).
        self.get_logger().info(f'lat={lat:.6f} lon={lon:.6f} alt={alt:.1f}m volts={volts:.1f} gz={gz:.2f}')


# --- BOILERPLATE EXECUTION ---
# This block is required at the bottom of EVERY ROS 2 Python script.
def main(args=None):
    # 1. Boot up the ROS 2 communications system
    rclpy.init(args=args)
    
    # 2. Create an instance of the class we just wrote above
    telemetry_logger = TelemetryLogger()
    
    # 3. Spin! This is an infinite loop that keeps the program alive. 
    # Without this, the script would run once and instantly close.
    rclpy.spin(telemetry_logger)
    
    # 4. If the user presses Ctrl+C, the spin loop breaks, and we clean up nicely.
    telemetry_logger.destroy_node()
    rclpy.shutdown()

# This is standard Python: it tells the computer to run the 'main()' function 
# if this file is executed directly from the terminal.
if __name__ == '__main__':
    main()