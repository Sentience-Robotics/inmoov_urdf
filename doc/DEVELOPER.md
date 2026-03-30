# Developer guide — `thais_urdf`

ROS 2 **Humble**. For **contributors** who change URDF/xacro, meshes, RViz config, or **launch files** in the **`thais_urdf`** package (repository root = oneament package named `thais_urdf`).

**Runtime bringup / hardware plugin / cameras**: `../lucy_ros_packages/doc/DEVELOPER.md` when both repos live under the same workspace `src/`. On GitHub: [Sentience-Robotics/lucy_ros_packages](https://github.com/Sentience-Robotics/lucy_ros_packages) → `doc/DEVELOPER.md`.

---

## 1. Role of this repository

| Concern | Owned here |
|---------|------------|
| Robot **description** (xacro, meshes, limits) | `inmoov/` |
| **ros2_control** blocks (real vs Gazebo plugins) | `inmoov/ros2_control/` |
| **RViz** saved layout | `config/inmoov_rviz.rviz` |
| **Combo launches** (RViz and/or GZ Sim + rosbridge + control) | `launch/` |

Controller **parameters** (`joint_trajectory_controller`, etc.) live in **`lucy_ros_packages`** → `lucy_ros2_control/config/lucy_controllers.yaml`. Launches pass `controller_config` into xacro; keep YAML and xacro **joint lists identical**.

---

## 2. Layout

```text
thais_urdf/
├── doc/DEVELOPER.md
├── package.xml
├── CMakeLists.txt
├── launch/
│   ├── rviz.launch.py
│   ├── gazebo.launch.py
│   └── rviz_standalone.launch.py
├── config/
│   └── inmoov_rviz.rviz
└── inmoov/
    ├── urdf/inmoov.urdf.xacro
    ├── 3dmodel/robot_description.urdf.xacro
    ├── ros2_control/
    │   ├── inmoov_ros2_control.xacro
    │   └── inmoov_gazebo.xacro
    └── meshes/
```

---

## 3. Build and install (`CMakeLists.txt`)

**`launch/`**, **`config/`**, and **`inmoov/`** are installed to `share/thais_urdf/`. Defaults for `urdf_path` and `base_path` in **`rviz.launch.py`** / **`gazebo.launch.py`** come from **`get_package_share_directory("thais_urdf")`** → `.../inmoov` and `.../inmoov/urdf/inmoov.urdf.xacro`.

**`lucy_ros2_control`** **`control.launch.py`** uses the same share paths and **`exec_depend`s `thais_urdf`**. This package does **not** declare **`exec_depend` `lucy_ros2_control`** (that would create **lucy_ros2_control ↔ thais_urdf** cycle for `colcon`). Combo launches still **require** `lucy_ros2_control` at runtime for the default `lucy_controllers.yaml` path.

---

## 4. Xacro and ros2_control

| File | Role |
|------|------|
| `inmoov/urdf/inmoov.urdf.xacro` | Top-level arguments: `base_path`, `use_gazebo_sim`, `controller_config`; includes description + ros2_control (+ Gazebo when sim). |
| `inmoov/3dmodel/robot_description.urdf.xacro` | Links, joints, mesh paths. |
| `inmoov/ros2_control/inmoov_ros2_control.xacro` | Declares hardware/sim systems (e.g. `LucySystemHardware` vs `gz_ros2_control/GazeboSimSystem`). |
| `inmoov/ros2_control/inmoov_gazebo.xacro` | Gazebo spawn / plugin glue for sim. |

Editing joint names or interfaces here requires matching **`lucy_controllers.yaml`** and any teleop/UI joint order (see lucy_ros_packages developer doc).

---

## 5. Launch files (developer notes)

| Launch | Stack |
|--------|--------|
| `rviz.launch.py` | Real-oriented: `robot_state_publisher`, delayed `ros2_control_node`, spawners, rosbridge, RViz (`use_sim_time: false`). |
| `gazebo.launch.py` | GZ Sim, `/clock` bridge, spawn, `gz_ros2_control` plugin path, rosbridge, RViz (`use_sim_time: true` where applicable). |

**Arguments** (both): `urdf_path`, `base_path` — defaults come from **`get_package_share_directory("thais_urdf")`** (installed `inmoov/`).

**Sim time**: every node in a sim session must agree with `/clock`; if you add nodes to `gazebo.launch.py`, set `use_sim_time` consistently (see ROS 2 sim time tutorial).

---

## 6. RViz

- Display config: `config/inmoov_rviz.rviz` — pin RViz version expectations in release notes if visuals break across upgrades.
- Typical chain: `joint_state_broadcaster` → `/joint_states` → `robot_state_publisher` → TF → RobotModel.

---

## 7. Extension checklist (`thais_urdf`)

1. **New link/joint/mesh** → update xacro and collision/visual paths; run `xacro`/`check_urdf` locally.
2. **New ros2_control joint** → edit `inmoov_ros2_control.xacro` **and** `lucy_controllers.yaml` (sibling repo) together.
3. **New launch argument** → document in root `README.md` and here if it affects integrators.
4. **Licensing** → InMoov-derived assets: keep `LICENSE` / attribution accurate when adding meshes.

---

## 8. Quick commands

```bash
ros2 launch thais_urdf rviz.launch.py
ros2 launch thais_urdf gazebo.launch.py
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
