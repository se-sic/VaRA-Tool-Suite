#include <chrono>
#include <thread>

#include <gtest/gtest.h>

TEST(BasicCases, Successful) {
    SUCCEED();
}

TEST(BasicCases, Failing) {
    EXPECT_EQ(1, 2);
}

TEST(BasicCases, Timeout) {
    std::this_thread::sleep_for(std::chrono::seconds(2));
    SUCCEED();
}
