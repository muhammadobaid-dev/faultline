# Prototype Phase — Supervisor Checklist (CS619)

**Project:** Smart Fleet & Logistics Management System (Sawarri)  
**Group:** S26PROJECTD2A66 | **Student:** BC220404864  
**Deadline:** Wed 26 Aug, 2026

## Supervisor Requirements → App Mapping

| # | Requirement | Status | Where in App |
|---|-------------|--------|--------------|
| 1 | Registration page with important fields | Done | `RegisterActivity` |
| 2 | Register with User ID (auto), name, username, email, address, mobile | Done | Form + Firebase Auth + Firestore |
| 3 | Save all registration data in database | Done | Firestore `users` + `usernames` |
| 4 | Login page | Done | `LoginActivity` |
| 5 | Login with username and password | Done | Username **or** email + password |
| 6 | After login, edit registration information | Done | Settings → Edit Registration Info |

## Firebase Setup (must do once)

1. Open [Firebase Console — sawarri-d3e33 Authentication](https://console.firebase.google.com/project/sawarri-d3e33/authentication/users)
2. **Authentication → Sign-in method → Email/Password → Enable**
3. **Firestore Database** → create if missing (production mode), then deploy rules:

```bash
cd "Smart Fleet & Logistics Management System"
npx firebase-tools login
npx firebase-tools deploy --only firestore:rules
```

Or paste `firebase/firestore.rules` manually in Firebase Console → Firestore → Rules → Publish.

4. Confirm `android/app/google-services.json` matches package `com.sawarri`

## Demo Flow for Supervisor / Evaluator

1. Open **Sawarri** app on emulator
2. Tap **Register** → fill Name, Username, Email, Mobile (`03XXXXXXXXX`), Address, Password, Role
3. Submit → toast shows system **User ID** (`SWR-XXXXXXXX`)
4. Check Firebase Authentication users + Firestore `users` collection
5. Logout → Login with **username** + password
6. Open **Settings** (toolbar) → edit name/username/mobile/address → **Save Changes**
7. Confirm Firestore document updated

## Note

Email cannot be changed after registration (Firebase Auth constraint). User ID is system-generated and read-only.
