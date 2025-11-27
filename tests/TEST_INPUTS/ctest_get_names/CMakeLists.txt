cmake_minimum_required(VERSION 3.15)
project(ctest_only NONE)

enable_testing()

add_test(NAME time COMMAND "/usr/bin/timedatectl")

add_test(NAME fail COMMAND "/usr/bin/false")

# timeout test
add_test(NAME timeout COMMAND "/usr/bin/timeout 10 ping 8.8.8.8")