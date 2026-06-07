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
- **`robot_name`**: logical name (e.g. `inmoov`).
- **`passive_urdf_joints`** / **`ignore_urdf_joints`** *(optional)*: string lists merged together; URDF joints named here are **excluded** from the pipeline **“not mapped to any actuator”** cross-check warning. **Synonyms** (same validation rules): `urdf_passive`, `urdf_passive_joints`, `urdf_ignore`, `urdf_ignore_joints`. Cross-check matches **`actuators[].urdf_joint`** against the URDF (not actuator **`id`**). Does **not** remove joints from the URDF or generation elsewhere — only suppresses that informational warning on save.
  - The control panel **Configuration** page also treats `passive_urdf_joints` as the **assignable pool** for new actuators: the **JOINT** dropdown lists every passive entry minus anything in `ignore_urdf_joints` and minus joints already mapped to another actuator. Picking a joint **removes** it from `passive_urdf_joints`; deleting an actuator (or clearing its joint) **re-adds** the freed joint (`appendPassiveUrdfJointIfUnassigned`), so the two lists stay in sync as the operator edits.
- **`firmware`**: `source_dir`, `build_dir` — paths relative to the micro-ROS firmware workspace for the pipeline.
- **`controller_manager`**: e.g. `update_rate`.
- **`boards`**: ordered map of board id → `serial_id` (optional USB serial for `picotool --ser`, alphanumeric or empty), **`board_class`** (`internal_servo_only` \| `internal_servo_i2c_pwm`), **`internal_servo_slots`** (max valid `physical_pin` for actuators on that board), firmware target, compile definition, micro-ROS actuator/sensor topics, and `controller` (`name`, `type`). **Order** of keys is the order of generated ros2_control blocks and controller sections. **Board id** is also the firmware C basename: `config_<board_id>.c`. **No `/dev/ttyACM*`** here — serial devices are launch-time (`lucy_bringup` args), not committed hardware truth.
- **`actuators`**: list of actuators with `urdf_joint` (must match URDF), `board`, `virtual_pin` (contiguous per board, used for firmware ordering and for `JointState.position` indices on that board’s actuator topic), `physical_pin` (**1..`boards.<id>.internal_servo_slots`**: the `N` in `INTERNAL_SERVO_N` emitted in firmware C — not GPIO index and not “+1” from another convention), `servo_type`, calibration (`offset_deg`, `direction`, `scale`), limits, `enabled` (if `false`, the row is still listed in generated `ros2_control` and trajectory controllers, but omitted from firmware C so the servo is not driven on the Pico).
- **`sensors`**: finger pressure sensors; `associated_actuator` references an actuator `id`.

## Hardware angle limits (`servo_*_deg`)

`servo_min_deg`, `servo_max_deg`, and `servo_default_deg` are **servo-frame degrees**: the angle the motor actually sees, before any URDF visualization convention. They bound electrical/mechanical travel in firmware and in **LucySystemHardware** after the URDF→servo mapping.

They are **not** the same as the LCP slider’s joint-space meaning unless `offset_deg = 0`, `direction = ±1`, and `scale = 1`. The control panel slider is labeled in **servo degrees**; trajectory commands on the wire stay in **URDF radians**.

## URDF `<limit>` (joint-space envelope)

Each `urdf_joint` has `<limit lower="…" upper="…"/>` in the URDF (radians). **`lucy_config_generator`** copies those onto each actuated joint’s ros2_control position **command_interface** as `<param name="min">` / `<param name="max">` in `description/ros2_control/inmoov_ros2_control.xacro`. **LucySystemHardware** (real hardware and RViz/mock) clamps `hw_commands_` to that envelope before converting to actuator degrees, so MoveIt, teleop, CLI, and the LCP can command past the URDF wall in the UI but the stack stops at the realized angle. `/joint_states` reports the clamped joint position.

**Gazebo** uses stock **`gz_ros2_control/GazeboSimSystem`**, which does **not** apply those `min`/`max` params in `write()` — only **LucySystemHardware** enforces the ros2_control URDF envelope today. Gazebo may still respect joint limits from the spawned model/physics depending on how the world is built; that is separate from ros2_control clamping. After changing generated limits for real/mock, reload the control stack; for Gazebo topology changes, **restart Gazebo** so `gz_ros2_control` reloads the URDF.

RViz-only / mock hardware uses **`lucy_ros2_control/LucySystemHardware`** with `publish_actuators:=false` so URDF limits are enforced the same way as on real hardware, without micro-ROS topics.

## `offset_deg`, `direction`, and `scale` (URDF command ↔ servo)

Symmetric mapping (used by **LucySystemHardware**, firmware, and the LCP):

```text
joint_deg = (servo_deg - offset_deg) * direction * scale
servo_deg = joint_deg / (direction * scale) + offset_deg
joint_rad = deg_to_rad(joint_deg)
```

- **`direction`**: `+1` or `-1` if the horn is mounted opposite the positive URDF axis.
- **`scale`**: ratio between a change in **commanded joint angle** and **servo angle** when the linkage is not 1:1.
- **`offset_deg`**: shift so URDF “zero” matches the real neutral assembly (e.g. `offset_deg: 90` with a 0–180° servo maps URDF 0° to servo 90°).

These are **calibration between ros2_control / URDF joint commands and the servo command**, not an RViz-only layer. Generated ros2_control params are the source of truth for the plugin and for the panel’s publish/subscribe conversion.

## Shoulder Y joints

`left_shoulder_y_link_joint` and `right_shoulder_y_link_joint` are **torso** joints (servos on `rp2040_torso_head`). Legacy URDF names still say “shoulder”; the YAML assigns them to the torso board so generated ros2_control and firmware stay consistent.

Older InMoov-style actuator tables often name torso PCA pins **5** and **6** as `left_shoulder_pitch_joint` / `right_shoulder_pitch_joint` (legacy naming). This repository’s YAML maps those **same pins** to URDF **`left_shoulder_y_link_joint` / `right_shoulder_y_link_joint`** (Lucy wiring / model).

## Head and expression actuators

Extra head DOFs (eyelids, cheeks, separate eyeball drivers, and so on) are **not** listed in `active.yaml` until the URDF exports matching joint names and each row is validated on hardware. See [inmoov_i2.md](inmoov_i2.md) for a YAML appendix for a future **InMoov i2**–style extension.

## Simulation mode (control panel)

With **SIMULATION ONLY** enabled in the activate workflow, `lucy_config_generator` emits:

- One `<ros2_control>` block per board (`gz_ros2_control/GazeboSimSystem` when `use_gazebo_sim:=true`, otherwise `lucy_ros2_control/LucySystemHardware` with `publish_actuators:=false` for RViz/mock). URDF `min`/`max` on the command interface are enforced by **LucySystemHardware** only (real + mock), not by the stock Gazebo plugin.
- `controllers.yaml` with `joint_state_broadcaster` + a single `lucy_sim_controller` listing every actuator `urdf_joint`.

After generation, `lucy_config_pipeline` calls **`/lucy_control/restart`** so the running stack reloads without a full `lucy.launch.py` restart. Structural joint changes still require that restart (Humble does not hot-swap URDF hardware topology).

## Editing

1. Edit `config/hardware/active.yaml` (or a copy under `configs/`).
2. Run validation (`colcon test --packages-select thais_urdf`) and the generator when implemented.
3. Re-commit generated artifacts (`description/ros2_control/inmoov_ros2_control.xacro`, `config/controllers.yaml`) after regeneration.
