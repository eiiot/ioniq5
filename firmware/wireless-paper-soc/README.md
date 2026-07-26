# Wireless Paper entryway remote

Shows the Ioniq 5 battery state of charge, cabin temperature, climate state,
cabin-protection state, and sensor connectivity on a Heltec Wireless Paper.

- Tap **PRG** to refresh immediately.
- Hold **PRG** for about one second to toggle cabin protection.

## Flash and test over USB

```sh
PORT=/dev/cu.usbserial-0001 ./scripts/flash wireless-paper-soc
```

At the serial monitor, send either a percentage or an NDJSON vehicle message:

```text
67
{"soc_pct":67}
```

## Standalone Wi-Fi mode

Provision credentials once over USB:

```json
{"command":"configure","ssid":"...","password":"...","server_url":"https://ioniq5-api.tuft.host","api_key":"..."}
```

The credentials are saved in the ESP32's local preferences and are not part of
the firmware image. The display polls `/v1/status` over authenticated HTTPS
every five minutes, retries temporary failures after 30 seconds, and retains
the last display when offline.

## BLE protocol

- Device name: `IONIQ5-SOC`
- Service: `42c7a100-7d8e-4c6c-9e3f-c99a9cc06a21`
- SOC characteristic: `42c7a101-7d8e-4c6c-9e3f-c99a9cc06a21`
- Properties: read, write, notify
- Payload: ASCII percentage (`0` through `100`) or JSON containing `soc_pct`

The default build targets Wireless Paper V1.1. Set `WIRELESS_PAPER_REV` to
`10`, `111`, or `12` for V1.0, V1.1.1, or V1.2 respectively.
