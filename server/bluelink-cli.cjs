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
}, 75_000);

client.once("error", (error) => {
  clearTimeout(timeout);
  console.error(error?.message || String(error));
  process.exit(1);
});

client.once("ready", async (vehicles) => {
  try {
    if (vehicles.length !== 1) {
      throw new Error(`Expected one vehicle, found ${vehicles.length}`);
    }
    const vehicle = vehicles[0];
    let result;
    if (action === "start") {
      result = await vehicle.start({
        hvac: true,
        temperature: 72,
        unit: "F",
        duration: 10,
        defrost: false,
        heatedFeatures: 0,
      });
    } else if (action === "stop") {
      result = await vehicle.stop();
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
