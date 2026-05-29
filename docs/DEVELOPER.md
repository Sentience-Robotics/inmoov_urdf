# Developer guide — `thais_urdf`

ROS 2 **Humble**. For **contributors** who change URDF/xacro, meshes, RViz config, **hardware YAML**, or **launch files** in the **`thais_urdf`** package (repository root = one ament package named `thais_urdf`).

**Runtime bringup / hardware plugin / cameras**: `../lucy_ros_packages/docs/DEVELOPER.md` when both repos live under the same workspace `src/`. On GitHub: [Sentience-Robotics/lucy_ros_packages](https://github.com/Sentience-Robotics/lucy_ros_packages) → `docs/DEVELOPER.md`.

---

## 1. Role of this repository

| Concern | Owned here |
|---------|------------|
| Robot **description** (xacro, meshes, limits) | `description/` |
| **ros2_control** blocks (real vs Gazebo plugins) | `description/ros2_control/` |
| **Hardware mapping** (boards, actuators, sensors) | `config/hardware/active.yaml` — see [hardware_mapping.md](hardware_mapping.md) |
| **Controller parameters** for this package’s default bringup | `config/controllers.yaml` (joint lists must stay aligned with ros2_control / URDF) |
| **RViz** saved layout | `config/inmoov_rviz.rviz` |
| **Launches** (RViz and/or GZ Sim + control) | `launch/` |

For **InMoov i2–style** head and expression actuators not present in the current i1 URDF, see [inmoov_i2.md](inmoov_i2.md).

If you use **`lucy_ros_packages`** for Jetson bringup, keep **`lucy_controllers.yaml`** (or equivalent) in sync with **`config/controllers.yaml`** when joint sets overlap.

---

## 2. Layout

```text
thais_urdf/
├── docs/
│   ├── DEVELOPER.md
│   ├── hardware_mapping.md
│   └── inmoov_i2.md
├── package.xml
├── CMakeLists.txt
├── launch/
│   ├── control.launch.py
│   ├── gazebo.launch.py
│   ├── joint_preview.launch.py
│   └── rviz_standalone.launch.py
├── scripts/
│   ├── scale_xacro_origins.py
│   ├── inject_collisions.py
│   └── autocalibrate_joint_limits.py
├── config/
│   ├── controllers.yaml
│   ├── inmoov_rviz.rviz
│   └── hardware/
│       ├── active.yaml
│       └── configs/
├── description/
│   ├── urdf/inmoov.urdf.xacro
│   ├── robot_description/
│   ├── ros2_control/
│   │   ├── inmoov_ros2_control.xacro
│   │   └── inmoov_gazebo.xacro
│   └── meshes/
```

---

## 3. Build and install (`CMakeLists.txt`)

**`launch/`**, **`config/`**, **`description/`**, and **`docs/`** install to `share/thais_urdf/`. Defaults for `urdf_path` and `base_path` in **`gazebo.launch.py`** / **`control.launch.py`** come from **`get_package_share_directory("thais_urdf")`** → `.../description` and `.../description/urdf/inmoov.urdf.xacro` (see **`config/control.launch.yaml`** for **`control.launch.py`**).

**`lucy_ros2_control`** may consume this URDF when both packages are in one workspace. This package does **not** declare **`exec_depend` `lucy_ros2_control`** (avoids a **lucy_ros2_control ↔ thais_urdf** cycle for `colcon`). Combo launches still **require** `lucy_ros2_control` at runtime if you use its default controller YAML path.

---

## 4. Xacro and ros2_control

| File | Role |
|------|------|
| `description/urdf/inmoov.urdf.xacro` | Top-level arguments: `base_path`, `use_gazebo_sim`, `use_mock_hardware`, `controller_config`; includes properties + description + ros2_control (+ Gazebo when sim). |
| `description/robot_description/urdf/properties.xacro` | **`model_scale`** xacro property (default `0.113`). Single source of truth — not a launch arg. |
| `description/robot_description/...` | Links, joints, mesh paths; joint/visual/collision origins and primitive sizes use `${model_scale * …}`. |
| `docs/joint_calibration.md` | Hand-edit log of URDF `<limit>` values; URDF limits and hardware servo limits are **decoupled** (see `hardware_mapping.md`). |
| `description/ros2_control/inmoov_ros2_control.xacro` | Declares hardware/sim systems (e.g. `LucySystemHardware` vs `gz_ros2_control/GazeboSimSystem`). |
| `description/ros2_control/inmoov_gazebo.xacro` | Gazebo spawn / plugin glue for sim. |

Editing joint names or interfaces here requires matching **`config/controllers.yaml`**, **`config/hardware/active.yaml`**, and any teleop/UI joint order (see lucy_ros_packages developer doc).

---

## 5. Launch files (developer notes)

| Launch | Stack |
|--------|-------|
| `control.launch.py` | Real: `robot_state_publisher`, delayed `ros2_control_node`, spawners. Add **`rviz_standalone.launch.py`** in another terminal for RViz. |
| `gazebo.launch.py` | GZ Sim, `/clock` bridge, spawn, `gz_ros2_control` plugin path. Args **`base_path`**. |
| `rviz.launch.py` | RViz2 — use when **`/robot_description`** and **`/joint_states`** already exist. |
| `rviz_standalone.launch.py` | RViz2 only — use when **`/robot_description`** and **`/joint_states`** already exist. |
| **`joint_preview.launch.py`** | **`robot_state_publisher`** + **`joint_state_publisher_gui`** + RViz — sweep URDF limits with sliders (no hardware). |

### URDF calibration loop (collisions + joint limits)

The URDF has two concerns to tune **independently**: **collisions** (rarely
revisited once correct) and **joint limits** (per-joint, by hand or by
auto-sweep against those collisions).

#### A. Pre-flight (every session)

```bash
# Inside the lucy_ros2:humble container (./launch_lucy.sh drops you in one).
cd /workspace
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select thais_urdf
source install/setup.bash
```

`--symlink-install` means edits in `src/thais_urdf/description/**` and
`src/thais_urdf/launch/**` are picked up on the next `ros2 launch` without
rebuilding. Re-run `colcon build` only when you touch `CMakeLists.txt`,
`package.xml`, or files outside `description/`.

#### B. Collisions — manual edit + automatic injection

Collision strategy is **all-mesh, per-visual**: every `<visual><mesh/>` in
every link gets a paired `<collision>` reusing the same origin + mesh
filename. Multi-mesh body links like `torso_y_link` (≈80 sub-DAEs) collide
as their full visual hull, not a single representative DAE. Hand-authored
primitive collisions on root frames (`base_node`, `stand_link`) are
preserved. Mass and inertia tensors are also written here.

**B.1 Manual edit.** Hand-author `<collision>` blocks directly in
`description/robot_description/urdf/robot_description.urdf.xacro`. Each
`<collision>` should mirror the matching `<visual>` origin + mesh filename,
or use a primitive (`<box>`, `<cylinder>`, `<sphere>`) when a mesh is
overkill. Wrap dimensions in `${model_scale * N}` so they follow the global
scale.

**B.2 Automatic injection** (idempotent — collision names are derived from
each visual's `name=`, so re-runs are no-ops unless visuals were added):

```bash
python3 src/thais_urdf/scripts/inject_collisions.py \
  src/thais_urdf/description/robot_description/urdf/robot_description.urdf.xacro
```

**B.3 Visualize in RViz:**

```bash
ros2 launch thais_urdf joint_preview.launch.py
```

The default RViz config (`config/inmoov_rviz.rviz`) has **two** `RobotModel`
displays: opaque visual + translucent collision overlay. In the *Displays*
panel, toggle `RobotModel (Visual)` off to see only collision shapes
(exactly what PyBullet/Gazebo will see); raise `RobotModel (Collision)` alpha
to 1.0 for a solid view. Drive each joint with the `joint_state_publisher_gui`
sliders and look for:

- collisions that obviously don't hug the mesh (visual artifacts in the DAE),
- non-adjacent links interpenetrating at neutral pose (auto-cal will skip
  those joints),
- missing collision on links you care about — every `<visual><mesh/>` should
  have a matching `<collision>`.

#### C. Joint limits — manual + automatic collision-bound calibration

Limits are per-joint, in **radians**, in
`description/robot_description/urdf/robot_description.urdf.xacro`. They are
intentionally **decoupled** from `config/hardware/active.yaml` — the hardware
mapping handles servo↔URDF conversion (see [hardware_mapping.md](hardware_mapping.md)).

Two routes:

**C.1 By hand (preferred for the actuator end-stop)**

**C.1.1** Power off the motors, back-drive the real joint to each mechanical
extreme.

**C.1.2** Read off the angle in URDF radians (mind the joint axis sign).

**C.1.3** Edit the corresponding `<limit lower="..." upper="..."/>` in
`src/thais_urdf/description/robot_description/urdf/robot_description.urdf.xacro`;
add a trailing `<!-- = X deg .. Y deg -->` comment for readability.

**C.1.4** Log the values in [`docs/joint_calibration.md`](joint_calibration.md).

**C.1.5 Reload (one of):**

Quick visual loop with sliders:

```bash
ros2 launch thais_urdf joint_preview.launch.py
```

In a running stack, without relaunching:

```bash
ros2 service call /lucy_control/restart std_srvs/srv/Trigger {}
```

**C.2 Automatic calibration (collision-bound envelope)**

The script expands xacro, loads the URDF in PyBullet
(`URDF_USE_SELF_COLLISION | EXCLUDE_PARENT`), holds every joint at zero,
sweeps each actuated joint upward and downward in fixed-degree increments,
and records the first self-collision angle minus a safety margin. It
streams the sweep into `/joint_states` so you watch it live inside your
existing RViz layout (same model + collision overlay).

```bash
# Stream into your existing RViz config (recommended — same model + collision overlay).
# Terminal 1: launch RViz without the slider GUI so it doesn't fight the publisher.
ros2 launch thais_urdf joint_preview.launch.py jsp_gui:=false
# Terminal 2: drive /joint_states from the sweep at 60 Hz.
python3 src/thais_urdf/scripts/autocalibrate_joint_limits.py --view rviz --rate-hz 60

# Focus on a single joint while debugging (skips all others, can stack --joint).
python3 src/thais_urdf/scripts/autocalibrate_joint_limits.py \
  --view rviz --rate-hz 30 --joint left_shoulder_y --joint left_shoulder_x
```

`--rate-hz` controls the `/joint_states` publish rate fed into RViz;
`--joint <urdf_joint>` is repeatable and isolates a single axis (everything
else is held at zero) for faster iteration when debugging one chain.
`pybullet` is installed in the `lucy_ros2:humble` image via
`Dockerfile.humble` (`pip install pybullet`; no Jammy apt package); for a
host-side run see `src/thais_urdf/scripts/requirements.txt`.

Treat the result as an **upper bound on the kinematic envelope**, not the
real actuator end-stop. Reasons to override the auto-result by hand:
mechanical stops the URDF can't model (cable tension, gear stop), important
poses outside the per-axis sweep from neutral, finger meshes that overlap at
the bind pose.

**Baseline-contact masking.** With the all-mesh collision strategy, sub-meshes
of adjacent links overlap by construction (torso-y/torso-z share material
across the joint, shoulders blend into upper arms, etc.). The script captures
the set of link pairs already in contact at neutral pose and ignores them
during the sweep — only **new** contacts caused by the joint motion stop
the sweep.

#### F. Phase 5 — integrated checks (RViz + Gazebo)

After Phase D looks right, verify in the full stack. **Run from inside the
container** (`./launch_lucy.sh` opens one); `lucy_bringup` orchestrates
`robot_state_publisher`, `ros2_control`, controllers, and the bridge.

```bash
# Mock-hardware path (controllers spawn against GenericSystem; no Gazebo, no real motors).
ros2 launch lucy_bringup lucy.launch.py real:=false rviz:=true

# Headless Gazebo (server-only with EGL rendering — cameras keep producing frames).
ros2 launch lucy_bringup lucy.launch.py gazebo:=true headless:=true

# Gazebo with on-screen viewer + RViz (X11 needed).
ros2 launch lucy_bringup lucy.launch.py gazebo:=true rviz:=true
```

Toggling URDF parameters at runtime: the `lucy_control_supervisor` re-reads
the xacro on demand. After editing the URDF (and `colcon build`-ing if the
share path matters):

```bash
ros2 service call /lucy_control/restart std_srvs/srv/Trigger {}
```

This restarts `robot_state_publisher` + `ros2_control` with the new URDF.
**Caveat**: when the ros2_control topology changes (joints added/removed,
hardware system swapped) Gazebo must be relaunched — the `gz_ros2_control`
plugin is loaded once at world spawn and won't re-read.

**Sim time**: every node in a sim session must agree with `/clock`; if you
add nodes to `gazebo.launch.py`, set `use_sim_time` consistently (see ROS 2
sim time tutorial).

**Arguments** (URDF launches): `urdf_path`, `base_path` — defaults come from
**`get_package_share_directory("thais_urdf")`** (installed `description/`).

**Dependency note**: this package doesn't init the robot. `robot_state_publisher`
must be running before RViz or Gazebo can render the URDF — `lucy_bringup`
sequences this for you (see `lucy.launch.py`).

---

## 6. RViz

- Display config: `config/inmoov_rviz.rviz` — pin RViz version expectations in release notes if visuals break across upgrades.
- Typical chain: `joint_state_broadcaster` → `/joint_states` → `robot_state_publisher` → TF → RobotModel.

---

## 7. Extension checklist (`thais_urdf`)

1. **New link/joint/mesh** → update xacro and collision/visual paths; run `xacro`/`check_urdf` locally.
2. **New ros2_control joint** → edit `inmoov_ros2_control.xacro`, **`config/hardware/active.yaml`**, and **`config/controllers.yaml`** together (and firmware when the generator is wired).
3. **New launch argument** → document in root `README.md` and here if it affects integrators.
4. **Licensing** → InMoov-derived assets: keep `LICENSE` / attribution accurate when adding meshes.

---

## 8. Quick commands

```bash
ros2 launch thais_urdf joint_preview.launch.py
ros2 launch thais_urdf control.launch.py
ros2 launch thais_urdf rviz_standalone.launch.py
ros2 launch thais_urdf gazebo.launch.py headless:=true
# With web panel: lucy_bringup lucy.launch.py real:=false rviz:=true
# Optional: urdf_path:=... base_path:=...
```

---

## 9. CI

Triggers: **pull_request**, and **push** to **`main` / `master` / `dev`** only.

`.github/workflows/ci.yml` uses a **colcon workspace** next to the checkout (not under it), runs **`rosdep install`**, **`colcon build --packages-select thais_urdf`**, **`colcon test`**, then **`pytest-cov`** on `thais_urdf` tests (XML/HTML under `colcon_ws/build/coverage_reports/`, **Codecov** flag `thais_urdf`, optional **`CODECOV_TOKEN`**).

Local commands: see **README.md** → *Tests and coverage (local)*.

---

## 10. Contributing

The repository root **`CONTRIBUTING.md`** must include the **exact GPLv3 “contributing” wording** expected by **`ament_copyright`** (see that file’s first paragraph), plus **`LICENSE`** at the root.

Copyright **2025 Sentience Robotics Team**; same **GPL-3.0** license as the package (see `LICENSE`).

- Open issues and merge requests on the host for this repository.
- Match ROS 2 / ament style; run `colcon test --packages-select thais_urdf` before submitting.
- Update **README.md** or this guide when behavior or layout changes.

See **`CODE_OF_CONDUCT.md`** at the repository root.
