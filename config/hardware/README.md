# Hardware mapping (YAML)

`active.yaml` is the **single source of truth** for Lucy hardware: RP2040 boards, actuators, and finger pressure sensors. The micro-ROS config generator will read this file and emit firmware C, `description/ros2_control/inmoov_ros2_control.xacro`, and `config/controllers.yaml`.

## Layout

| Path | Role |
|------|------|
| `active.yaml` | Active mapping used for generation and validation |
| `active_meta.yaml` | `{ name, activated_at }` for the active slot |
| `configs/*.yaml` | Named presets (e.g. `default.yaml` mirrors the last activated snapshot) |
| `backups/` | Automatic backups before activation |

## Top-level keys

- **`version`**: schema version (integer, currently `1`).
- **`robot_name`**: logical name (e.g. `thais`).
- **`firmware`**: `source_dir`, `build_dir` — paths relative to the micro-ROS firmware workspace for the pipeline.
- **`controller_manager`**: e.g. `update_rate`.
- **`boards`**: map of board id → serial, device path, firmware target, compile definition, micro-ROS actuator/sensor topics, and `controller` (`name`, `type`) for ros2_control.
- **`actuators`**: list of actuators with `urdf_joint` (must match URDF), `board`, `virtual_pin` (contiguous per board, used for firmware ordering), `physical_pin`, `servo_type`, calibration (`offset_deg`, `direction`, `scale`), limits, `enabled`.
- **`sensors`**: finger pressure sensors; `associated_actuator` references an actuator `id`.

## Hardware angle limits (`servo_*_deg`)

Values sent to real servos are expressed in **degrees in the servo’s own range**. This is independent of how the URDF might visualize the joint (often symmetric angles); the mapping from **URDF / ros2_control command** to **hardware command** is what `offset_deg`, `direction`, and `scale` are for (see below).

## `offset_deg`, `direction`, and `scale` (URDF command → hardware)

These fields tune how a **trajectory command in joint space** (what `joint_trajectory_controller` and the URDF use for that `urdf_joint`) is converted to the **angle actually sent to the servo** (within `[servo_min_deg, servo_max_deg]`):

- **`direction`**: `+1` or `-1` to flip motion if the horn is mounted opposite to the positive URDF axis.
- **`scale`**: ratio between a change in **commanded joint angle** and a change in **servo angle** when the mechanism is not 1:1 (gear reduction, non-linear linkage approximated as linear, etc.).
- **`offset_deg`**: constant shift after direction/scale so that “zero” in the controller matches the real neutral pose for that hardware assembly.

So they are **calibration between ros2_control / URDF joint values and real actuator commands**, not a separate “RViz-only” layer. Gazebo (ideal model) may ignore them unless the sim stack is extended to mimic the same mapping; the **LucySystemHardware** plugin and firmware are the consumers of these parameters once generated into ros2_control.

## Shoulder Y joints

`left_shoulder_y_link_joint` and `right_shoulder_y_link_joint` are **torso** joints (servos on `rp2040_torso_head`). Legacy URDF names still say “shoulder”; the YAML assigns them to the torso board so generated ros2_control and firmware stay consistent.

On **`hardware_config/inmoov_actuators_config.xacro`**, torso PCA pins **5** and **6** are named `left_shoulder_pitch_joint` / `right_shoulder_pitch_joint` (legacy). The YAML maps those **same pins** to URDF **`left_shoulder_y_link_joint` / `right_shoulder_y_link_joint`** (actual wiring / model).

## Parity with `hardware_config/*.xacro`

- **Torso/head block in xacro** (pins 1–4, 6+, many `type="180"` rows): several **joint_name** entries do **not** match current **URDF** joint names (e.g. `jaw_joint` vs `i01.head.jaw_link_joint`). They are **omitted** here until each row is mapped to a real `urdf_joint` (follow-up for full head/torso coverage in the generator milestone).

## Editing

1. Edit `active.yaml` (or a copy under `configs/`).
2. Run validation (`colcon test --packages-select thais_urdf`) and the generator when implemented.
3. Re-commit generated artifacts (`inmoov_ros2_control.xacro`, `controllers.yaml`) after regeneration.
