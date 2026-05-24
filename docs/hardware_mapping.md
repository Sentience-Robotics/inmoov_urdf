# Hardware mapping (YAML)

`config/hardware/active.yaml` is the **single source of truth** for Lucy hardware: RP2040 boards, actuators, and finger pressure sensors. The **`lucy_config_generator`** package (in `lucy_ros_packages`) reads this file and emits firmware C, `description/ros2_control/inmoov_ros2_control.xacro`, and `config/controllers.yaml`.

For **InMoov i1 vs i2** scope and how to extend the YAML with **head / expression** actuators when the URDF evolves, see [inmoov_i2.md](inmoov_i2.md).

## Layout

| Path | Role |
|------|------|
| `config/hardware/active.yaml` | Active mapping used for generation and validation |
| `config/hardware/active_meta.yaml` | `{ name, activated_at }` for the active slot; optional `{ flashed_name, flashed_at }` after a successful pipeline flash |
| `config/hardware/configs/*.yaml` | Named presets (e.g. `default.yaml` mirrors the last activated snapshot) |
| `config/hardware/backups/` | Automatic backups before activation |

## Top-level keys

- **`version`**: schema version (integer, currently `1`).
- **`robot_name`**: logical name (e.g. `thais`).
- **`passive_urdf_joints`** / **`ignore_urdf_joints`** *(optional)*: string lists merged together; URDF joints named here are **excluded** from the pipeline **“not mapped to any actuator”** cross-check warning. **Synonyms** (same validation rules): `urdf_passive`, `urdf_passive_joints`, `urdf_ignore`, `urdf_ignore_joints`. Cross-check matches **`actuators[].urdf_joint`** against the URDF (not actuator **`id`**). Does **not** remove joints from the URDF or generation elsewhere — only suppresses that informational warning on save.
  - The control panel **Configuration** page also treats `passive_urdf_joints` as the **assignable pool** for new actuators: the **JOINT** dropdown lists every passive entry minus anything in `ignore_urdf_joints` and minus joints already mapped to another actuator. Picking a joint **removes** it from `passive_urdf_joints`; deleting an actuator (or clearing its joint) **re-adds** the freed joint (`appendPassiveUrdfJointIfUnassigned`), so the two lists stay in sync as the operator edits.
- **`firmware`**: `source_dir`, `build_dir` — paths relative to the micro-ROS firmware workspace for the pipeline.
- **`controller_manager`**: e.g. `update_rate`.
- **`boards`**: ordered map of board id → `serial_id` (optional USB serial for `picotool --ser`, alphanumeric or empty), **`board_class`** (`internal_servo_only` \| `internal_servo_i2c_pwm`), **`internal_servo_slots`** (max valid `physical_pin` for actuators on that board), firmware target, compile definition, micro-ROS actuator/sensor topics, and `controller` (`name`, `type`). **Order** of keys is the order of generated ros2_control blocks and controller sections. **Board id** is also the firmware C basename: `config_<board_id>.c`. **No `/dev/ttyACM*`** here — serial devices are launch-time (`lucy_bringup` args), not committed hardware truth.
- **`actuators`**: list of actuators with `urdf_joint` (must match URDF), `board`, `virtual_pin` (contiguous per board, used for firmware ordering and for `JointState.position` indices on that board’s actuator topic), `physical_pin` (**1..`boards.<id>.internal_servo_slots`**: the `N` in `INTERNAL_SERVO_N` emitted in firmware C — not GPIO index and not “+1” from another convention), `servo_type`, calibration (`offset_deg`, `direction`, `scale`), limits, `enabled` (if `false`, the row is still listed in generated `ros2_control` and trajectory controllers, but omitted from firmware C so the servo is not driven on the Pico).
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

Older InMoov-style actuator tables often name torso PCA pins **5** and **6** as `left_shoulder_pitch_joint` / `right_shoulder_pitch_joint` (legacy naming). This repository’s YAML maps those **same pins** to URDF **`left_shoulder_y_link_joint` / `right_shoulder_y_link_joint`** (Lucy wiring / model).

## Head and expression actuators

Extra head DOFs (eyelids, cheeks, separate eyeball drivers, and so on) are **not** listed in `active.yaml` until the URDF exports matching joint names and each row is validated on hardware. See [inmoov_i2.md](inmoov_i2.md) for a YAML appendix for a future **InMoov i2**–style extension.

## Editing

1. Edit `config/hardware/active.yaml` (or a copy under `configs/`).
2. Run validation (`colcon test --packages-select thais_urdf`) and the generator when implemented.
3. Re-commit generated artifacts (`description/ros2_control/inmoov_ros2_control.xacro`, `config/controllers.yaml`) after regeneration.
