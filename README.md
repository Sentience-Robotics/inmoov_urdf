# thais_urdf

ROS 2 **Humble** package with the **InMoov-derived** robot description used by Lucy: **URDF/xacro**, **DAE meshes**, **ros2_control** blocks, **Gazebo (gz-sim) physics**, an **RViz** layout, and **launch files** for ros2_control + RViz / Gazebo.

The web control panel (rosbridge + `/config/*` services) is **not** started from here — use `lucy_bringup` (`lucy.launch.py`) or `web_ros_api.launch.py` from `lucy_ros_packages`.

> Historical name: `package.xml` is `thais_urdf` but the content is the InMoov-style description used by Lucy.

## Repository layout

```text
thais_urdf/
├── package.xml              # ROS package: thais_urdf
├── CMakeLists.txt           # Installs launch/, config/, description/, docs/, worlds/
├── docs/                    # Developer + hardware docs (see Documentation map)
├── launch/
│   ├── control.launch.py        # ros2_control + spawners (real robot)
│   ├── gazebo.launch.py         # gz-sim + ros2_control + optional RViz
│   ├── joint_preview.launch.py  # robot_state_publisher + joint_state_publisher_gui + RViz
│   ├── rviz.launch.py           # RViz2 only (used by lucy_bringup)
│   └── rviz_standalone.launch.py # RViz2 only (manual second-terminal use)
├── config/
│   ├── controllers.yaml         # controller_manager + named controllers
│   ├── control.launch.yaml      # defaults for control.launch.py
│   ├── inmoov_rviz.rviz         # RViz layout (visual + collision overlay)
│   └── hardware/
│       ├── active.yaml          # single source of truth for the live mapping
│       ├── active_meta.yaml     # which preset is active + flash metadata
│       └── configs/             # named presets (default / sim / dated snapshots)
├── description/
│   ├── urdf/inmoov.urdf.xacro                    # top-level entry
│   ├── robot_description/
│   │   ├── urdf/properties.xacro                 # model_scale
│   │   ├── urdf/robot_description.urdf.xacro     # links, joints, visuals, collisions, materials
│   │   └── meshes/dae/*.dae                      # 290 Collada meshes (visual + collision)
│   ├── ros2_control/
│   │   ├── inmoov_ros2_control.xacro             # hardware interfaces (real / sim / mock)
│   │   └── inmoov_gz_ros2_control.xacro          # gz_ros2_control plugin (sim only)
│   └── gazebo/
│       └── inmoov_gazebo_physics.xacro           # static / friction / self_collide (sim only)
├── worlds/default.sdf       # minimal world used by gazebo.launch.py
├── scripts/                 # inject_collisions.py, autocalibrate_joint_limits.py, scale_xacro_origins.py
├── test/                    # pytest suite (xacro smoke, YAML, collisions, joint limits)
└── archive/                 # Original InMoov-i1 STL meshes + URDF + PDF (lineage, not runtime)
```

**Install**: `launch/`, `config/`, `description/`, `docs/`, `worlds/` install to `share/thais_urdf/`. The combo launches resolve defaults from `get_package_share_directory("thais_urdf")`; override only for custom trees.

## Relationship to `lucy_ros_packages`

| Repo | Role |
|------|------|
| **`thais_urdf`** (this) | Canonical robot description + sim/visualization entry launches (no rosbridge). |
| **`lucy_ros_packages`** | LUCY bringup (`lucy_bringup`), `LucySystemHardware` plugin, cameras, `web_ros_api` (rosbridge + `lucy_config_pipeline`). |

`lucy_ros2_control` consumes this URDF when both packages share `lucy_ws/src/`. **No** `package.xml` dependency on `lucy_ros2_control` (would create a colcon cycle) — keep both packages in the workspace.

## Requirements

ROS 2 Humble plus: `robot_state_publisher`, `controller_manager`, `rviz2`, `ros_gz_sim`, `ros_gz_bridge`, `gz_ros2_control`, `launch_ros`, `lucy_ros2_control`. The auto-cal script also needs **PyBullet** (already in the `lucy_ros2:humble` image, `pip` otherwise).

```bash
rosdep install --from-paths src --ignore-src -r -y
```

