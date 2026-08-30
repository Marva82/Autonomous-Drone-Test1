import time
from pymavlink import mavutil

def main():
    print("--- PyMAVLink Takeoff Script ---")
    
    # 1. Connect directly to the ArduPilot UDP stream
    print("Connecting to flight controller...")
    master = mavutil.mavlink_connection('udp:127.0.0.1:14550')
    master.wait_heartbeat()
    print("Heartbeat received!")

    # 2. Request Telemetry Data (Message 33: GLOBAL_POSITION_INT)
    # We must explicitly ask the flight controller to stream position data at 10Hz
    master.mav.request_data_stream_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_POSITION, 10, 1)

    # 3. Switch to GUIDED mode (Mode 4 in ArduCopter)
    print("Switching to GUIDED mode...")
    master.mav.set_mode_send(
        master.target_system, 
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 
        4) # 4 is GUIDED
    time.sleep(1)

    # 4. Arm the motors (Component Arm/Disarm command)
    print("Arming motors...")
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
        1, 0, 0, 0, 0, 0, 0) # The '1' means ARM
    
    time.sleep(2) # Wait for spool up

    # 5. Command Takeoff to 5 meters
    print("Initiating Takeoff to 5.0m...")
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0,
        0, 0, 0, 0, 0, 0, 5.0) # The 5.0 is Z altitude

    # 6. Monitor Altitude until reached
    print("Monitoring altitude...")
    while True:
        # Block the script until we receive the next position message
        msg = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
        
        # PyMAVLink reports relative_alt in millimeters. Convert to meters.
        alt_m = msg.relative_alt / 1000.0 
        print(f"Current Altitude: {alt_m:.2f} m")

        if alt_m >= 4.8:
            print("Target altitude reached! Mission Complete.")
            break

if __name__ == '__main__':
    main()