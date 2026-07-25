# Wireless Paper SOC display

Shows the Ioniq 5 high-voltage battery state of charge on a Heltec Wireless
Paper. The displayed value can be updated either over USB serial or BLE.

## Flash and test over USB

```sh
PORT=/dev/cu.usbserial-0001 ./scripts/flash wireless-paper-soc
```

At the serial monitor, send either a percentage or an NDJSON vehicle message:

```text
67
{"soc_pct":67}
```

## BLE protocol

- Device name: `IONIQ5-SOC`
- Service: `42c7a100-7d8e-4c6c-9e3f-c99a9cc06a21`
- SOC characteristic: `42c7a101-7d8e-4c6c-9e3f-c99a9cc06a21`
- Properties: read, write, notify
- Payload: ASCII percentage (`0` through `100`) or JSON containing `soc_pct`

The default build targets Wireless Paper V1.1. Set `WIRELESS_PAPER_REV` to
`10`, `111`, or `12` for V1.0, V1.1.1, or V1.2 respectively.
