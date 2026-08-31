import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, GroupAction, 
                            TimerAction, ExecuteProcess, RegisterEventHandler)
from launch.substitutions import LaunchConfiguration
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node, PushRosNamespace

def generate_launch_description():
    # ---------------------------------------------------------
    # 1. DECLARE LAUNCH ARGUMENTS
    # This allows the operator to pass data via command line.
    # e.g., ros2 launch patrol_params_demo ... drone_name:=drone_1
    # ---------------------------------------------------------
    drone_name_arg = DeclareLaunchArgument(
        'drone_name',
        default_value='alpha_drone',
        description='The namespace to isolate this drone\'s topics'
    )

    # Wrap the argument in a LaunchConfiguration so it can be passed to nodes
    drone_name_config = LaunchConfiguration('drone_name')

    # Get the path to our YAML file dynamically
    config_dir = os.path.join(get_package_share_directory('patrol_params_demo'), 'config')
    yaml_file_path = os.path.join(config_dir, 'production_patrol.yaml')

    # ---------------------------------------------------------
    # 2. NAMESPACES AND GROUPS (Isolation for multi-drone)
    # ---------------------------------------------------------
    # By pushing a namespace, every node inside this GroupAction 
    # gets prefixed. '/flyto' becomes '/alpha_drone/flyto'.
    subsystem_group = GroupAction(
        actions=[
            PushRosNamespace(drone_name_config),

            # The Action Server Node
            Node(
                package='waypoint_control',
                executable='flyto_action_server',
                name='action_server',
                output='screen' # Shows logging on the terminal
            ),

            # ---------------------------------------------------------
            # 3. TIMERS (Because everything starts at once)
            # ---------------------------------------------------------
            # Wait 6 seconds for the action server (and MAVROS) to boot 
            # before starting the Mission Commander and loading the YAML.
            TimerAction(
                period=6.0,
                actions=[
                    Node(
                        package='patrol_params_demo',
                        executable='mission_commander',
                        name='mission_commander',
                        output='screen',
                        parameters=[yaml_file_path] # Pass the YAML file here!
                    )
                ]
            )
        ]
    )

    # ---------------------------------------------------------
    # 4. EXECUTING PROCESSES (e.g., Requesting a Stream)
    # ---------------------------------------------------------
    # Wait 10 seconds total (4 seconds after commander), then ask 
    # the flight controller for a data stream using a raw terminal command.
    stream_request = TimerAction(
        period=10.0,
        actions=[
            ExecuteProcess(
                cmd=['ros2', 'topic', 'hz', '/mavros/local_position/pose'],
                output='screen',
                name='stream_probe'
            )
        ]
    )

    # ---------------------------------------------------------
    # 5. EVENT HANDLERS (Reacting to a node exiting)
    # ---------------------------------------------------------
    # Let's create a temporary "probe" that just prints something and exits.
    probe_node = ExecuteProcess(
        cmd=['echo', 'System Diagnostics Complete!'],
        name='diagnostic_probe',
        output='screen'
    )

    # When the probe finishes and exits, this handler catches it 
    # and runs a follow-up action.
    probe_exit_handler = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=probe_node,
            on_exit=[
                ExecuteProcess(
                    cmd=['echo', 'Probe exited gracefully. Mission is GO.'],
                    output='screen'
                )
            ]
        )
    )

    # ---------------------------------------------------------
    # RETURN THE MASTER LIST
    # ---------------------------------------------------------
    return LaunchDescription([
        drone_name_arg,
        probe_exit_handler,
        probe_node,
        subsystem_group,
        stream_request
    ])