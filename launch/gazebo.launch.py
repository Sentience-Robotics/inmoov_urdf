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

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node


def _gz_ros2_control_plugin_path():
    try:
        share = get_package_share_directory("gz_ros2_control")
        return os.path.join(os.path.dirname(share), "lib")
    except Exception:
        return "/opt/ros/humble/lib"


def generate_launch_description():
    # Paths
    pkg_share = get_package_share_directory("thais_urdf")
    default_base = os.path.join(pkg_share, "description")

    # Launch Arguments
    base_path_arg = DeclareLaunchArgument(
        "base_path",
        default_value=default_base,
        description="Base path for xacro (mesh_dir)",
    )

    base_path = LaunchConfiguration("base_path")

    # Bridge for Clock (Sim Time)
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

    # Gazebo Launch
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

    # Spawn Robot
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-name", "lucy", "-topic", "robot_description", "-z", "0.5"],
        output="screen",
        parameters=[{"use_sim_time": True}],
    )
    mesh_dae = PathJoinSubstitution([base_path, "robot_description", "meshes", "dae"])

    # Controller Spawners
    # These interact with the controller_manager running INSIDE Gazebo (gz_ros2_control)
    def create_spawner(name, delay=0.0):
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

    spawn_jsb = create_spawner("joint_state_broadcaster")
    spawn_left = create_spawner("left_arm_controller", delay=2.0)
    spawn_right = create_spawner("right_arm_controller", delay=4.0)
    spawn_torso = create_spawner("torso_head_controller", delay=6.0)

    return LaunchDescription(
        [
            # Arguments
            base_path_arg,
            # Env Vars
            SetEnvironmentVariable(name="GZ_SIM_RESOURCE_PATH", value=mesh_dae),
            SetEnvironmentVariable(
                name="GZ_SIM_SYSTEM_PLUGIN_PATH", value=gz_plugin_path
            ),
            SetEnvironmentVariable(
                name="IGN_GAZEBO_SYSTEM_PLUGIN_PATH", value=ign_plugin_path
            ),
            # State and Control
            spawn_jsb,
            spawn_left,
            spawn_right,
            spawn_torso,
            # Simulation
            gz_sim_launch,
            clock_bridge,
            camera_bridge,
            camera_compressor,
            spawn_robot,
        ]
    )
