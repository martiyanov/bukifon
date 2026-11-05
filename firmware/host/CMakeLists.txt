# CMake build for the Bukifon host engine (optional; the Makefile is the
# primary path used by tests/run_tests.sh, because this environment has no cmake).
#
#   cmake -S firmware/host -B firmware/host/build-cmake
#   cmake --build firmware/host/build-cmake -j
#   ./firmware/host/build-cmake/bukifon_tests
#   ./firmware/host/build-cmake/bukifon_render firmware/tests/out
cmake_minimum_required(VERSION 3.16)
project(bukifon_host CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

file(GLOB_RECURSE BUKIFON_ENGINE_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/../src/*.cpp")
list(FILTER BUKIFON_ENGINE_SOURCES EXCLUDE REGEX "/hal/")  # Arduino-only headers, no .cpp

add_library(bukifon_engine STATIC ${BUKIFON_ENGINE_SOURCES})
target_include_directories(bukifon_engine PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/../src")

file(GLOB BUKIFON_TEST_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/../tests/*.cpp")
add_executable(bukifon_tests ${BUKIFON_TEST_SOURCES})
target_link_libraries(bukifon_tests PRIVATE bukifon_engine)

add_executable(bukifon_render render_wav.cpp)
target_include_directories(bukifon_render PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(bukifon_render PRIVATE bukifon_engine)
