# ESP32-C3 Aranet USB bridge

Scans nearby Aranet devices without pairing and writes newline-delimited JSON
over the ESP32-C3 native USB CDC serial connection at 115200 baud.

Example:

```json
{"type":"aranet4","address":"aa:bb:cc:dd:ee:ff","rssi_dbm":-54,"co2_ppm":742,"temperature_c":23.15,"humidity_pct":41.0,"pressure_hpa":1012.3,"battery_pct":96,"measurement_age_s":4,"measurement_interval_s":60,"counter":17}
```

The Aranet mobile app must have **Smart Home integrations** enabled for
measurement data to appear in BLE advertisements. The bridge never connects,
pairs, or asks for the Aranet PIN.

## Commands

From the repository root:

```sh
./scripts/flash c3-aranet-bridge
./scripts/flash c3-aranet-bridge --no-monitor
```

To monitor an already-flashed board:

```sh
.venv/bin/pio device monitor --port /dev/cu.usbmodem2101 --baud 115200
```

