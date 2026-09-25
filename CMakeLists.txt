cmake_minimum_required(VERSION 3.10)
project(fast_enhance CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(cpp/include)

add_library(fast_enhance SHARED cpp/src/fast_enhance.cpp)

set_target_properties(fast_enhance PROPERTIES
    PREFIX ""
    OUTPUT_NAME "fast_enhance"
)