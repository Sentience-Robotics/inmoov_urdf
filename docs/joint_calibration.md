# Joint calibration log

URDF `<limit lower upper>` values in
[`description/robot_description/urdf/robot_description.urdf.xacro`](../description/robot_description/urdf/robot_description.urdf.xacro)
are **set by hand** to match the **mechanically reachable range** of each joint
on the real Lucy. They are intentionally decoupled from `config/hardware/active.yaml`
servo travel: the hardware mapping (`offset_deg`, `direction`, `scale`) handles
the URDF-rad to servo-deg conversion (see
[`hardware_mapping.md`](hardware_mapping.md)).

## Iteration loop

1. Pose the real robot to each mechanical extreme (motors off, hand-back-driven).
2. Read the angle in radians from the URDF frame (joint axis, sign conventions).
3. Edit `<limit lower="..." upper="..."/>` in
   `description/robot_description/urdf/robot_description.urdf.xacro`. Add a
   trailing `<!-- = X deg -->` comment for readability.
4. `colcon build --symlink-install --packages-select thais_urdf`
5. `ros2 launch thais_urdf joint_preview.launch.py` and slide the joint to both
   limits — confirm no chassis interpenetration.
6. Optional automation (no real-world tape needed): see
   [`scripts/autocalibrate_joint_limits.py`](../scripts/autocalibrate_joint_limits.py)
   which sweeps each joint in PyBullet from a neutral pose and records the first
   self-collision angle. Treat its output as an **upper bound** (kinematic
   self-collision envelope), not as the actuator end-stops.

## Calibration table (fill in as joints are measured)

| URDF joint | lower (rad) | upper (rad) | lower (deg) | upper (deg) | Notes |
|------------|-------------|-------------|-------------|-------------|-------|
| `i01.torso.midStom_link_joint` | | | | | |
| `i01.torso.topStom_link_joint` | | | | | |
| `left_shoulder_y_link_joint` | | | | | |
| `left_shoulder_x_link_joint` | | | | | |
| `left_shoulder_z_link_joint` | | | | | |
| `left_elbow_x_link_joint` | | | | | |
| `left_wrist_z_link_joint` | | | | | |
| `right_shoulder_y_link_joint` | | | | | |
| `right_shoulder_x_link_joint` | | | | | |
| `right_shoulder_z_link_joint` | | | | | |
| `right_elbow_x_link_joint` | | | | | |
| `right_wrist_z_link_joint` | | | | | |
| `i01.head.neck.001_link_joint` | | | | | |
| `i01.head.rollNeck_link_joint` | | | | | |
| `i01.head.rothead_link_joint` | | | | | |
| `i01.head.jaw_link_joint` | | | | | |
| `i01.head.eyeRight.001_link_joint` | | | | | |
| `i01.head.eyeRight_link_joint` | | | | | |
| `i01.head.eyeLeft.001_link_joint` | | | | | |
| `i01.head.eyeLeft_link_joint` | | | | | |
| `i01.leftHand.thumb_link_joint` | | | | | |
| `i01.leftHand.index_link_joint` | | | | | |
| `i01.leftHand.majeure_link_joint` | | | | | |
| `i01.leftHand.ringFinger_link_joint` | | | | | |
| `i01.leftHand.pinky_link_joint` | | | | | |
| `i01.rightHand.thumb_link_joint` | | | | | |
| `i01.rightHand.index_link_joint` | | | | | |
| `i01.rightHand.majeure_link_joint` | | | | | |
| `i01.rightHand.ringFinger_link_joint` | | | | | |
| `i01.rightHand.pinky_link_joint` | | | | | |
