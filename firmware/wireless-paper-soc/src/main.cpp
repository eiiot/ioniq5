#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <NimBLEDevice.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
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
constexpr uint32_t kPollIntervalMs = 5 * 60 * 1000;
constexpr uint32_t kRetryIntervalMs = 30 * 1000;

// ISRG Root X1. The hosted Tuft endpoint currently chains to Let's Encrypt.
constexpr char kRootCertificate[] = R"PEM(
-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI
rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL
ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ
3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK
NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5
ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur
TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC
jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc
oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq
4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d
emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----
)PEM";

struct NetworkConfig {
  String ssid;
  String password;
  String serverUrl;
  String apiKey;

  bool complete() const {
    return !ssid.isEmpty() && !serverUrl.isEmpty() && !apiKey.isEmpty();
  }
};

NimBLECharacteristic *socCharacteristic = nullptr;
std::string serialBuffer;
int currentSocPercent = -1;
NetworkConfig networkConfig;
uint32_t nextPollAtMs = 0;

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

NetworkConfig loadNetworkConfig() {
  Preferences preferences;
  preferences.begin("ioniq5-soc", true);
  NetworkConfig config{
      preferences.getString("ssid"),
      preferences.getString("password"),
      preferences.getString("server"),
      preferences.getString("api_key"),
  };
  preferences.end();
  return config;
}

void saveNetworkConfig(const NetworkConfig &config) {
  Preferences preferences;
  preferences.begin("ioniq5-soc", false);
  preferences.putString("ssid", config.ssid);
  preferences.putString("password", config.password);
  preferences.putString("server", config.serverUrl);
  preferences.putString("api_key", config.apiKey);
  preferences.end();
}

bool applyConfiguration(const std::string &message) {
  DynamicJsonDocument document(1024);
  if (deserializeJson(document, message) != DeserializationError::Ok ||
      document["command"] != "configure") {
    return false;
  }
  NetworkConfig candidate{
      document["ssid"].as<String>(),
      document["password"].as<String>(),
      document["server_url"].as<String>(),
      document["api_key"].as<String>(),
  };
  if (!candidate.complete()) {
    Serial.println(
        "{\"event\":\"configuration_failed\",\"error\":\"missing field\"}");
    return true;
  }
  saveNetworkConfig(candidate);
  Serial.println("{\"event\":\"configured\",\"restarting\":true}");
  Serial.flush();
  delay(100);
  ESP.restart();
  return true;
}

bool connectWifi() {
  if (!networkConfig.complete()) {
    return false;
  }
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }
  WiFi.mode(WIFI_STA);
  WiFi.begin(networkConfig.ssid.c_str(), networkConfig.password.c_str());
  const uint32_t deadline = millis() + 15000;
  while (WiFi.status() != WL_CONNECTED &&
         static_cast<int32_t>(deadline - millis()) > 0) {
    delay(250);
  }
  Serial.printf(
      "{\"event\":\"wifi\",\"connected\":%s,\"rssi_dbm\":%d}\n",
      WiFi.status() == WL_CONNECTED ? "true" : "false",
      WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0);
  return WiFi.status() == WL_CONNECTED;
}

bool fetchSoc() {
  if (!connectWifi()) {
    return false;
  }
  WiFiClientSecure client;
  client.setCACert(kRootCertificate);
  HTTPClient request;
  const String url = networkConfig.serverUrl + "/v1/status";
  if (!request.begin(client, url)) {
    return false;
  }
  request.addHeader("Accept", "application/json");
  request.addHeader("Authorization", "Bearer " + networkConfig.apiKey);
  const int status = request.GET();
  if (status != HTTP_CODE_OK) {
    Serial.printf("{\"event\":\"http_error\",\"status\":%d}\n", status);
    request.end();
    return false;
  }

  DynamicJsonDocument document(4096);
  const String responseBody = request.getString();
  const DeserializationError error =
      deserializeJson(document, responseBody);
  request.end();
  JsonVariant socValue = document["vehicle"]["soc_pct"];
  if (error != DeserializationError::Ok || socValue.isNull()) {
    Serial.printf(
        "{\"event\":\"soc_fetch_failed\",\"error\":\"%s\","
        "\"body_length\":%u}\n",
        error.c_str(), responseBody.length());
    return false;
  }
  const int socPercent = socValue.as<int>();
  if (socPercent < 0 || socPercent > 100) {
    Serial.println(
        "{\"event\":\"soc_fetch_failed\",\"error\":\"invalid SOC\"}");
    return false;
  }
  return applySocMessage(std::to_string(socPercent), "wifi");
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
        if (!applyConfiguration(serialBuffer)) {
          applySocMessage(serialBuffer, "usb");
        }
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
  networkConfig = loadNetworkConfig();
  Serial.printf(
      "{\"event\":\"ready\",\"device\":\"wireless-paper-soc\","
      "\"schema_version\":1,\"ble_name\":\"%s\"}\n",
      kDeviceName);
  nextPollAtMs = millis();
}

void loop() {
  processSerial();
  if (networkConfig.complete() &&
      static_cast<int32_t>(millis() - nextPollAtMs) >= 0) {
    const bool succeeded = fetchSoc();
    nextPollAtMs =
        millis() + (succeeded ? kPollIntervalMs : kRetryIntervalMs);
  }
  delay(10);
}
