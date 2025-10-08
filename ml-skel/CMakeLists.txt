cmake_minimum_required(VERSION 3.22)
project (ml_skel LANGUAGES CXX)

#Use C++20, treat warnings seriously in Debug 
set (CMAKE_CXX_STANDARD 20)
set (CMAKE_CXX_STANDARD_REQUIRED ON)

if (CMAKE_BUILD_TYPE STREQUAL "Debug")
    if (MSVC)
        add_compile_options(/W4 /permissive-)
    else()
        add_compile_options(-Wall -Wextra -Wpedantic -Werror)
    endif()
endif()

#Optionally enable Address Sanitizer in Debug builds
if (CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    set(SANITIZERS "address,undefined")
    add_link_options("$<$<CONFIG:Debug>:-fsanitize=${SANITIZERS}>")
    add_compile_options ("$<$<CONFIG:Debug>:-fsanitize=${SANITIZERS}>")
endif()

add_executable (ml_skel
    src/main.cpp
)
target_include_directories (ml_skel PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)