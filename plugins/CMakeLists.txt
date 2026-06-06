cmake_minimum_required(VERSION 3.10)
project(mock_sensor)

find_package(ament_cmake REQUIRED)
find_package(gz-sim8 REQUIRED)
find_package(ros_gz_sim REQUIRED)
find_package(ros_gz_interfaces REQUIRED)
find_package(simulation_interfaces REQUIRED)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_library(mock_sensor SHARED MockSensor.cpp)

set_target_properties(mock_sensor PROPERTIES CXX_VISIBILITY_PRESET default)
ament_target_dependencies(mock_sensor
    ament_cmake
    ros_gz_sim
)
target_link_libraries(mock_sensor
    gz-sim8::gz-sim8
)

install(TARGETS mock_sensor
    DESTINATION lib/${PROJECT_NAME}
)
