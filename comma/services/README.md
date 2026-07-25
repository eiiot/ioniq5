# comma services

## Aranet bridge

`aranet_bridge.py` reads the ESP32-C3 from `/dev/ttyACM0`, reconnects after USB
resets, and atomically maintains the most recent valid reading at:

```text
/tmp/ioniq5/aranet-latest.json
```

Run it directly on the comma:

```sh
python3 comma/services/aranet_bridge.py
```

Override the device or output location when needed:

```sh
python3 comma/services/aranet_bridge.py \
  --device /dev/ttyACM0 \
  --latest-path /tmp/ioniq5/aranet-latest.json
```

This is currently a foreground development service. Process-manager integration
will be added after parked-awake behavior is measured.

## Control API

`control_api.py` serves an authenticated API on localhost for Cloudflare Tunnel.
Generate the API key once:

```sh
python3 comma/services/control_api.py --init-api-key
```

Copy the printed value into the app, then start the API:

```sh
python3 comma/services/control_api.py
```

The API binds only to `127.0.0.1:8787`. Every control/status endpoint requires
`Authorization: Bearer <key>`; `/health` is the only unauthenticated endpoint.
