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
│   └── rviz_standalone.launch.py
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
| `description/urdf/inmoov.urdf.xacro` | Top-level arguments: `base_path`, `use_gazebo_sim`, `controller_config`; includes description + ros2_control (+ Gazebo when sim). |
| `description/robot_description/...` | Links, joints, mesh paths (included from top-level xacro). |
| `description/ros2_control/inmoov_ros2_control.xacro` | Declares hardware/sim systems (e.g. `LucySystemHardware` vs `gz_ros2_control/GazeboSimSystem`). |
| `description/ros2_control/inmoov_gazebo.xacro` | Gazebo spawn / plugin glue for sim. |

Editing joint names or interfaces here requires matching **`config/controllers.yaml`**, **`config/hardware/active.yaml`**, and any teleop/UI joint order (see lucy_ros_packages developer doc).

---

## 5. Launch files (developer notes)

| Launch | Stack |
|--------|-------|
| `control.launch.py` | Real: `robot_state_publisher`, delayed `ros2_control_node`, spawners. Add **`rviz_standalone.launch.py`** in another terminal for RViz. |
| `gazebo.launch.py` | GZ Sim, `/clock` bridge, spawn, `gz_ros2_control` plugin path, optional RViz via **`start_rviz`**. Args **`urdf_path`**, **`base_path`**, **`robot_package`**, **`start_rviz`**. |
| `rviz_standalone.launch.py` | RViz2 only — use when **`/robot_description`** and **`/joint_states`** already exist. |

**Arguments** (URDF launches): `urdf_path`, `base_path` — defaults come from **`get_package_share_directory("thais_urdf")`** (installed `description/`).

**Sim time**: every node in a sim session must agree with `/clock`; if you add nodes to `gazebo.launch.py`, set `use_sim_time` consistently (see ROS 2 sim time tutorial).

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
ros2 launch thais_urdf control.launch.py
ros2 launch thais_urdf rviz_standalone.launch.py
ros2 launch thais_urdf gazebo.launch.py
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
