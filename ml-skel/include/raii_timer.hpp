#pragma once
#include <chrono>
#include <iostream>
#include <string_view>

class RaiiTimer {
public:
  explicit RaiiTimer(std::string_view name)
    : name_(name), start_(std::chrono::steady_clock::now()) {}

  // no copying, but allow moving if you like
  RaiiTimer(const RaiiTimer&) = delete;
  RaiiTimer& operator=(const RaiiTimer&) = delete;

  ~RaiiTimer() {
    using namespace std::chrono;
    const auto end = steady_clock::now();
    const auto ms = duration_cast<milliseconds>(end - start_).count();
    std::cout << "[TIMER] " << name_ << " took " << ms << " ms\n";
  }

private:
  std::string_view name_;
  std::chrono::steady_clock::time_point start_;
};
