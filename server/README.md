# Hosted relay

The relay lets both the app and comma make outbound HTTPS requests instead of
opening an inbound tunnel to the car.

Endpoints:

- `GET /health`
- `GET /v1/status`
- `GET /v1/history` (minute-level cabin temperature for the last 24 hours)
- `GET /v1/config`
- `PATCH /v1/config`
- `POST /v1/telemetry`

All `/v1/*` endpoints require the same bearer key. Run the server with private
paths for the key and persisted state:

```sh
python3 server/relay_api.py \
  --api-key-path /private/api.key \
  --state-path /private/state.json
```

The server polls Bluelink's cached vehicle status every five minutes and
includes the latest high-voltage battery SOC in `GET /v1/status` under
`vehicle.soc_pct`. This feed is used by the Wireless Paper display.
