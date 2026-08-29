import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.msg import ParameterDescriptor, FloatingPointRange, IntegerRange, SetParametersResult

class PatrolConfigNode(Node):
    def __init__(self):
        super().__init__('patrol_config')

        # 1. Define the constraints (Descriptors)
        # These act as hard interlocks. The node will automatically reject values outside these ranges.
        alt_descriptor = ParameterDescriptor(
            description='Altitude above launch for the patrol sweep, in meters',
            floating_point_range=[FloatingPointRange(from_value=5.0, to_value=200.0, step=0.0)]
        )
        
        speed_descriptor = ParameterDescriptor(
            description='Cruise speed in meters per second',
            floating_point_range=[FloatingPointRange(from_value=1.0, to_value=15.0, step=0.0)]
        )

        leg_count_descriptor = ParameterDescriptor(
            description='Number of legs in the patrol pattern',
            integer_range=[IntegerRange(from_value=1, to_value=50, step=0)]
        )

        # 2. Declare the Parameters (with default fallback values and their descriptors)
        self.declare_parameter('sweep_altitude_m', 30.0, alt_descriptor)
        self.declare_parameter('cruise_speed_mps', 5.0, speed_descriptor)
        self.declare_parameter('leg_count', 4, leg_count_descriptor)
        self.declare_parameter('leg_length_m', 100.0) # No strict range limit applied here
        self.declare_parameter('return_home', True)
        self.declare_parameter('site_name', 'Default Test Site')

        # 3. Register the Callback Interlock
        # Every time an operator tries to change a parameter via terminal, it passes through this function first.
        self.add_on_set_parameters_callback(self.validate_parameters)

        # 4. Print the initial configuration on startup
        self.print_mission_briefing()

    def print_mission_briefing(self):
        """Calculates derived values and prints the active configuration."""
        alt = self.get_parameter('sweep_altitude_m').value
        speed = self.get_parameter('cruise_speed_mps').value
        legs = self.get_parameter('leg_count').value
        length = self.get_parameter('leg_length_m').value
        site = self.get_parameter('site_name').value

        total_distance = legs * length
        estimated_time_sec = total_distance / speed

        self.get_logger().info('--- PATROL CONFIGURATION LOADED ---')
        self.get_logger().info(f'Site Name: {site}')
        self.get_logger().info(f'Altitude:  {alt} m')
        self.get_logger().info(f'Route:     {legs} legs at {length}m each (Total: {total_distance}m)')
        self.get_logger().info(f'Est. Time: {estimated_time_sec / 60.0:.2f} minutes')
        self.get_logger().info('-----------------------------------')

    def validate_parameters(self, params):
        """
        The Endurance Budget Interlock. 
        Evaluates proposed parameter changes BEFORE they are applied.
        """
        # Start by assuming we are keeping the current values
        proposed_speed = self.get_parameter('cruise_speed_mps').value
        proposed_legs = self.get_parameter('leg_count').value
        proposed_length = self.get_parameter('leg_length_m').value

        # Overwrite with any new values the operator is trying to set
        for param in params:
            if param.name == 'cruise_speed_mps':
                proposed_speed = param.value
            elif param.name == 'leg_count':
                proposed_legs = param.value
            elif param.name == 'leg_length_m':
                proposed_length = param.value

        # Calculate relationship constraint
        total_distance = proposed_legs * proposed_length
        est_time_seconds = total_distance / proposed_speed

        MAX_ENDURANCE_SEC = 1800.0 # 30 minutes

        if est_time_seconds > MAX_ENDURANCE_SEC:
            error_msg = f'MISSION DENIED: Endurance budget exceeded. Est time: {est_time_seconds/60:.1f} mins > 30 min limit.'
            self.get_logger().warn(error_msg)
            return SetParametersResult(successful=False, reason=error_msg)

        self.get_logger().info('Parameters updated and accepted by Endurance Interlock.')
        return SetParametersResult(successful=True)

def main(args=None):
    rclpy.init(args=args)
    node = PatrolConfigNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()