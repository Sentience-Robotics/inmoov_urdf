#!/usr/bin/env python3
# Copyright 2025 Sentience Robotics Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Gazebo Harmonic sim + ros2_control (sim spawners). Optional RViz (``start_rviz``).
# No rosbridge.
#
# ``headless:=true`` runs gz-sim server-only with EGL rendering
# (``gz sim -s -r --headless-rendering``) so camera sensors keep producing
# frames without an X server — the ros_gz camera bridge stays functional.

import os
import shutil
import sys
from pathlib import Path

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PythonExpression,
)
from launch_ros.actions import Node
from lucy_control_supervisor.controllers_spawn import controllers_to_spawn
import yaml


# gz sim refuses to run the server and the Qt GUI in one process on macOS
# (Cocoa wants the GUI on the main thread) and on Windows (gz-sim#168). Both
# need -s for the server plus a second "gz sim -g" for the GUI.
_SPLIT_GZ_GUI = sys.platform in ("darwin", "win32")


def _gz_gui_cmd():
    """argv for the standalone GUI process.

    Resolved rather than named: on Windows gz is a .bat that ExecuteProcess
    will not find, because it does not search PATHEXT.
    """
    return [shutil.which("gz") or "gz", "sim", "-g"]


def _gz_ros2_control_plugin_path():
    pkg_share = get_package_prefix("inmoov_urdf")
    plugin_path = os.path.join(pkg_share, "lib", "mock_sensor")
    try:
        share = get_package_share_directory("gz_ros2_control")
        return os.path.join(os.path.dirname(share), "lib") + os.pathsep + plugin_path
    except Exception:
        return "/opt/ros/jazzy/lib" + os.pathsep + plugin_path


_DEFAULT_GENERATED_FILES = {
    "ros2_control_xacro": "inmoov_ros2_control.xacro",
    "controllers_yaml": "controllers.yaml",
}


