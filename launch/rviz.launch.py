#!/usr/bin/env python3
# Real robot + RViz + rosbridge. Control panel at ws://localhost:9090.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _get_default_urdf_base(launch_file_path):
    launch_dir = os.path.dirname(os.path.abspath(launch_file_path))
    # From install: .../install/thais_urdf/share/thais_urdf/launch -> 5 levels up to workspace
    if os.path.sep + "install" + os.path.sep in launch_dir or launch_dir.endswith(os.path.sep + "install"):
        workspace = os.path.normpath(os.path.join(launch_dir, "..", "..", "..", "..", ".."))
    else:
        workspace = os.path.normpath(os.path.join(launch_dir, "..", "..", ".."))
    urdf_path = os.path.join(workspace, "src", "thais_urdf", "inmoov", "urdf", "inmoov.urdf.xacro")
    base_path = os.path.join(workspace, "src", "thais_urdf", "inmoov")
    return urdf_path, base_path


def generate_launch_description():
    default_urdf, default_base = _get_default_urdf_base(__file__)
    urdf_path_arg = DeclareLaunchArgument("urdf_path", default_value=default_urdf, description="Path to inmoov.urdf.xacro")
    base_path_arg = DeclareLaunchArgument("base_path", default_value=default_base, description="Base path for xacro (mesh_dir)")
    urdf_path = LaunchConfiguration("urdf_path")
    base_path = LaunchConfiguration("base_path")

    lucy_share = get_package_share_directory("lucy_ros2_control")
    controllers_yaml = os.path.join(lucy_share, "config", "lucy_controllers.yaml")
    robot_description = Command(["xacro ", urdf_path, " base_path:=", base_path])
    robot_description_dict = {"robot_description": robot_description}

    rosbridge = ExecuteProcess(
        cmd=["ros2", "launch", "rosbridge_server", "rosbridge_websocket_launch.xml"],
        output="screen",
        shell=True,
    )

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
        package="controller_manager", executable="spawner", arguments=["joint_state_broadcaster"], output="screen",
    )
    spawn_left = Node(
        package="controller_manager", executable="spawner", arguments=["left_arm_controller"], output="screen",
    )
    spawn_right = Node(
        package="controller_manager", executable="spawner", arguments=["right_arm_controller"], output="screen",
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
        parameters=[{"use_sim_time": False}],
    )

    return LaunchDescription([
        urdf_path_arg, base_path_arg,
        rosbridge,
        robot_state_publisher, ros2_control_node,
        spawn_joint_state, spawn_left, spawn_right,
        rviz,
    ])
