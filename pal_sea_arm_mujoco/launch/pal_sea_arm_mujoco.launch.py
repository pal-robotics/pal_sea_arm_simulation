# Copyright (c) 2024 PAL Robotics S.L. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import yaml
from os import environ, pathsep
from ament_index_python.packages import get_package_prefix


from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable, SetLaunchConfiguration
from launch.conditions import IfCondition
from launch_pal.include_utils import include_scoped_launch_py_description
from launch_pal.arg_utils import LaunchArgumentsBase
from launch_pal.robot_arguments import CommonArgs
from pal_sea_arm_description.launch_arguments import SEAArmArgs

from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch_pal.param_utils import merge_param_files

from dataclasses import dataclass


@dataclass(frozen=True)
class LaunchArguments(LaunchArgumentsBase):
    end_effector: DeclareLaunchArgument = SEAArmArgs.end_effector
    ft_sensor: DeclareLaunchArgument = SEAArmArgs.ft_sensor
    wrist_model: DeclareLaunchArgument = SEAArmArgs.wrist_model
    moveit: DeclareLaunchArgument = CommonArgs.moveit
    world_name: DeclareLaunchArgument = CommonArgs.world_name
    arm_type: DeclareLaunchArgument = DeclareLaunchArgument(
        'arm_type', default_value='tiago-pro',
        choices=['pal-sea-arm-standalone', 'tiago-pro', 'tiago-sea', 'tiago-sea-dual'],
        description='The arm model')
    mujoco: DeclareLaunchArgument = DeclareLaunchArgument(
        'mujoco', default_value='true', choices=['true', 'false'], description='Mujoco tags')
    mj_position: DeclareLaunchArgument = DeclareLaunchArgument(
        'mj_position', default_value='true', choices=['true', 'false'], description='Mujoco position tags')
    mj_motor: DeclareLaunchArgument = DeclareLaunchArgument(
        'mj_motor', default_value='false', choices=['true', 'false'], description='Mujoco motor tags')
    mj_control: DeclareLaunchArgument = DeclareLaunchArgument(
        'mj_control', default_value='true', choices=['true', 'false'], description='Mujoco Ros2 control tags')
    mj_simulate: DeclareLaunchArgument = DeclareLaunchArgument(
        'mj_simulate', default_value='false', choices=['true', 'false'], description='Mujoco simulation tool tags')

   # TO MODIFY FILE YAML
def declare_actions(launch_description: LaunchDescription, launch_args: LaunchArguments):

    set_sim_time = SetLaunchConfiguration('use_sim_time', 'True')
    launch_description.add_action(set_sim_time)

    # Import controller configuration files
    pal_sea_arm_controller_path = os.path.join(get_package_share_directory('pal_sea_arm_controller_configuration'))
 
    # controller_manager_config_yaml = os.path.join(pal_sea_arm_controller_path, 'config', 'gazebo_controller_manager_cfg.yaml')
    arm_controller_yaml = os.path.join(pal_sea_arm_controller_path, 'config', 'arm_controller.yaml')
    joint_state_broadcaster_yaml = os.path.join(pal_sea_arm_controller_path, 'config', 'joint_state_broadcaster.yaml')

    # Manage argument in the controller configuration file
    with open(arm_controller_yaml, 'r') as f:
        content = f.read()
    arm_content = content.replace('${ARM_SIDE_PREFIX}', f'arm')
    pal_sea_controller_yaml = os.path.join(pal_sea_arm_controller_path, 'config', f'pal_sea_controller_yaml')
    
    with open(pal_sea_controller_yaml, 'w') as arm_file:
        arm_file.write(arm_content)


    merged_yaml = merge_param_files([
                                    # controller_manager_config_yaml,
                                    pal_sea_controller_yaml, 
                                    joint_state_broadcaster_yaml,
                                    ])
    
    print("merged",merged_yaml)
    
    model_pub = Node(
        package='pal_mujoco_model_loader_ros',
        executable='publisher',
        parameters=[{'robot_name': 'pal_sea_arm'}],
        output='screen',
    )
    launch_description.add_action(model_pub)

    node_mujoco_ros2_control = Node(
        package='mujoco_ros2_control',
        executable='mujoco_ros2_control',
        output='screen',
        parameters=[merged_yaml, {'use_sim_time': True}],
    ) 
    launch_description.add_action(node_mujoco_ros2_control)


    # move_group = include_scoped_launch_py_description(
    #     pkg_name='pal_sea_arm_moveit_config',
    #     paths=['launch', 'move_group.launch.py'],
    #     launch_arguments={
    #         "end_effector": launch_args.end_effector,
    #         "ft_sensor": launch_args.ft_sensor,
    #         "wrist_model": launch_args.wrist_model,
    #         "arm_type": launch_args.arm_type,
    #         "use_sim_time": LaunchConfiguration("use_sim_time")},
    #     condition=IfCondition(LaunchConfiguration("moveit")))

    # launch_description.add_action(move_group)

    robot_bringup = include_scoped_launch_py_description(
        pkg_name='pal_sea_arm_bringup', paths=['launch', 'pal_sea_arm_bringup.launch.py'],
        launch_arguments={
            "use_sim_time": LaunchConfiguration("use_sim_time"),
            "arm_type": launch_args.arm_type,
            "end_effector": launch_args.end_effector,
            "ft_sensor": launch_args.ft_sensor,
            "wrist_model": launch_args.wrist_model,
            'mujoco': LaunchConfiguration('mujoco'),
            'mj_position': LaunchConfiguration('mj_position'),
            'mj_motor': LaunchConfiguration('mj_motor'),
            'mj_control': LaunchConfiguration('mj_control'),
            'mj_simulate': LaunchConfiguration('mj_simulate'),
            })

    launch_description.add_action(robot_bringup)


    return

def generate_launch_description():

    # Create the launch description
    ld = LaunchDescription()

    launch_arguments = LaunchArguments()

    launch_arguments.add_to_launch_description(ld)

    declare_actions(ld, launch_arguments)

    return ld

