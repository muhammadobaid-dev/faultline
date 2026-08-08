# Firebase Setup — Sawarri (sawarri-d3e33)

## Connected Configuration

| Setting | Value |
|---------|-------|
| **Firebase Project** | Sawarri |
| **Project ID** | `sawarri-d3e33` |
| **Project Number** | `587951406869` |
| **Android Package** | `com.sawarri` |
| **Storage Bucket** | `sawarri-d3e33.firebasestorage.app` |
| **Billing Plan** | Spark (Free) |

## Files Integrated

- `android/app/google-services.json` — Firebase Android config
- `android/app/build.gradle.kts` — Google Services plugin enabled
- `.firebaserc` — CLI linked to `sawarri-d3e33`
- `firebase.json` — Firestore, Functions, Storage rules

## Firebase Console — Enable These Services

Go to [Firebase Console](https://console.firebase.google.com/project/sawarri-d3e33) and enable:

1. **Authentication** → Email/Password + Phone
2. **Firestore Database** → Create database (production mode, then deploy rules)
3. **Storage** → Enable bucket
4. **Cloud Messaging** → For push notifications

## Deploy Backend Rules

```bash
cd "Smart Fleet & Logistics Management System"
firebase login
firebase deploy --only firestore:rules,firestore:indexes,storage
```

## Deploy Cloud Functions (optional)

```bash
cd firebase/functions
npm install
cd ../..
firebase deploy --only functions
```

## Seed Sample Data

Import `firebase/seed-data.json` vehicles and services into Firestore collections manually, or use Firebase Console.

## Maps — Free OpenStreetMap

Live GPS tracking uses **OSMDroid + OpenStreetMap**:
- Completely **FREE**
- **No API key** required
- **No billing** account needed
- Works with internet connection only

No setup required — maps work out of the box after Gradle sync.

## Verify Connection

1. Open `android/` in Android Studio
2. Sync Gradle — no `google-services.json` errors should appear
3. Run app — Splash screen loads, Firebase Auth initializes
