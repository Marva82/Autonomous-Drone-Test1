# ROS 2 & Gazebo: Troubleshooting Model Spawn Failures

When a drone fails to spawn correctly—or spawns but behaves erratically—guessing at the problem will cost you hours. Follow this strict diagnostic order to isolate the issue, and watch out for the four common pitfalls that often trick developers.

## Part 1: The Diagnostic Order

Always run through these four checks sequentially before altering your code.

### 1. Does the description parse correctly?
Before Gazebo even sees your model, you must ensure the Xacro compiler and the URDF parser can read it.
* **Command:** `xacro ~/drone_ws/src/drone_description/urdf/drone.urdf.xacro > /tmp/test.urdf`
* **Command:** `check_urdf /tmp/test.urdf`
* **Success:** You should see a clean breakdown of your links and joints.

### 2. Are the resource files where Gazebo expects them?
If your URDF references 3D meshes, Gazebo must know where the package is actually installed.
* **Command:** `echo $GZ_SIM_RESOURCE_PATH`
* **Command:** `ls ~/drone_ws/install/drone_description/share/drone_description/meshes/`

### 3. Did it actually spawn in the world?
Ask the physics engine directly if the entity exists.
* **Command:** `gz model --list`
* **Success:** You should see `patrol_drone` listed alongside static environment models.

### 4. Is the model doing what you think it is?
Verify its telemetry and check for duplicate publishers.
* **Command:** `gz topic -i -t /imu_sensor`
* **Success:** You should see exactly **1** publisher.

---

## Part 2: The 4 Common Pitfalls (The "Gotchas")

### A. The Missing Resource (Invisible Links)
* **Symptom:** The model spawns, but certain parts are completely invisible.
* **The Cause:** Gazebo cannot resolve the `package://` URI. The file either wasn't installed, or `GZ_SIM_RESOURCE_PATH` isn't set.
* **The Fix:** Rerun `colcon build` and ensure `CMakeLists.txt` is installing the `meshes` directory.

### B. The Missing Inertial Block (The Silent Physics Killer)
* **Symptom:** `check_urdf` is happy, but the drone flips violently or slides across the floor.
* **The Cause:** Gazebo requires a `<mass>` and `<inertia>` block for every physical link. If you miss one, it assigns an undefined inertia tensor.
* **The Danger:** Stripping one link's inertia drops total mass silently (e.g., 1.65 kg -> 1.63 kg).

### C. The Duplicate Name (The Schizophrenic Sensor)
* **Symptom:** Sensor readings jump erratically between two different values.
* **The Cause:** You spawned the drone twice without deleting the first one. You are reading telemetry from two physical entities broadcasting to the exact same topic.
* **The Fix:** Always check `gz topic -i` to ensure you only have one publisher.

### D. The Missing System Plugin (The Ghost Sensor)
* **Symptom:** Perfect `<sensor>` tags in URDF/SDF, but `gz topic -l` shows the topic does not exist.
* **The Cause:** Modern Gazebo is modular. You must explicitly load the system plugin for specific sensor types in your `.sdf` world file.
