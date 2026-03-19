cmake_minimum_required(VERSION 3.26)

project (THAMES)

set (THAMES_VERSION 5.2.0)
set (THAMES_VERSION_MAJOR 5)
set (THAMES_VERSION_MINOR 2.0)

# Use find_package for vcpkg-managed libraries
find_package(PNG REQUIRED)
find_package(ZLIB REQUIRED)

# getopt library - MSVC only (Unix and MinGW have it built-in)
if(MSVC)
    find_package(unofficial-getopt-win32 REQUIRED)
    set(EXTRA_LIBS ${EXTRA_LIBS} unofficial::getopt-win32::getopt)
endif()

# Math library handling - not needed on MSVC, required on Unix and MinGW
if(NOT MSVC)
    find_library(MATH_LIB NAMES m libm HINTS "/usr/lib" "/c/msys64/mingw64/lib")
    if(MATH_LIB)
        message("Found MATH_LIB: [${MATH_LIB}]")
        set(EXTRA_LIBS ${EXTRA_LIBS} ${MATH_LIB})
    else()
        message(WARNING "Did not find MATH lib - continuing without it")
    endif()
endif()

# Set up library list
set(EXTRA_LIBS ${EXTRA_LIBS} PNG::PNG ZLIB::ZLIB)
message("EXTRA_LIBS: " ${EXTRA_LIBS})

# Use include_directories instead of manual -I flags to handle special characters in paths
# Note: PNG/ZLIB headers come from vcpkg on MSVC, MinGW and Unix need custom include paths
if(NOT MSVC)
    include_directories("${CMAKE_SOURCE_DIR}/include")
    include_directories("${CMAKE_SOURCE_DIR}/src/include")
    if(UNIX)
        include_directories("/usr/local/include")
    endif()
endif()

# Platform-specific compiler flags
if(MSVC)
    set(CMAKE_C_FLAGS "/O2")
else()
    set(CMAKE_C_FLAGS "-O2")
endif()

message ("Top level CMAKE_C_FLAGS: " ${CMAKE_C_FLAGS})
message ("Linked libraries are: " ${EXTRA_LIBS})

add_subdirectory (${CMAKE_SOURCE_DIR}/src/thamesauxlib)
add_subdirectory (${CMAKE_SOURCE_DIR}/src/zlib)

add_executable (micgen ${CMAKE_SOURCE_DIR}/src/micgen.c)
target_link_libraries (micgen  thamesaux ${EXTRA_LIBS})

# Increase stack size on Windows (default 1MB is too small for large stack arrays)
if(WIN32)
    target_link_options(micgen PRIVATE "-Wl,--stack,8388608")  # 8 MB stack
endif()

#add_executable (elastic ${CMAKE_SOURCE_DIR}/src/elastic.c)
#target_link_libraries (elastic  thamesaux ${EXTRA_LIBS})

set (EXECS "micgen")
# set (EXECS ${EXECS} "elastic")

#install (TARGETS ${EXECS} DESTINATION ${CMAKE_SOURCE_DIR}/bin)
