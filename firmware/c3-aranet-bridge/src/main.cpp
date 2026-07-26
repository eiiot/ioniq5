#include <Arduino.h>
#include <Adafruit_SHT4x.h>
#include <NimBLEDevice.h>
#include <Wire.h>

#include <cstring>
#include <string>

namespace {

constexpr uint16_t kAranetManufacturerId = 0x0702;
constexpr uint32_t kScanDurationSeconds = 5;
constexpr uint32_t kPauseBetweenScansMs = 5000;
constexpr uint8_t kIntegrationsFlag = 1U << 5;
constexpr uint8_t kSdaPin = 4;
constexpr uint8_t kSclPin = 5;
constexpr uint32_t kSht41IntervalMs = 2000;

struct Aranet4Reading {
  bool integrationsEnabled = false;
  uint16_t co2Ppm = 0;
  uint16_t temperatureRaw = 0;
  uint16_t pressureRaw = 0;
  uint8_t humidityPct = 0;
  uint8_t batteryPct = 0;
  uint16_t intervalSeconds = 0;
  uint16_t ageSeconds = 0;
  uint8_t counter = 0;
};

NimBLEScan *scanner = nullptr;
Adafruit_SHT4x sht41;
bool sht41Available = false;
uint32_t sht41Counter = 0;

uint16_t readLittleEndianU16(const uint8_t *bytes) {
  return static_cast<uint16_t>(bytes[0]) |
         (static_cast<uint16_t>(bytes[1]) << 8);
}

bool decodeAranet4(NimBLEAdvertisedDevice &advertisement,
                   Aranet4Reading &reading) {
  const std::string raw = advertisement.getManufacturerData();
  if (raw.size() < 2) {
    return false;
  }

  const auto *bytes = reinterpret_cast<const uint8_t *>(raw.data());
  if (readLittleEndianU16(bytes) != kAranetManufacturerId) {
    return false;
  }

  // The bytes after the two-byte manufacturer ID use one of two Aranet
  // layouts. Current packets include a leading device-type byte; legacy
  // Aranet4 packets do not.
  const uint8_t *payload = bytes + 2;
  const size_t payloadSize = raw.size() - 2;
  size_t layoutOffset = 1;
  if (raw.size() == 9 || raw.size() == 24) {
    layoutOffset = 0;
  } else if (payloadSize == 0 || payload[0] != 0) {
    // Device type 0 is Aranet4. Ignore Aranet2/Radon/Radiation for now.
    return false;
  }

  if (payloadSize <= layoutOffset) {
    return false;
  }
  reading.integrationsEnabled =
      (payload[layoutOffset] & kIntegrationsFlag) != 0;
  if (!reading.integrationsEnabled) {
    return true;
  }

  // The final counter byte is payload[layoutOffset + 21].
  if (payloadSize < layoutOffset + 22) {
    return false;
  }

  reading.co2Ppm = readLittleEndianU16(payload + layoutOffset + 8);
  reading.temperatureRaw =
      readLittleEndianU16(payload + layoutOffset + 10);
  reading.pressureRaw = readLittleEndianU16(payload + layoutOffset + 12);
  reading.humidityPct = payload[layoutOffset + 14];
  reading.batteryPct = payload[layoutOffset + 15];
  reading.intervalSeconds =
      readLittleEndianU16(payload + layoutOffset + 17);
  reading.ageSeconds = readLittleEndianU16(payload + layoutOffset + 19);
  reading.counter = payload[layoutOffset + 21];
  return true;
}

void printReading(NimBLEAdvertisedDevice &advertisement,
                  const Aranet4Reading &reading) {
  Serial.printf(
      "{\"type\":\"aranet4\",\"address\":\"%s\",\"rssi_dbm\":%d,"
      "\"co2_ppm\":%u,\"temperature_c\":%.2f,\"humidity_pct\":%u,"
      "\"pressure_hpa\":%.1f,\"battery_pct\":%u,"
      "\"measurement_age_s\":%u,\"measurement_interval_s\":%u,"
      "\"counter\":%u}\n",
      advertisement.getAddress().toString().c_str(),
      advertisement.getRSSI(),
      reading.co2Ppm,
      reading.temperatureRaw / 20.0,
      reading.humidityPct,
      reading.pressureRaw / 10.0,
      reading.batteryPct,
      reading.ageSeconds,
      reading.intervalSeconds,
      reading.counter);
}

void printSht41Reading() {
  sensors_event_t humidity{};
  sensors_event_t temperature{};
  if (!sht41.getEvent(&humidity, &temperature)) {
    Serial.printf(
        "{\"event\":\"sht41_read_error\",\"counter\":%lu}\n",
        static_cast<unsigned long>(sht41Counter++));
    return;
  }
  Serial.printf(
      "{\"type\":\"sht41\",\"temperature_c\":%.2f,"
      "\"humidity_pct\":%.2f,\"counter\":%lu}\n",
      temperature.temperature, humidity.relative_humidity,
      static_cast<unsigned long>(sht41Counter++));
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(1000);

  Wire.begin(kSdaPin, kSclPin);
  sht41Available = sht41.begin(&Wire);
  if (sht41Available) {
    sht41.setPrecision(SHT4X_HIGH_PRECISION);
    sht41.setHeater(SHT4X_NO_HEATER);
  } else {
    NimBLEDevice::init("");
    scanner = NimBLEDevice::getScan();
    scanner->setActiveScan(true);
  }

  Serial.printf(
      "{\"event\":\"ready\",\"device\":\"c3-cabin-bridge\","
      "\"schema_version\":2,\"sht41\":%s,"
      "\"fallback\":\"aranet4\"}\n",
      sht41Available ? "true" : "false");
}

void loop() {
  if (sht41Available) {
    printSht41Reading();
    delay(kSht41IntervalMs);
    return;
  }

  scanner->start(kScanDurationSeconds, false);
  NimBLEScanResults results = scanner->getResults();

  bool foundAranet4 = false;
  for (int index = 0; index < results.getCount(); ++index) {
    NimBLEAdvertisedDevice advertisement = results.getDevice(index);
    Aranet4Reading reading;
    if (!decodeAranet4(advertisement, reading)) {
      continue;
    }

    foundAranet4 = true;
    if (!reading.integrationsEnabled) {
      Serial.printf(
          "{\"event\":\"integrations_disabled\",\"address\":\"%s\","
          "\"rssi_dbm\":%d}\n",
          advertisement.getAddress().toString().c_str(),
          advertisement.getRSSI());
      continue;
    }

    printReading(advertisement, reading);
  }

  if (!foundAranet4) {
    Serial.println("{\"event\":\"scan_complete\",\"aranet_devices\":0}");
  }

  scanner->clearResults();
  delay(kPauseBetweenScansMs);
}
