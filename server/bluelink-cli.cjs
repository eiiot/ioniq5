#!/usr/bin/env node

const { BlueLinky } = require("bluelinky");

const action = process.argv[2];
if (!["status", "start", "stop"].includes(action)) {
  console.error("Usage: bluelink-cli.cjs status|start|stop");
  process.exit(2);
}

for (const name of ["BL_USER", "BL_PASS", "BL_REGION"]) {
  if (!process.env[name]) {
    console.error(`Missing ${name}`);
    process.exit(2);
  }
}

const client = new BlueLinky({
  username: process.env.BL_USER,
  password: process.env.BL_PASS,
  region: process.env.BL_REGION,
  brand: "hyundai",
  autoLogin: false,
  pin: process.env.BL_PIN || "0000",
});

const timeout = setTimeout(() => {
  console.error("Bluelink command timed out");
  process.exit(2);
}, 140_000);

client.once("error", (error) => {
  clearTimeout(timeout);
  console.error(error?.message || String(error));
  process.exit(1);
});

function payloadTimestamp() {
  const now = new Date();
  const part = (value) => String(value).padStart(2, "0");
  return [
    now.getUTCFullYear(),
    part(now.getUTCMonth() + 1),
    part(now.getUTCDate()),
    part(now.getUTCHours()),
    part(now.getUTCMinutes()),
    part(now.getUTCSeconds()),
  ].join("");
}

async function sendHyundaiUsEvClimate(vehicle, command) {
  const controller = vehicle.controller;
  await controller.refreshAccessToken();
  const config = vehicle.vehicleConfig;
  const environment = controller.environment;
  const vin = vehicle.vin();
  const headers = {
    client_id: environment.clientId,
    clientSecret: environment.clientSecret,
    Host: environment.host,
    "User-Agent": "okhttp/3.12.0",
    "Content-Type": "application/json",
    Accept: "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    Connection: "Keep-Alive",
    accessToken: controller.session.accessToken,
    language: "0",
    to: "ISS",
    encryptFlag: "false",
    from: "SPA",
    offset: "-5",
    brandIndicator: config.brandIndicator || "H",
    origin: `https://${environment.host}`,
    referer: `https://${environment.host}/login`,
    username: process.env.BL_USER,
    blueLinkServicePin: process.env.BL_PIN,
    refresh: "false",
    gen: String(config.generation),
    registrationId: config.regId,
    vin,
    "APPCLOUD-VIN": vin,
    payloadGenerated: payloadTimestamp(),
    includeNonConnectedVehicles: "Y",
  };
  const path =
    command === "start"
      ? "/ac/v2/evc/fatc/start"
      : "/ac/v2/evc/fatc/stop";
  const body =
    command === "start"
      ? {
          airCtrl: 1,
          airTemp: { value: "72", unit: 1 },
          defrost: false,
          heating1: 0,
        }
      : {};
  const response = await fetch(`${environment.baseUrl}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const responseBody = await response.text();
  if (!response.ok) {
    throw new Error(
      `Hyundai API ${response.status}: ${responseBody || response.statusText}`,
    );
  }
  const transactionId =
    response.headers.get("tmsTid") ||
    response.headers.get("transactionId") ||
    response.headers.get("Xid");
  if (!transactionId) {
    throw new Error("Hyundai accepted the request without a transaction ID");
  }

  const statusHeaders = {
    ...headers,
    tid: transactionId,
    login_id: process.env.BL_USER,
    service_type: "REMOTE_POLL",
  };
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const statusResponse = await fetch(
      `${environment.baseUrl}/ac/v2/rmt/getRunningStatus`,
      { method: "GET", headers: statusHeaders },
    );
    const statusBody = await statusResponse.text();
    if (!statusResponse.ok) {
      throw new Error(
        `Hyundai command status ${statusResponse.status}: ${
          statusBody || statusResponse.statusText
        }`,
      );
    }
    let commandStatus;
    try {
      commandStatus = JSON.parse(statusBody).status;
    } catch {
      commandStatus = null;
    }
    if (commandStatus === "SUCCESS") {
      return {
        status: response.status,
        transactionId,
        commandStatus,
      };
    }
    if (commandStatus === "ERROR") {
      throw new Error("Hyundai reported command failure");
    }
    await new Promise((resolve) => setTimeout(resolve, 2_000));
  }
  throw new Error("Hyundai command confirmation timed out");
}

client.once("ready", async (vehicles) => {
  try {
    if (vehicles.length !== 1) {
      throw new Error(`Expected one vehicle, found ${vehicles.length}`);
    }
    const vehicle = vehicles[0];
    let result;
    if (action === "start") {
      result = await sendHyundaiUsEvClimate(vehicle, "start");
    } else if (action === "stop") {
      result = await sendHyundaiUsEvClimate(vehicle, "stop");
    } else {
      const status = await vehicle.status({ refresh: false, parsed: true });
      result = {
        climateActive: status?.climate?.active ?? null,
        batteryChargeHV: status?.engine?.batteryChargeHV ?? null,
        lastUpdate: status?.lastupdate ?? null,
      };
    }
    if (typeof result === "string" && /^failed\b/i.test(result)) {
      throw new Error(result);
    }
    clearTimeout(timeout);
    console.log(JSON.stringify({ ok: true, action, result }));
    process.exit(0);
  } catch (error) {
    clearTimeout(timeout);
    console.error(error?.message || String(error));
    process.exit(1);
  }
});

client.login();
