# Smart Fleet & Logistics Management System

> **Final Year Project — CS619 | Virtual University of Pakistan**

| Field | Details |
|-------|---------|
| **Group ID** | S26PROJECTD2A66 |
| **Student ID** | BC220404864 |
| **Supervisor** | Muhammad Anwar (manwar@vu.edu.pk) |
| **Domain** | Mobile Application |
| **Semester** | Spring 2026 |

A professional Android mobile application that automates commercial logistics services including home shifting, freight transport, and last-mile delivery with real-time GPS tracking and staged payment lifecycle.

---

## Features

- **User Authentication** — Email/phone registration for Customers, Drivers, and Admins
- **Service Dashboard** — Vehicle categories from bikes to heavy-duty trucks
- **Automated Quoting** — Instant price quotes based on cargo dimensions, weight, and distance
- **Staged Payments** — 10% deposit → 50% at pickup → final settlement at delivery
- **Real-Time GPS Tracking** — Live shipment monitoring via Google Maps Platform
- **Admin Dashboard** — Fleet management, booking approval, driver assignment
- **Driver Portal** — Task management, status updates, location sharing
- **Automated Notifications** — FCM push notifications for all trip milestones
- **Auto-Cancellation** — 24-hour deposit deadline enforcement
- **Proof of Delivery** — Digital signature at destination

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Android Studio (Kotlin), MVVM Architecture |
| **Backend** | Firebase (Firestore, Auth, Cloud Functions, FCM) |
| **Maps** | OpenStreetMap (OSMDroid) — Free, no API key |
| **Payments** | JazzCash / EasyPaisa Integration |
| **Design** | Material Design 3 |

---

## Project Structure

```
Smart Fleet & Logistics Management System/
├── docs/
│   ├── HIGH_LEVEL_DESIGN.md          # Complete HLD document
│   └── SOFTWARE_REQUIREMENTS_SPECIFICATION.md
├── android/
│   └── app/src/main/java/com/smartfleet/logistics/
│       ├── data/
│       │   ├── model/Models.kt       # Data models & enums
│       │   └── repository/Repositories.kt
│       ├── ui/
│       │   └── viewmodel/ViewModels.kt
│       └── SmartFleetApp.kt
├── firebase/
│   ├── firestore.rules               # Security rules
│   ├── firestore.indexes.json        # Database indexes
│   ├── seed-data.json                # Sample vehicles & services
│   └── functions/src/index.ts        # Cloud Functions
└── README.md
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [High-Level Design](docs/HIGH_LEVEL_DESIGN.md) | Architecture, modules, database, diagrams |
| [SRS](docs/SOFTWARE_REQUIREMENTS_SPECIFICATION.md) | Functional & non-functional requirements |

---

## Setup Instructions

### Prerequisites
- Android Studio Hedgehog (2023.1.1) or later
- JDK 17
- Firebase project created at [console.firebase.google.com](https://console.firebase.google.com)
- Google Maps API key with Maps SDK and Directions API enabled

### 1. Firebase Setup
```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login and initialize
firebase login
cd firebase
firebase init

# Deploy rules and functions
firebase deploy --only firestore:rules,firestore:indexes,functions
```

### 2. Android Setup
1. Open `android/` folder in Android Studio
2. `google-services.json` is already placed in `android/app/` (Firebase project: **sawarri-d3e33**, package: **com.sawarri**)
3. Copy `local.properties.example` to `local.properties` (only SDK path needed — **no Maps API key**)
4. Sync Gradle and run on emulator or device

### 3. Seed Data
Import `firebase/seed-data.json` into Firestore collections `vehicles` and `services`.

---

## Payment Lifecycle

```
Total Quote: PKR 50,000

Phase 0 (Deposit):    10% = PKR 5,000    → On admin approval
Phase 1 (Pickup):     50% = PKR 22,500   → Driver arrives at pickup
Phase 2 (Final):      40% = PKR 22,500   → POD signed at destination
```

---

## Trip Status Flow

```
REQUESTED → PENDING_APPROVAL → APPROVED → DEPOSIT_PAID → ASSIGNED
    → EN_ROUTE → AT_PICKUP → IN_TRANSIT → AT_DESTINATION
    → DELIVERED → CLOSED
```

---

## Development Methodology

**VU Process Model** — Waterfall + Spiral hybrid:
- Waterfall for requirements analysis and system design
- Spiral iterations for GPS tracking and payment gateway features

---

## License

This project is developed as a Final Year Project for Virtual University of Pakistan (CS619).

---

**Supervisor:** Muhammad Anwar | manwar@vu.edu.pk | MS Teams: anwarvu@outlook.com
