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

# Real robot: robot_state_publisher + ros2_control_node + spawners.
# Controllers live in this package (config/controllers.yaml).

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    share = get_package_share_directory("thais_urdf")
    default_base = os.path.join(share, "description")
    default_urdf = os.path.join(default_base, "urdf", "inmoov.urdf.xacro")
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
    urdf_path = LaunchConfiguration("urdf_path")
    base_path = LaunchConfiguration("base_path")

    controllers_yaml = PathJoinSubstitution([
        FindPackageShare("thais_urdf"), "config", "controllers.yaml",
    ])
    robot_description = Command(["xacro ", urdf_path, " base_path:=", base_path])
    robot_description_dict = {"robot_description": robot_description}

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description_dict],
    )
    ros2_control_node = TimerAction(
        period=2.0,
        actions=[
            Node(
                package="controller_manager",
                executable="ros2_control_node",
                output="screen",
                parameters=[controllers_yaml, robot_description_dict],
            )
        ],
    )
    spawn_joint_state = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
        output="screen",
    )
    spawn_left = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["left_arm_controller"],
        output="screen",
    )
    spawn_right = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["right_arm_controller"],
        output="screen",
    )

    return LaunchDescription([
        urdf_path_arg, base_path_arg,
        robot_state_publisher, ros2_control_node,
        spawn_joint_state, spawn_left, spawn_right,
    ])
