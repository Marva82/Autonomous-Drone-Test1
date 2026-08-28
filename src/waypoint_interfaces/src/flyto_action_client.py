import sys
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from waypoint_interfaces.action import FlyTo

class FlyToClient(Node):
    def __init__(self, x, y, z, cancel_after=None):
        super().__init__('flyto_action_client')
        self._client = ActionClient(self, FlyTo, 'flyto')
        self._x = float(x)
        self._y = float(y)
        self._z = float(z)
        self._cancel_after = cancel_after
        self._goal_handle = None
        self._cancel_timer = None

    def send_goal(self):
        self.get_logger().info('Waiting for action server...')
        self._client.wait_for_server()

        # Create the exact Goal package defined in FlyTo.action
        goal_msg = FlyTo.Goal()
        goal_msg.x = self._x
        goal_msg.y = self._y
        goal_msg.z = self._z

        self.get_logger().info(f'Sending Goal: X={self._x} Y={self._y} Z={self._z}')
        
        # Send it! Note that we attach our feedback function here.
        self._send_goal_future = self._client.send_goal_async(
            goal_msg, 
            feedback_callback=self.feedback_callback
        )
        
        # When the server replies with ACCEPT or REJECT, run this function:
        self._send_goal_future.add_done_callback(self.goal_response_callback)

        # If the user launched this script with --cancel, start the countdown
        if self._cancel_after is not None:
            self.get_logger().info(f'Will automatically cancel in {self._cancel_after} seconds.')
            self._cancel_timer = self.create_timer(float(self._cancel_after), self.cancel_goal)

    def goal_response_callback(self, future):
        """Runs once when the Server decides to accept or reject the goal."""
        self._goal_handle = future.result()
        if not self._goal_handle.accepted:
            self.get_logger().info('Mission rejected by Server.')
            return

        self.get_logger().info('Mission accepted by Server! Flying...')
        
        # Now that we are flying, wait for the final RESULT.
        self._get_result_future = self._goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        """Runs constantly as the Server streams distance data back."""
        feedback = feedback_msg.feedback
        self.get_logger().info(f'Live Feedback: {feedback.distance_remaining:.1f} meters to go')

    def cancel_goal(self):
        """Triggers if the cancel timer expires."""
        self.get_logger().info('ABORTING MISSION! Sending cancel request...')
        if self._goal_handle is not None:
            self._goal_handle.cancel_goal_async()
        if self._cancel_timer:
            self._cancel_timer.cancel()

    def get_result_callback(self, future):
        """Runs once when the Server completes the flight or honors a cancel."""
        result = future.result().result
        self.get_logger().info(f'Final Result: Arrived={result.arrived}, Error Margin={result.final_distance:.2f}m')
        
        # The script's job is done, shut it down.
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    
    # Simple argument parsing so we can launch it with coordinates from the terminal
    if len(sys.argv) < 4:
        print("Usage: ros2 run waypoint_control flyto_action_client X Y Z [--cancel SECONDS]")
        return
        
    x, y, z = sys.argv[1], sys.argv[2], sys.argv[3]
    cancel_after = None
    
    if len(sys.argv) == 6 and sys.argv[4] == '--cancel':
        cancel_after = sys.argv[5]

    client = FlyToClient(x, y, z, cancel_after)
    client.send_goal()
    
    # Keep the node alive to receive feedback and results
    rclpy.spin(client)

if __name__ == '__main__':
    main()