def _active_generated_files(pkg_share: str) -> dict[str, str]:
    """Generated-artifact filenames from the active preset (defaults if unreadable)."""
    candidates = [
        Path.cwd() / "src" / "inmoov_urdf" / "config" / "hardware" / "active.yaml",
        Path(pkg_share) / "config" / "hardware" / "active.yaml",
    ]
    out = dict(_DEFAULT_GENERATED_FILES)
    for active in candidates:
        if not active.is_file():
            continue
        try:
            data = yaml.safe_load(active.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return out
        section = data.get("generated_files") if isinstance(data, dict) else None
        if isinstance(section, dict):
            for key in out:
                value = section.get(key)
                if isinstance(value, str) and value.strip() and "/" not in value:
                    out[key] = value.strip()
        return out
    return out


def _default_controllers_yaml(pkg_share: str, controllers_basename: str) -> str:
    cwd_candidate = Path.cwd() / "src" / "inmoov_urdf" / "config" / controllers_basename
    if cwd_candidate.is_file():
        return str(cwd_candidate.resolve())
    return os.path.join(pkg_share, "config", controllers_basename)


def _sim_camera_topics(pkg_share: str) -> list[tuple[str, str]]:
    """LCP-facing (compressed) topics for every camera simulated in Gazebo."""
    candidates = [
        Path.cwd() / "src" / "inmoov_urdf" / "config" / "hardware" / "active.yaml",
        Path(pkg_share) / "config" / "hardware" / "active.yaml",
    ]
    for active in candidates:
        if not active.is_file():
            continue
        try:
            data = yaml.safe_load(active.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return []
        cameras = data.get("cameras") if isinstance(data, dict) else None
        if not isinstance(cameras, list):
            return []
        topics: list[tuple[str, str]] = []
        for cam in cameras:
            if not isinstance(cam, dict):
                continue
            topic = cam.get("topic")
            if not isinstance(topic, str) or not topic.strip():
                continue
            compressed_topic = cam.get("compressed_topic")
            if not isinstance(compressed_topic, str) or not compressed_topic.strip():
                continue
            if cam.get("external"):
                gz_topic = cam.get("sim_gz_topic")
                if not isinstance(gz_topic, str) or not gz_topic.strip():
                    continue
            elif not cam.get("link"):
                continue
            topics.append((topic.strip(), compressed_topic.strip()))
        return topics
    return []


def _gpu_env_actions(context, *args, **kwargs):
    """Headless/Jetson EGL needs a writable runtime dir; GUI must keep the user session dir."""
    headless = LaunchConfiguration("headless").perform(context).lower().strip()
    gpu_mode = os.environ.get("LUCY_GPU_MODE", "").lower()
    actions = []
    if headless in ("true", "1", "yes") or gpu_mode in ("jetson", "nvidia"):
        actions.append(
            SetEnvironmentVariable(name="XDG_RUNTIME_DIR", value="/tmp/runtime-root")
        )
    if gpu_mode in ("jetson", "nvidia"):
        actions.extend(
            [
                SetEnvironmentVariable(
                    name="__EGL_VENDOR_LIBRARY_FILENAMES",
                    value="/usr/share/glvnd/egl_vendor.d/10_nvidia.json",
                ),
                SetEnvironmentVariable(
                    name="__GLX_VENDOR_LIBRARY_NAME", value="nvidia"
                ),
            ]
        )
    else:
        # NixOS: Pixi OGRE needs host Mesa EGL (GLX fails on Wayland/XWayland).
        nix_mesa = "/run/opengl-driver/share/glvnd/egl_vendor.d/50_mesa.json"
        if os.path.isfile(nix_mesa):
            actions.append(
                SetEnvironmentVariable(
                    name="__EGL_VENDOR_LIBRARY_FILENAMES", value=nix_mesa
                )
            )
    if not os.environ.get("GZ_IP"):
        actions.append(SetEnvironmentVariable(name="GZ_IP", value="127.0.0.1"))
    return actions


def generate_launch_description():
    ros_distro = os.environ.get("ROS_DISTRO", "jazzy").lower()
    pkg_share = get_package_share_directory("inmoov_urdf")
    # Pasted into a file:// URI by the xacro, so posix even on Windows.
    default_base = Path(pkg_share, "description").as_posix()
    generated = _active_generated_files(pkg_share)
    default_controllers = _default_controllers_yaml(
        pkg_share, generated["controllers_yaml"]
    )

    base_path_arg = DeclareLaunchArgument(
        "base_path",
        default_value=default_base,
        description="Base path for xacro (mesh_dir)",
    )
    controllers_yaml_arg = DeclareLaunchArgument(
        "controllers_yaml",
        default_value=default_controllers,
        description="Absolute path to controllers.yaml (pipeline write path)",
    )
    urdf_path_arg = DeclareLaunchArgument(
        "urdf_path",
        default_value=os.path.join(default_base, "urdf", "inmoov.urdf.xacro"),
        description="Top-level robot xacro",
    )
    ros2_control_file_arg = DeclareLaunchArgument(
        "ros2_control_file",
        default_value=generated["ros2_control_xacro"],
        description="Generated ros2_control xacro basename (generated_files in active.yaml)",
    )
    headless_arg = DeclareLaunchArgument(
        "headless",
        default_value="false",
        description=(
            "If true: run gz-sim server-only with EGL rendering "
            "(-s -r --headless-rendering). Camera sensors keep producing frames "
            "without an X server, so the ros_gz camera bridge stays functional."
        ),
    )

    bridge_config_path = os.path.join(
        get_package_share_directory("inmoov_urdf"),
        "description",
        "gazebo",
        "gazebo_bridge.yaml",
    )
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[{"use_sim_time": True, "config_file": bridge_config_path}],
        remappings=[("/world/default/clock", "/clock")],
        output="screen",
    )

    # ros_gz_bridge can only emit raw Image; the LCP wants JPEG CompressedImage.
    # For every simulated camera (robot-mounted + external world camera), republish
    # the bridged raw topic -> the compressed topic the LCP subscribes to.
    def _camera_compressor(topic: str, compressed_topic: str) -> Node:
        safe = "".join(c if c.isalnum() else "_" for c in compressed_topic).strip("_")
        if ros_distro == "humble":
            return Node(
                package="image_transport",
                executable="republish",
                name="camera_compressor_" + safe,
                arguments=["raw", "compressed"],
                remappings=[
                    ("in", topic),
                    ("out/compressed", compressed_topic),
                ],
                parameters=[{"use_sim_time": True}],
                output="screen",
            )
        return Node(
            package="image_transport",
            executable="republish",
            name="camera_compressor_" + safe,
            remappings=[
                ("in", topic),
                ("out/compressed", compressed_topic),
            ],
            parameters=[
                {
                    "use_sim_time": True,
                    "in_transport": "raw",
                    "out_transport": "compressed",
                }
            ],
            output="screen",
        )

    camera_compressors = [
        _camera_compressor(topic, compressed_topic)
        for topic, compressed_topic in _sim_camera_topics(pkg_share)
    ]

    ros_lib = _gz_ros2_control_plugin_path()
    gz_plugin_path = os.pathsep.join(
        [s for s in [os.environ.get("GZ_SIM_SYSTEM_PLUGIN_PATH", ""), ros_lib] if s]
    ).strip(os.pathsep)

    try:
        gz_sim_share = get_package_share_directory("ros_gz_sim")
        gz_sim_launch_path = os.path.join(gz_sim_share, "launch", "gz_sim.launch.py")
    except Exception:
        gz_sim_launch_path = "/opt/ros/jazzy/share/ros_gz_sim/launch/gz_sim.launch.py"
    # Embedded in the PythonExpression string literal below, where a Windows
    # path is read as escape sequences: the drive-relative part raises, and a
    # folder starting with n would silently become a newline. Gazebo takes
    # forward slashes on every platform.
    default_world = Path(pkg_share, "worlds", "default.sdf").as_posix()
    # When headless: server-only (-s) with EGL rendering (--headless-rendering)
    # so OGRE2 still renders camera sensors without an X display. Otherwise:
    # normal GUI launch.
    # See _SPLIT_GZ_GUI: macOS and Windows both refuse a combined server+GUI
    # process, so run the server with -s and start the GUI separately below.
    gui_server_args = "-s -r " if _SPLIT_GZ_GUI else "-r "
    gz_args = PythonExpression(
        [
            "'-s -r --headless-rendering ",
            default_world,
            "'",
            " if '",
            LaunchConfiguration("headless"),
            "'.lower() in ('true', '1', 'yes') ",
            "else '",
            gui_server_args,
            default_world,
            "'",
        ]
    )
    gz_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_sim_launch_path),
        launch_arguments={"gz_args": gz_args}.items(),
    )

    # Second process for the Qt GUI on macOS (see gz_args). Delayed so the
    # server's transport is advertising before the GUI connects to it.
    gazebo_gui_actions = []
    if _SPLIT_GZ_GUI:
        gazebo_gui_actions.append(
            TimerAction(
                period=6.0,
                actions=[
                    ExecuteProcess(
                        cmd=_gz_gui_cmd(),
                        name="gazebo_gui",
                        output="screen",
                        condition=UnlessCondition(LaunchConfiguration("headless")),
                    )
                ],
            )
        )

    spawn_robot = TimerAction(
        period=8.0,
        actions=[
            Node(
                package="ros_gz_sim",
                executable="create",
                arguments=["-name", "lucy", "-topic", "robot_description", "-z", "0.0"],
                output="screen",
                parameters=[{"use_sim_time": True}],
            )
        ],
    )
    mesh_dae = get_package_share_directory("inmoov_urdf")

    def create_spawner(name: str, delay: float = 0.0):
        spawner = Node(
            package="controller_manager",
            executable="spawner",
            arguments=[name, "--switch-timeout", "10"],
            output="screen",
            parameters=[{"use_sim_time": True}],
        )
        if delay > 0.0:
            return TimerAction(period=delay, actions=[spawner])
        return spawner

    def spawner_actions_from_yaml(context, *args, **kwargs):
        yaml_path = LaunchConfiguration("controllers_yaml").perform(context)
        names = controllers_to_spawn(Path(yaml_path))
        return [
            create_spawner(name, delay=float(idx * 2)) for idx, name in enumerate(names)
        ]

    supervisor = Node(
        package="lucy_control_supervisor",
        executable="control_supervisor_node",
        name="lucy_control_supervisor",
        output="screen",
        parameters=[
            {
                "urdf_path": LaunchConfiguration("urdf_path"),
                "base_path": LaunchConfiguration("base_path"),
                "controllers_yaml": LaunchConfiguration("controllers_yaml"),
                "use_gazebo_sim": True,
                "gazebo_only": True,
                "autostart": False,
                "ros2_control_file": LaunchConfiguration("ros2_control_file"),
            }
        ],
    )

    return LaunchDescription(
        [
            base_path_arg,
            controllers_yaml_arg,
            urdf_path_arg,
            ros2_control_file_arg,
            headless_arg,
            OpaqueFunction(function=_gpu_env_actions),
            SetEnvironmentVariable(name="GZ_SIM_RESOURCE_PATH", value=mesh_dae),
            SetEnvironmentVariable(
                name="GZ_SIM_SYSTEM_PLUGIN_PATH", value=gz_plugin_path
            ),
            supervisor,
            OpaqueFunction(function=spawner_actions_from_yaml),
            gz_sim_launch,
            *gazebo_gui_actions,
            spawn_robot,
            bridge,
            *camera_compressors,
        ]
    )
