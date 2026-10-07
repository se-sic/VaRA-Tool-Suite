cmake_minimum_required(VERSION 3.15)

project(gtest_test_project LANGUAGES CXX)

enable_testing()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(GTest REQUIRED)

add_executable(gtest_test_project test_project.cpp)
target_link_libraries(gtest_test_project PRIVATE GTest::gtest_main)

gtest_add_tests(TARGET gtest_test_project
TEST_LIST gtestTests)
set_tests_properties(${gtestTests} PROPERTIES TIMEOUT 1)