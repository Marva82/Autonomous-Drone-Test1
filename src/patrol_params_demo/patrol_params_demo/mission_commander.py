import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
import math

from waypoint_interfaces.action import FlyTo

class MissionCommander(Node):
    def __init__(self):
        super().__init__('mission_commander')

        # 1. Declare Parameters (Falling back to defaults if no YAML is provided)
        self.declare_parameter('sweep_altitude_m', 30.0)
        self.declare_parameter('leg_count', 4)
        self.declare_parameter('leg_length_m', 100.0)
        self.declare_parameter('return_home', True)

        # 2. Setup the Action Client
        self.action_client = ActionClient(self, FlyTo, 'flyto')
        
        self.waypoints = []
        self.current_wp_index = 0

        # Boot sequence
        self.get_logger().info('Mission Commander Online. Waiting for Action Server...')
        self.action_client.wait_for_server()
        
        self.generate_flight_plan()
        self.send_next_waypoint()

    def generate_flight_plan(self):
        """Calculates a geometric polygon based on leg count and length."""
        alt = self.get_parameter('sweep_altitude_m').value
        legs = self.get_parameter('leg_count').value
        length = self.get_parameter('leg_length_m').value
        return_home = self.get_parameter('return_home').value

        self.get_logger().info(f'Generating {legs}-sided patrol pattern...')

        # Math to generate the patrol polygon
        for i in range(legs):
            angle = (2 * math.pi / legs) * i
            x = length * math.cos(angle)
            y = length * math.sin(angle)
            self.waypoints.append((x, y, alt))

        # Add origin as the final waypoint if return_home is true
        if return_home:
            self.waypoints.append((0.0, 0.0, alt))
            self.get_logger().info('Return to Launch added to flight plan.')

    def send_next_waypoint(self):
        """Dispatches the next coordinate in the list."""
        if self.current_wp_index >= len(self.waypoints):
            self.get_logger().info('MISSION COMPLETE. All waypoints reached.')
            return

        target_x, target_y, target_z = self.waypoints[self.current_wp_index]
        
        goal_msg = FlyTo.Goal()
        goal_msg.x = target_x
        goal_msg.y = target_y
        goal_msg.z = target_z

        self.get_logger().info(f'Sending Drone to Waypoint {self.current_wp_index + 1}: X:{target_x:.1f}, Y:{target_y:.1f}')

        # Send the goal and attach a callback to listen for the server's response
        send_goal_future = self.action_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self.goal_accepted_callback)

    def goal_accepted_callback(self, future):
        """Checks if the Action Server accepted the coordinate."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Waypoint rejected by Action Server! Aborting.')
            return

        # If accepted, wait for the drone to physically arrive
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.waypoint_reached_callback)

    def waypoint_reached_callback(self, future):
        """Triggers when the drone physically reaches the waypoint."""
        result = future.result().result
        if result.arrived:
            self.get_logger().info(f'Waypoint {self.current_wp_index + 1} secured.')
            # Advance the state machine and trigger the next flight
            self.current_wp_index += 1
            self.send_next_waypoint()
        else:
            self.get_logger().warn('Drone failed to reach waypoint.')


def main(args=None):
    rclpy.init(args=args)
    node = MissionCommander()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()