For the control panel, also build `lucy_bringup` + `lucy_config_pipeline` (pulled in via `lucy_bringup`'s `package.xml`).

## Build

```bash
source /opt/ros/humble/setup.bash
cd lucy_ws
colcon build --symlink-install --packages-select thais_urdf lucy_ros2_control
source install/setup.bash
```

`--symlink-install` lets edits to `description/`, `launch/`, `config/`, and `scripts/` be picked up on the next `ros2 launch` without rebuilding. Re-run `colcon build` only after touching `CMakeLists.txt`, `package.xml`, or `test/`.

## Quick launches

```bash
# URDF preview with sliders + RViz (no hardware, no controllers)
ros2 launch thais_urdf joint_preview.launch.py

# Real robot: ros2_control + controllers (RViz in another terminal)
ros2 launch thais_urdf control.launch.py
ros2 launch thais_urdf rviz_standalone.launch.py

# gz-sim + ros2_control + optional RViz
ros2 launch thais_urdf gazebo.launch.py                  # GUI
ros2 launch thais_urdf gazebo.launch.py headless:=true   # server-only, EGL render
ros2 launch thais_urdf gazebo.launch.py start_rviz:=true # spawn RViz too

# Full stack (rosbridge + web panel) — from lucy_bringup
ros2 launch lucy_bringup lucy.launch.py real:=false rviz:=true
ros2 launch lucy_bringup lucy.launch.py gazebo:=true real:=false
```

Common arguments:

| Launch | Arg | Default | Notes |
|--------|-----|---------|-------|
| `control.launch.py` | `urdf_path`, `base_path`, `controllers_yaml`, `use_mock_hardware` | from `config/control.launch.yaml` | `use_mock_hardware:=true` keeps `LucySystemHardware` but sets `publish_actuators:=false` so URDF clamping is enforced without micro-ROS publishing. |
| `gazebo.launch.py` | `urdf_path`, `base_path`, `controllers_yaml`, `headless`, `start_rviz` | package share | `headless:=true` runs `gz sim -s -r --headless-rendering`. |
| `rviz_standalone.launch.py` | `rviz_config`, `use_sim_time` | `config/inmoov_rviz.rviz`, `false` | Use when `/robot_description` + `/joint_states` already exist. |
| `joint_preview.launch.py` | `jsp_gui` | `true` | `false` hides sliders so an external publisher can drive `/joint_states`. |

## Standalone xacro → URDF

Tools that cannot consume xacro (Isaac Sim, offline MoveIt pipelines, the LCP exporter, …):

```bash
ros2 run xacro xacro description/urdf/inmoov.urdf.xacro \
    base_path:=$(pwd)/description \
    use_gazebo_sim:=false \
  | sed 's|file://[^ "]*meshes/dae/\([^"]*\)|meshes/dae/\1|g' \
  > /tmp/robot_description.urdf
```

| Argument | Default | Purpose |
|----------|---------|---------|
| `base_path` | `.` | Parent of `robot_description/`; the xacro appends `/robot_description/meshes/dae`. |
| `use_gazebo_sim` | `false` | `true` enables `gz_ros2_control` plugin + Gazebo physics overrides. |
| `use_mock_hardware` | `false` | `true` keeps `LucySystemHardware` but disables the micro-ROS actuator publisher (URDF clamping still runs). |

`model_scale` is **not** a launch arg — it is a single xacro property in [`description/robot_description/urdf/properties.xacro`](description/robot_description/urdf/properties.xacro) (current value `0.1196`, targets a measured crown height of 1.80 m). The flat URDF is **not** committed; regenerate on demand when needed.

## Tests and CI

```bash
colcon build --symlink-install --packages-select thais_urdf lucy_ros2_control \
  --cmake-args -DBUILD_TESTING=ON
colcon test --packages-select thais_urdf --event-handlers console_direct+
colcon test-result --verbose
```

Local coverage (needs `python3-pytest-cov`):

```bash
mkdir -p build/coverage_reports build/coverage_html
python3 -m pytest src/thais_urdf/test/ \
  --cov=src/thais_urdf/launch --cov=src/thais_urdf/test \
  --cov-report=term-missing \
  --cov-report=xml:build/coverage_reports/thais_urdf.xml \
  --cov-report=html:build/coverage_html/thais_urdf
```

CI: `.github/workflows/ci.yml` builds `thais_urdf` + `lucy_ros2_control`, runs `colcon test`, then `pytest-cov`. Cobertura XML + HTML are uploaded to Codecov (flag `thais_urdf`) when `CODECOV_TOKEN` is set.

## Documentation map

| Doc | Content |
|-----|---------|
| This file | Package scope, build, launches, integration points |
| [**`docs/DEVELOPER.md`**](docs/DEVELOPER.md) | **Editing the URDF**, calibration workflow (collisions + joint limits), xacro architecture, scripts, extension checklist |
| [`docs/hardware_mapping.md`](docs/hardware_mapping.md) | Schema for `config/hardware/active.yaml` (boards, actuators, calibration fields) |
| [`docs/inmoov_i2.md`](docs/inmoov_i2.md) | i1 (current) vs i2 head/expression actuators — YAML appendix |
| `lucy_ros_packages` README | Lucy system bringup, hardware plugin, cameras, web panel |
| `lucy_ws/docs/simulation_and_visualization.md` | Control panel ↔ ROS pipeline and sim-time notes |

## License and assets

- **InMoov-derived** meshes and lineage: see `LICENSE` and attribution (CC BY-NC 4.0, Gael Langevin / InMoov). The original STL set + InMoov.urdf + PDF live under `archive/` for reference.
- **Package code** (launch, xacro, CMake, scripts): **GPL-3.0** per `package.xml`.

## Maintainer

Sentience Robotics Team — `contact@sentience-robotics.fr`.
