cmake_minimum_required(VERSION 3.24)
project(tetwrap LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

find_package(pybind11 CONFIG REQUIRED)

# Canonical TetGen source pin. Fetch only into the build tree; never use a
# developer's ignored vendor directory or accept an unchecked download.
include(FetchContent)
FetchContent_Declare(tetgen
  URL https://codeberg.org/TetGen/TetGen/archive/v1.6.0.tar.gz
  URL_HASH SHA256=3116b53f16c02d5f4681edf9073b4db74fdd306fdc535dab2270a46faaba0dcd
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE
  # Skip upstream CMake targets; compile the two library sources below.
  SOURCE_SUBDIR dtcc-unused-upstream-cmake
)
FetchContent_MakeAvailable(tetgen)
set(TETGEN_DIR "${tetgen_SOURCE_DIR}")
set(TETGEN_SOURCES "${TETGEN_DIR}/tetgen.cxx" "${TETGEN_DIR}/predicates.cxx")

add_library(tet STATIC ${TETGEN_SOURCES})
target_compile_definitions(tet PUBLIC TETLIBRARY)
target_include_directories(tet PUBLIC "${TETGEN_DIR}")

if(APPLE)
  target_link_options(tet PRIVATE "-Wl,-undefined,error")
endif()

pybind11_add_module(_tetwrap tetwrap.cpp)
target_link_libraries(_tetwrap PRIVATE tet)

install(TARGETS _tetwrap
  LIBRARY DESTINATION dtcc_tetgen_wrapper
  RUNTIME DESTINATION dtcc_tetgen_wrapper
)
install(FILES "${TETGEN_DIR}/LICENSE"
  DESTINATION dtcc_tetgen_wrapper/licenses RENAME TetGen-LICENSE.txt)

install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/../../../LICENSE"
  "${CMAKE_CURRENT_SOURCE_DIR}/../../../THIRD_PARTY_NOTICES.md"
  "${CMAKE_CURRENT_SOURCE_DIR}/../../../licenses/pybind11-LICENSE.txt"
  DESTINATION dtcc_tetgen_wrapper/licenses)

if(MSVC)
  target_compile_options(tet PRIVATE /W4)
  target_compile_options(_tetwrap PRIVATE /W4)
else()
  target_compile_options(tet PRIVATE -Wall -Wextra -Wpedantic)
  target_compile_options(_tetwrap PRIVATE -Wall -Wextra -Wpedantic)
endif()
