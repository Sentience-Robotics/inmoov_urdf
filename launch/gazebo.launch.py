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

# Gazebo sim + ros2_control (sim spawners). Optional RViz (``start_rviz``). No rosbridge.

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from lucy_control_supervisor.controllers_spawn import controllers_to_spawn


def _gz_ros2_control_plugin_path():
    try:
        share = get_package_share_directory("gz_ros2_control")
        return os.path.join(os.path.dirname(share), "lib")
    except Exception:
        return "/opt/ros/humble/lib"


def _default_controllers_yaml(pkg_share: str) -> str:
    cwd_candidate = Path.cwd() / "src" / "thais_urdf" / "config" / "controllers.yaml"
    if cwd_candidate.is_file():
        return str(cwd_candidate.resolve())
    return os.path.join(pkg_share, "config", "controllers.yaml")


def generate_launch_description():
    pkg_share = get_package_share_directory("thais_urdf")
    default_base = os.path.join(pkg_share, "description")
    default_controllers = _default_controllers_yaml(pkg_share)

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

    base_path = LaunchConfiguration("base_path")

    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/world/default/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        parameters=[{"use_sim_time": True}],
        remappings=[("/world/default/clock", "/clock")],
        output="screen",
    )

    camera_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/world/default/camera@sensor_msgs/msg/Image[gz.msgs.Image"],
        parameters=[{"use_sim_time": True}],
        remappings=[("/world/default/camera", "/camera/gazebo/raw")],
        output="screen",
    )

    camera_compressor = Node(
        package="image_transport",
        executable="republish",
        remappings=[
            ("in", "/camera/gazebo/raw"),
            ("out/compressed", "/camera/gazebo/compressed"),
        ],
        parameters=[
            {"in_transport": "raw", "out_transport": "compressed", "use_sim_time": True}
        ],
        output="screen",
    )

    try:
        gz_sim_share = get_package_share_directory("ros_gz_sim")
        gz_sim_launch_path = os.path.join(gz_sim_share, "launch", "gz_sim.launch.py")
    except Exception:
        gz_sim_launch_path = "/opt/ros/humble/share/ros_gz_sim/launch/gz_sim.launch.py"

    ros_lib = _gz_ros2_control_plugin_path()
    gz_plugin_path = os.pathsep.join(
        [s for s in [os.environ.get("GZ_SIM_SYSTEM_PLUGIN_PATH", ""), ros_lib] if s]
    ).strip(os.pathsep)
    ign_plugin_path = os.pathsep.join(
        [s for s in [os.environ.get("IGN_GAZEBO_SYSTEM_PLUGIN_PATH", ""), ros_lib] if s]
    ).strip(os.pathsep)

    default_world = os.path.join(pkg_share, "worlds", "default.sdf")
    gz_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_sim_launch_path),
        launch_arguments={"gz_args": f"-r {default_world}"}.items(),
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-name", "lucy", "-topic", "robot_description", "-z", "0.5"],
        output="screen",
        parameters=[{"use_sim_time": True}],
    )
    mesh_dae = PathJoinSubstitution([base_path, "robot_description", "meshes", "dae"])

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
        return [create_spawner(name, delay=float(idx * 2)) for idx, name in enumerate(names)]

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
            }
        ],
    )

    return LaunchDescription(
        [
            base_path_arg,
            controllers_yaml_arg,
            urdf_path_arg,
            SetEnvironmentVariable(name="GZ_SIM_RESOURCE_PATH", value=mesh_dae),
            SetEnvironmentVariable(
                name="GZ_SIM_SYSTEM_PLUGIN_PATH", value=gz_plugin_path
            ),
            SetEnvironmentVariable(
                name="IGN_GAZEBO_SYSTEM_PLUGIN_PATH", value=ign_plugin_path
            ),
            supervisor,
            OpaqueFunction(function=spawner_actions_from_yaml),
            gz_sim_launch,
            clock_bridge,
            camera_bridge,
            camera_compressor,
            spawn_robot,
        ]
    )
