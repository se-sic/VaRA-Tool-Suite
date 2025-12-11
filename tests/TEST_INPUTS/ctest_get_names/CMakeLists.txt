cmake_minimum_required(VERSION 3.15)
project(ctest_only NONE)

enable_testing()

add_test(NAME time COMMAND "/usr/bin/timedatectl")

add_test(NAME fail COMMAND "/usr/bin/false")

# timeout test
add_test(NAME timeout COMMAND "sleep" 5)
set_tests_properties(timeout PROPERTIES TIMEOUT 1)