# Ioniq 5 tooling

Firmware, comma services, CAN research, and project notes for a 2022 Hyundai
Ioniq 5.

## Projects

- [`firmware/c3-aranet-bridge`](firmware/c3-aranet-bridge): streams Aranet4
  readings over the ESP32-C3 native USB serial connection.
- [`apps/mobile`](apps/mobile): Expo app for cabin status and automation
  controls.
- [`comma/services`](comma/services): USB telemetry reader and authenticated
  localhost control API.

## Quick start

Connect an ESP32-C3 over USB-C, then run:

```sh
./scripts/flash c3-aranet-bridge
```

The script creates a local Python virtual environment, installs PlatformIO,
builds and flashes the firmware, and opens a serial monitor. Set `PORT` to
override automatic `/dev/cu.usbmodem*` detection:

```sh
PORT=/dev/cu.usbmodem2101 ./scripts/flash c3-aranet-bridge
```
