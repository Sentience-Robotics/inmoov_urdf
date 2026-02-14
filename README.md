# thais_urdf

InMoov URDF and **combo launch files** for this workspace: RViz + rosbridge and Gazebo + RViz + rosbridge.

## In this workspace

- **URDF / meshes** — `inmoov/` (xacro, meshes). Used by both packages.
- **RViz config** — `config/inmoov_rviz.rviz`.
- **Launch (thais_urdf only)** — two standalone files:
  - **rviz.launch.py** — Real robot + RViz + rosbridge. Control panel at ws://localhost:9090.
  - **gazebo.launch.py** — Gazebo sim + RViz + ros2_control (sim spawners) + rosbridge.

## Usage

```bash
# Real + RViz + control panel
ros2 launch thais_urdf rviz.launch.py

# Gazebo sim + RViz + control panel
ros2 launch thais_urdf gazebo.launch.py
```

Optional: `urdf_path:=<path>` `base_path:=<path>`.

## License

This repo provides the **URDF model** for the InMoov robot (Blender/Phobos, ROS-compatible).
InMoov-derived assets: CC BY-NC 4.0 (Gael Langevin); project code: GPL-3.0. See [LICENSE](LICENSE).
