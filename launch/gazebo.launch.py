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

# Gazebo sim + RViz + ros2_control (sim spawners) + rosbridge.
# Control panel at ws://localhost:9090.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    LaunchConfiguration,
    PathJoinSubstitution,
    TextSubstitution,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _gz_ros2_control_plugin_path():
    try:
        share = get_package_share_directory("gz_ros2_control")
        return os.path.join(os.path.dirname(share), "lib")
    except Exception:
        return "/opt/ros/humble/lib"


def generate_launch_description():
    share = get_package_share_directory("thais_urdf")
    default_base = os.path.join(share, "inmoov")
    default_urdf = os.path.join(default_base, "urdf", "inmoov.urdf.xacro")
    lucy_share = get_package_share_directory("lucy_ros2_control")
    controller_config_path = os.path.join(lucy_share, "config", "lucy_controllers.yaml")

    urdf_path_arg = DeclareLaunchArgument(
        "urdf_path",
        default_value=default_urdf,
        description="Path to inmoov.urdf.xacro",
    )
    base_path_arg = DeclareLaunchArgument(
        "base_path",
        default_value=default_base,
        description="Base path for xacro (mesh_dir)",
    )

    rosbridge = ExecuteProcess(
        cmd=["ros2", "launch", "rosbridge_server", "rosbridge_websocket_launch.xml"],
        output="screen",
        shell=True,
    )

    urdf_path = LaunchConfiguration("urdf_path")
    base_path = LaunchConfiguration("base_path")
    mesh_dae = PathJoinSubstitution([base_path, "meshes", "dae"])
    gz_resource_path = [mesh_dae, TextSubstitution(text=os.pathsep), base_path]

    robot_description = Command([
        "xacro ", urdf_path,
        " base_path:=", base_path,
        " use_gazebo_sim:=true",
        " controller_config:=", controller_config_path,
    ])
    robot_description_dict = {"robot_description": robot_description}

    try:
        _gz_sim_share = get_package_share_directory("ros_gz_sim")
        _gz_sim_launch_path = os.path.join(_gz_sim_share, "launch", "gz_sim.launch.py")
    except Exception:
        _gz_sim_launch_path = "/opt/ros/humble/share/ros_gz_sim/launch/gz_sim.launch.py"

    gz_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(_gz_sim_launch_path),
        launch_arguments={"gz_args": "-r empty.sdf"}.items(),
    )

    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description_dict, {"use_sim_time": True}],
    )

    spawn_lucy_gazebo = TimerAction(
        period=4.0,
        actions=[
            Node(
                package="ros_gz_sim",
                executable="create",
                name="spawn_lucy",
                arguments=["-name", "lucy", "-param", "robot_description", "-z", "0.5"],
                parameters=[robot_description_dict],
                output="screen",
            )
        ],
    )

    ros_lib = _gz_ros2_control_plugin_path()
    gz_plugin_path = os.pathsep.join(
        [s for s in [os.environ.get("GZ_SIM_SYSTEM_PLUGIN_PATH", ""), ros_lib] if s]
    ).strip(os.pathsep)
    ign_plugin_path = os.pathsep.join(
        [s for s in [os.environ.get("IGN_GAZEBO_SYSTEM_PLUGIN_PATH", ""), ros_lib] if s]
    ).strip(os.pathsep)

    spawn_joint_state_sim = TimerAction(
        period=0.0,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=["joint_state_broadcaster", "--switch-timeout", "10"],
                output="screen",
            )
        ],
    )
    spawn_left_sim = TimerAction(
        period=0.5,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=["left_arm_controller", "--switch-timeout", "10"],
                output="screen",
            )
        ],
    )
    spawn_right_sim = TimerAction(
        period=1.0,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=["right_arm_controller", "--switch-timeout", "10"],
                output="screen",
            )
        ],
    )

    rviz_config = PathJoinSubstitution([
        FindPackageShare("thais_urdf"), "config", "inmoov_rviz.rviz",
    ])
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["--display-config", rviz_config],
        parameters=[{"use_sim_time": True}],
    )

    return LaunchDescription([
        urdf_path_arg,
        base_path_arg,
        rosbridge,
        SetEnvironmentVariable(name="GZ_SIM_RESOURCE_PATH", value=gz_resource_path),
        SetEnvironmentVariable(name="GZ_SIM_SYSTEM_PLUGIN_PATH", value=gz_plugin_path),
        SetEnvironmentVariable(name="IGN_GAZEBO_SYSTEM_PLUGIN_PATH", value=ign_plugin_path),
        gz_sim_launch,
        clock_bridge,
        robot_state_publisher,
        spawn_lucy_gazebo,
        spawn_joint_state_sim,
        spawn_left_sim,
        spawn_right_sim,
        rviz,
    ])
