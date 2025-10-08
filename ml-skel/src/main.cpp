#include "raii_timer.hpp"
#include <vector>
#include <numeric>
#include <iostream>

int main() {
  // The timer prints automatically when it leaves scope. That’s RAII.
  {
    RaiiTimer t("warmup");
    volatile int sink = 0;
    for (int i = 0; i < 1'000'000; ++i) sink += i;
  }

  {
    RaiiTimer t("sum 1..N");
    const int N = 10'000'000;
    std::vector<int> v(N);
    std::iota(v.begin(), v.end(), 1);
    long long sum = 0;
    for (int x : v) sum += x;
    std::cout << "sum = " << sum << "\n";
  }

  return 0;
}
