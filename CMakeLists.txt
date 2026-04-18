cmake_minimum_required(VERSION 3.8)
project(thais_urdf)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch config description hardware_config
  DESTINATION share/${PROJECT_NAME}/
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
  ament_add_pytest_test(xacro_smoke test/test_xacro_smoke.py
    TIMEOUT 180
  )
  ament_add_pytest_test(hardware_config test/test_hardware_config.py
    TIMEOUT 120
  )
endif()

ament_package()
