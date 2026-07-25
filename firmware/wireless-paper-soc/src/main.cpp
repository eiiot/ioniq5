#include <Arduino.h>
#include <NimBLEDevice.h>
#include <heltec-eink-modules.h>

#include <string>

#include "Fonts/FreeSans12pt7b.h"
#include "Fonts/FreeSansBold24pt7b.h"
#include "soc_protocol.h"

#ifndef WIRELESS_PAPER_REV
#define WIRELESS_PAPER_REV 11
#endif

#if WIRELESS_PAPER_REV == 10
EInkDisplay_WirelessPaperV1 display;
#elif WIRELESS_PAPER_REV == 111
EInkDisplay_WirelessPaperV1_1_1 display;
#elif WIRELESS_PAPER_REV == 12
EInkDisplay_WirelessPaperV1_2 display;
#else
EInkDisplay_WirelessPaperV1_1 display;
#endif

namespace {

constexpr char kDeviceName[] = "IONIQ5-SOC";
constexpr char kServiceUuid[] = "42c7a100-7d8e-4c6c-9e3f-c99a9cc06a21";
constexpr char kSocCharacteristicUuid[] =
    "42c7a101-7d8e-4c6c-9e3f-c99a9cc06a21";

NimBLECharacteristic *socCharacteristic = nullptr;
std::string serialBuffer;
int currentSocPercent = -1;

void renderWaiting() {
  display.landscape();
  display.clearMemory();
  display.setFont(&FreeSans12pt7b);
  display.printCenter("Waiting for SOC");
  display.update();
}

void renderSoc(int socPercent) {
  display.landscape();
  display.clearMemory();

  display.setFont(&FreeSans12pt7b);
  display.printCenter("IONIQ 5", 0, -38);

  const String value = String(socPercent) + "%";
  display.setFont(&FreeSansBold24pt7b);
  display.printCenter(value, 0, 7);

  display.setFont(&FreeSans12pt7b);
  display.printCenter("BATTERY", 0, 45);
  display.update();
}

bool applySocMessage(const std::string &message, const char *source) {
  int parsed = -1;
  if (!ioniq5::parseSocPercent(message, parsed)) {
    Serial.printf(
        "{\"event\":\"invalid_soc\",\"source\":\"%s\",\"value\":\"%s\"}\n",
        source, message.c_str());
    return false;
  }

  if (parsed != currentSocPercent) {
    currentSocPercent = parsed;
    renderSoc(currentSocPercent);
  }

  if (socCharacteristic != nullptr) {
    const std::string encoded = std::to_string(currentSocPercent);
    socCharacteristic->setValue(encoded);
    socCharacteristic->notify();
  }
  Serial.printf(
      "{\"event\":\"soc_updated\",\"source\":\"%s\",\"soc_pct\":%d}\n",
      source, currentSocPercent);
  return true;
}

class SocCallbacks final : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic *characteristic) override {
    applySocMessage(characteristic->getValue(), "ble");
  }
};

void setupBle() {
  NimBLEDevice::init(kDeviceName);
  NimBLEServer *server = NimBLEDevice::createServer();
  NimBLEService *service = server->createService(kServiceUuid);
  socCharacteristic = service->createCharacteristic(
      kSocCharacteristicUuid,
      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE |
          NIMBLE_PROPERTY::NOTIFY);
  socCharacteristic->setCallbacks(new SocCallbacks());
  socCharacteristic->setValue("--");
  service->start();

  NimBLEAdvertising *advertising = NimBLEDevice::getAdvertising();
  advertising->addServiceUUID(kServiceUuid);
  advertising->setScanResponse(true);
  advertising->start();
}

void processSerial() {
  while (Serial.available() > 0) {
    const char character = static_cast<char>(Serial.read());
    if (character == '\r') {
      continue;
    }
    if (character == '\n') {
      if (!serialBuffer.empty()) {
        applySocMessage(serialBuffer, "usb");
        serialBuffer.clear();
      }
      continue;
    }
    if (serialBuffer.size() < 256) {
      serialBuffer.push_back(character);
    } else {
      serialBuffer.clear();
    }
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(800);

  renderWaiting();
  setupBle();
  Serial.printf(
      "{\"event\":\"ready\",\"device\":\"wireless-paper-soc\","
      "\"schema_version\":1,\"ble_name\":\"%s\"}\n",
      kDeviceName);
}

void loop() {
  processSerial();
  delay(10);
}
