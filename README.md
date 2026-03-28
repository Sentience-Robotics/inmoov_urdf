# thais_urdf

ROS 2 **Humble** repository for the **InMoov-derived** robot description used by Lucy: **URDF/xacro**, **meshes**, **ros2_control** xacro blocks, **RViz** configuration, and **combo launch files** that tie together RViz, Gazebo (GZ Sim), `ros2_control`, and `rosbridge` for the web control panel.

The **`package.xml` name is `thais_urdf`** (historical name; content is the InMoov-style model and tooling).

## Repository layout

```text
thais_urdf/
├── package.xml              # ROS package: thais_urdf
├── CMakeLists.txt           # Installs launch/, config/, inmoov/ into share/thais_urdf
├── launch/
│   ├── rviz.launch.py      # Real stack + RViz + rosbridge + ros2_control node + spawners
│   ├── gazebo.launch.py    # Gazebo + clock bridge + spawn + gz_ros2_control + RViz + rosbridge
│   └── rviz_standalone.launch.py
├── config/
│   └── inmoov_rviz.rviz
└── inmoov/
    ├── urdf/inmoov.urdf.xacro           # Top-level xacro (base_path, use_gazebo_sim, controller_config)
    ├── 3dmodel/robot_description.urdf.xacro
    ├── ros2_control/
    │   ├── inmoov_ros2_control.xacro    # Real vs sim ros2_control systems
    │   └── inmoov_gazebo.xacro
    └── meshes/                          # Collision/visual assets (e.g. dae)
```

**Install:** `launch/`, `config/`, and **`inmoov/`** (URDF, meshes) install to **`share/thais_urdf`**. Default `urdf_path` / `base_path` in the combo launches use **`ros2 pkg prefix thais_urdf`**; override only for custom trees.

## Relationship to lucy_ros_packages

| Repo | Role |
|------|------|
| **thais_urdf** (this repo) | Canonical **robot description** and **sim/visualization/rosbridge** entry launches. |
| **[lucy_ros_packages](https://github.com/Sentience-Robotics/lucy_ros_packages)** | **Jetson bringup**, **`LucySystemHardware`**, **camera_ros**, RealSense. `lucy_ros2_control` consumes this URDF when using default layout (both repos in one `lucy_ws/src`). |

Default combo launches resolve controller YAML from the **`lucy_ros2_control`** package share (`get_package_share_directory`). Install **`lucy_ros2_control`** in the same workspace/underlay (there is **no** `package.xml` dependency to avoid a build cycle with this package). Keep YAML, xacro joint lists, and teleop/UI config in sync.

## Requirements

- ROS 2 **Humble**
- Packages used by default combo launches: `robot_state_publisher`, `controller_manager`, `rviz2`, `ros_gz_sim`, `ros_gz_bridge`, `gz_ros2_control`, `rosbridge_server`, `launch_ros`, and **`lucy_ros2_control`** (controller YAML + real-hardware plugin name in xacro). **`lucy_ros2_control`** is not listed in this package’s `package.xml` on purpose (avoids a **`colcon` cycle** with `lucy_ros2_control` → `thais_urdf`); keep both packages in the workspace.

Install other dependencies with `rosdep` from your workspace root when a `ros_distribution` is sourced.

## Building

```bash
# In a colcon workspace that contains this repo under src/
source /opt/ros/humble/setup.bash
cd lucy_ws
colcon build --packages-select thais_urdf
source install/setup.bash
```

For full stack development, build together with `lucy_ros2_control` at minimum:

```bash
colcon build --symlink-install --packages-select thais_urdf lucy_ros2_control
```

## Quick start

```bash
# Real robot + RViz + rosbridge (websocket for control panel, default ws://localhost:9090)
ros2 launch thais_urdf rviz.launch.py

# Gazebo sim + RViz + ros2_control (sim) + rosbridge
ros2 launch thais_urdf gazebo.launch.py
```

Optional launch arguments (both main launches):

- `urdf_path:=<path>` — default: `$(ros2 pkg prefix thais_urdf)/share/thais_urdf/inmoov/urdf/inmoov.urdf.xacro`
- `base_path:=<path>` — default: `.../share/thais_urdf/inmoov` (mesh and xacro include root)

## Tests and coverage (local)

**Dependencies:** `python3-pytest-cov` (e.g. `sudo apt install python3-pytest-cov`).

From your **workspace root**, with `src/thais_urdf` and `src/lucy_ros2_control` (same layout as CI):

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install \
  --packages-select thais_urdf lucy_ros2_control \
  --cmake-args -DBUILD_TESTING=ON
source install/setup.bash

colcon test --packages-select thais_urdf lucy_ros2_control --event-handlers console_direct+
colcon test-result --verbose
```

**Coverage** for this repo’s pytest suite (xacro smoke + launch/test tree):

```bash
mkdir -p build/coverage_reports build/coverage_html
python3 -m pytest src/thais_urdf/test/ \
  --cov=src/thais_urdf/launch \
  --cov=src/thais_urdf/test \
  --cov-report=term-missing \
  --cov-report=xml:build/coverage_reports/thais_urdf.xml \
  --cov-report=html:build/coverage_html/thais_urdf
```

Tests call **`xacro`** on the URDF; coverage mainly reflects **test + launch** Python lines, not meshes or C++.

## CI

**GitHub Actions** (`.github/workflows/ci.yml`) builds `thais_urdf` and `lucy_ros2_control`, runs **`colcon test`**, then **`pytest-cov`** for `src/thais_urdf/test/`. Cobertura XML and HTML are uploaded to [**Codecov**](https://codecov.io) (flag `thais_urdf`) when **`CODECOV_TOKEN`** is set, and stored as artifact `coverage-thais_urdf`.

## Documentation map

| Doc | Content |
|-----|---------|
| This file | Repository scope and integration |
| [**doc/DEVELOPER.md**](doc/DEVELOPER.md) | **Contributors** — URDF/xacro, launches, install layout, extension checklist |
| **lucy_ros_packages** repo README | Bringup, hardware control, cameras |
| Workspace **`lucy_ws/docs/developer_lucy_packages.md`** | Index pointing to each repo’s `doc/DEVELOPER.md` |
| Workspace **`lucy_ws/docs/simulation_and_visualization.md`** | Control panel ↔ ROS pipeline, sim time, gaps |

## License and assets

- **InMoov-derived** meshes and model lineage: see project **LICENSE** and attribution (e.g. **CC BY-NC 4.0**, Gael Langevin / InMoov project, where applicable).
- **Package code** (launch files, xacro, CMake): **GPL-3.0** per `package.xml` unless stated otherwise.

## Maintainer

Sentience Robotics Team — `contact@sentience-robotics.fr`.
