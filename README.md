# thais_urdf

ROS 2 **Humble** repository for the **InMoov-derived** robot description used by Lucy: **URDF/xacro**, **meshes**, **ros2_control** xacro blocks, **RViz** configuration, and **launch files** for **ros2_control** plus **RViz** or **Gazebo (GZ Sim)**.

The **web control panel** (rosbridge + hardware **`/config/*`** services) is **not** started from this package; use **`lucy_bringup`** **`lucy.launch.py`** (or **`web_ros_api.launch.py`**) — see workspace **`lucy_ws/README.md`**.

The **`package.xml` name is `thais_urdf`** (historical name; content is the InMoov-style model and tooling).

## Repository layout

```text
thais_urdf/
├── package.xml              # ROS package: thais_urdf
├── CMakeLists.txt           # Installs launch/, config/, description/, docs/
├── docs/                    # Developer + hardware mapping (see Documentation map)
├── launch/
│   ├── control.launch.py    # ros2_control + spawners (default controllers from this package)
│   ├── gazebo.launch.py     # Gazebo + … + optional RViz via start_rviz (no rosbridge)
│   └── rviz_standalone.launch.py
├── config/
│   ├── controllers.yaml
│   ├── inmoov_rviz.rviz
│   └── hardware/            # active.yaml — hardware single source of truth
└── description/
    ├── urdf/inmoov.urdf.xacro
    ├── robot_description/
    ├── ros2_control/
    │   ├── inmoov_ros2_control.xacro
    │   └── inmoov_gazebo.xacro
    └── meshes/
```

**Install:** `launch/`, `config/`, **`description/`**, and **`docs/`** install to **`share/thais_urdf`**. Default `urdf_path` / `base_path` in the combo launches use **`ros2 pkg prefix thais_urdf`**; override only for custom trees.

## Relationship to lucy_ros_packages

| Repo | Role |
|------|------|
| **thais_urdf** (this repo) | Canonical **robot description** and **sim/visualization** entry launches (**no rosbridge**). |
| **[lucy_ros_packages](https://github.com/Sentience-Robotics/lucy_ros_packages)** | **Jetson bringup** (**`lucy_bringup`**), **`LucySystemHardware`**, **camera_ros**, RealSense, **`web_ros_api`** (rosbridge + **`lucy_config_pipeline`**). `lucy_ros2_control` consumes this URDF when using default layout (both repos in one `lucy_ws/src`). |

Default combo launches resolve controller YAML from the **`lucy_ros2_control`** package share (`get_package_share_directory`). Install **`lucy_ros2_control`** in the same workspace/underlay (there is **no** `package.xml` dependency to avoid a build cycle with this package). Keep YAML, xacro joint lists, and teleop/UI config in sync.

## Requirements

- ROS 2 **Humble**
- Packages used by default **`thais_urdf`** launches: `robot_state_publisher`, `controller_manager`, `rviz2`, `ros_gz_sim`, `ros_gz_bridge`, `gz_ros2_control`, `launch_ros`, and **`lucy_ros2_control`** (controller YAML + real-hardware plugin name in xacro). **`lucy_ros2_control`** is not listed in this package’s `package.xml` on purpose (avoids a **`colcon` cycle** with `lucy_ros2_control` → `thais_urdf`); keep both packages in the workspace.

For the **control panel**, also build/source **`lucy_bringup`** and **`lucy_config_pipeline`** (pulled in via **`lucy_bringup`** `package.xml`).

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

### Robot description + RViz or Gazebo (no web panel)

```bash
# Real robot + ros2_control (terminal 1), then RViz only (terminal 2)
ros2 launch thais_urdf control.launch.py
ros2 launch thais_urdf rviz_standalone.launch.py

# Gazebo sim + ros2_control + optional RViz (no rosbridge)
ros2 launch thais_urdf gazebo.launch.py
```

Optional arguments for **`control.launch.py`** and **`gazebo.launch.py`**:

- `urdf_path`, `base_path`, `controllers_yaml` — **`control.launch.py`** (defaults from **`config/control.launch.yaml`**).
- `urdf_path`, `base_path`, `robot_package`, `start_rviz` — **`gazebo.launch.py`**.

### With the web control panel (rosbridge + `/config/*`)

Use **`lucy_bringup`** **`lucy.launch.py`** (single entry; set **`real`**, **`rviz`**, **`gazebo`**):

```bash
ros2 launch lucy_bringup lucy.launch.py real:=false rviz:=true
ros2 launch lucy_bringup lucy.launch.py gazebo:=true real:=false
```

Or start **`web_ros_api.launch.py`** next to **`thais_urdf`** RViz/Gazebo in separate terminals.

### RViz in a second terminal (bringup already running)

Use **`rviz_standalone.launch.py`** when another stack already publishes **`/robot_description`** and **`/joint_states`** — for example **[`lucy_bringup`](https://github.com/Sentience-Robotics/lucy_ros_packages)** has started **`lucy.launch.py`**. This avoids a second **`robot_state_publisher`**, **`ros2_control_node`**, or full control launch on the same graph.

**Terminal 1** (from **`lucy_ros_packages`**, workspace sourced):

```bash
ros2 launch lucy_bringup lucy.launch.py
```

**Terminal 2** (same machine; `source install/setup.bash` from your colcon workspace):

```bash
ros2 launch thais_urdf rviz_standalone.launch.py
```

Optional: `rviz_config:=<path>` — default packaged **`config/inmoov_rviz.rviz`**.

If you run **`lucy_ros2_control`** alone (e.g. `control.launch.py`) instead of full bringup, you can still use the same **`rviz_standalone.launch.py`** as long as `/robot_description` and `/joint_states` are available.

For **RViz + panel** on one machine without full Jetson bringup, use **`ros2 launch lucy_bringup lucy.launch.py real:=false rviz:=true`**.

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
| [**docs/DEVELOPER.md**](docs/DEVELOPER.md) | **Contributors** — URDF/xacro, hardware YAML, launches, install layout, extension checklist |
| [**docs/hardware_mapping.md**](docs/hardware_mapping.md) | Schema and calibration for `config/hardware/active.yaml` |
| [**docs/inmoov_i2.md**](docs/inmoov_i2.md) | i1 scope vs i2 head actuators (YAML appendix) |
| **lucy_ros_packages** repo README | Bringup, hardware control, cameras |
| Workspace **`lucy_ws/docs/developer_lucy_packages.md`** | Index pointing to each repo’s developer doc (paths vary by repo) |
| Workspace **`lucy_ws/docs/simulation_and_visualization.md`** | Control panel ↔ ROS pipeline, sim time, gaps |

## License and assets

- **InMoov-derived** meshes and model lineage: see project **LICENSE** and attribution (e.g. **CC BY-NC 4.0**, Gael Langevin / InMoov project, where applicable).
- **Package code** (launch files, xacro, CMake): **GPL-3.0** per `package.xml` unless stated otherwise.

## Maintainer

Sentience Robotics Team — `contact@sentience-robotics.fr`.
