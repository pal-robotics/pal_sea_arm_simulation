cmake_minimum_required(VERSION 2.8.3)
project(pal_sea_arm_gazebo)

find_package(catkin REQUIRED)

catkin_package(
#  INCLUDE_DIRS include
#  LIBRARIES canopies_gazebo
#  CATKIN_DEPENDS other_catkin_pkg
#  DEPENDS system_lib
)


foreach(dir launch scripts)
    install(DIRECTORY ${dir}/
        DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/${dir})
endforeach(dir)