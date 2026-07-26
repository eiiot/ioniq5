#include "soc_protocol.h"

#include <cassert>

int main() {
  int value = -1;
  assert(ioniq5::parseSocPercent("23", value) && value == 23);
  assert(ioniq5::parseSocPercent(" 100\n", value) && value == 100);
  assert(ioniq5::parseSocPercent(R"({"soc_pct":0})", value) && value == 0);
  assert(ioniq5::parseSocPercent(
      R"({"type":"vehicle","soc_pct":67,"charging":true})", value));
  assert(value == 67);

  assert(!ioniq5::parseSocPercent("", value));
  assert(!ioniq5::parseSocPercent("101", value));
  assert(!ioniq5::parseSocPercent("-1", value));
  assert(!ioniq5::parseSocPercent("twenty", value));
  assert(!ioniq5::parseSocPercent(R"({"temperature_c":23})", value));
  return 0;
}
