#include <Arduino.h>
#include <Aranet4.h>

namespace {

constexpr uint32_t kScanDurationSeconds = 5;
constexpr uint32_t kPauseBetweenScansMs = 5000;

NimBLEScan *scanner = nullptr;

const char *typeName(AranetType type) {
  switch (type) {
    case ARANET4:
      return "aranet4";
    case ARANET2:
      return "aranet2";
    case ARANET_RADIATION:
      return "aranet-radiation";
    case ARANET_RADON:
      return "aranet-radon";
    default:
      return "unknown";
  }
}

void printCommon(NimBLEAdvertisedDevice &advertisement,
                 AranetManufacturerData &manufacturer) {
  AranetData &data = manufacturer.data;
  Serial.printf(
      "{\"type\":\"%s\",\"address\":\"%s\",\"rssi_dbm\":%d",
      typeName(data.type),
      advertisement.getAddress().toString().c_str(),
      advertisement.getRSSI());

  switch (data.type) {
    case ARANET4:
      Serial.printf(
          ",\"co2_ppm\":%u,\"temperature_c\":%.2f,\"humidity_pct\":%.1f,"
          "\"pressure_hpa\":%.1f",
          data.co2,
          data.getTemperature(),
          data.getHumidity(),
          data.getPressure());
      break;
    case ARANET2:
      Serial.printf(
          ",\"temperature_c\":%.2f,\"humidity_pct\":%.1f",
          data.getTemperature(),
          data.getHumidity());
      break;
    case ARANET_RADON:
      Serial.printf(
          ",\"radon_bq_m3\":%u,\"temperature_c\":%.2f,"
          "\"humidity_pct\":%.1f,\"pressure_hpa\":%.1f",
          data.radon_concentration,
          data.getTemperature(),
          data.getHumidity(),
          data.getPressure());
      break;
    case ARANET_RADIATION:
      Serial.printf(
          ",\"radiation_rate_usv_h\":%.3f",
          data.radiation_rate / 1000.0);
      break;
    default:
      break;
  }

  Serial.printf(
      ",\"battery_pct\":%u,\"measurement_age_s\":%u,"
      "\"measurement_interval_s\":%u,\"counter\":%u}\n",
      data.battery,
      data.ago,
      data.interval,
      data.counter);
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(1000);

  Aranet4::init();
  scanner = NimBLEDevice::getScan();
  scanner->setActiveScan(true);

  Serial.println(
      "{\"event\":\"ready\",\"device\":\"c3-aranet-bridge\","
      "\"schema_version\":1}");
}

void loop() {
  scanner->start(kScanDurationSeconds, false);
  NimBLEScanResults results = scanner->getResults();

  bool foundAranet = false;
  for (int index = 0; index < results.getCount(); ++index) {
    NimBLEAdvertisedDevice advertisement = results.getDevice(index);
    AranetManufacturerData manufacturer;

    if (!manufacturer.fromAdvertisement(&advertisement)) {
      continue;
    }

    foundAranet = true;
    if (!manufacturer.flags.bits.integrations) {
      Serial.printf(
          "{\"event\":\"integrations_disabled\",\"address\":\"%s\","
          "\"rssi_dbm\":%d}\n",
          advertisement.getAddress().toString().c_str(),
          advertisement.getRSSI());
      continue;
    }

    printCommon(advertisement, manufacturer);
  }

  if (!foundAranet) {
    Serial.println("{\"event\":\"scan_complete\",\"aranet_devices\":0}");
  }

  scanner->clearResults();
  delay(kPauseBetweenScansMs);
}
