# SPDX-License-Identifier: GPL-3.0-or-later
# Optional Bukifon engine component.
#
# Empty by default (header-only scaffold).  To build the portable engine:
#   cd firmware/idf_p4/components/bukifon_engine
#   cp ../../../engine_unity.cpp .          # or copy src/ + include/ layout
#   cp -R ../../../src ./src
#   cp -R ../../../include ./include
# See ../README.md and ../../../README.md.
#
# The component stays buildable with no sources until the engine is copied in.
set(BUKIFON_SRCS "")
# Без CONFIGURE_DEPENDS: в script-режиме IDF этот флаг недопустим.
file(GLOB_RECURSE BUKIFON_ENGINE_SOURCES "${CMAKE_CURRENT_LIST_DIR}/src/*.cpp")
if(BUKIFON_ENGINE_SOURCES)
    list(APPEND BUKIFON_SRCS ${BUKIFON_ENGINE_SOURCES})
elseif(EXISTS "${CMAKE_CURRENT_LIST_DIR}/engine_unity.cpp")
    list(APPEND BUKIFON_SRCS "${CMAKE_CURRENT_LIST_DIR}/engine_unity.cpp")
endif()

idf_component_register(
    SRCS ${BUKIFON_SRCS}
    INCLUDE_DIRS "." "src" "include" "app"
    REQUIRES esp_timer
)
