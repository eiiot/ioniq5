#pragma once

#include <cctype>
#include <cstdlib>
#include <string>

namespace ioniq5 {

inline bool parseSocPercent(const std::string &message, int &socPercent) {
  const std::string key = "\"soc_pct\"";
  std::size_t start = message.find(key);
  if (start != std::string::npos) {
    start = message.find(':', start + key.size());
    if (start == std::string::npos) {
      return false;
    }
    ++start;
  } else {
    start = 0;
  }

  while (start < message.size() &&
         std::isspace(static_cast<unsigned char>(message[start]))) {
    ++start;
  }
  if (start == message.size()) {
    return false;
  }

  char *end = nullptr;
  const long value = std::strtol(message.c_str() + start, &end, 10);
  if (end == message.c_str() + start || value < 0 || value > 100) {
    return false;
  }

  while (*end != '\0' &&
         std::isspace(static_cast<unsigned char>(*end))) {
    ++end;
  }
  if (message.find(key) == std::string::npos && *end != '\0') {
    return false;
  }

  socPercent = static_cast<int>(value);
  return true;
}

}  // namespace ioniq5
