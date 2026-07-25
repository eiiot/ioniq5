# IONIQ 5 mobile app

A native controller for the comma-hosted IONIQ 5 API.

## Run

```sh
npm install
npx expo start
```

Open the project in Expo Go. Liquid Glass renders natively on iOS 26+ and
falls back to system material blur elsewhere.

The API base URL is `https://ioniq5.eliot.sh`. Enter the API key in the
Connection sheet. The app stores it with `expo-secure-store`; it is never
committed or embedded in the JavaScript bundle.

## Verify

```sh
npm run lint
npx tsc --noEmit
npx expo export --platform web
```

