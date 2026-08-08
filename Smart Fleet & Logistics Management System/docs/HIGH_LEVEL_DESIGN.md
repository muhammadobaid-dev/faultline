# Smart Fleet & Logistics Management System
## High-Level Design (HLD) Document

| **Field** | **Details** |
|-----------|-------------|
| **Project Title** | Smart Fleet & Logistics Management System |
| **Group ID** | S26PROJECTD2A66 |
| **Student ID** | BC220404864 |
| **Supervisor** | Muhammad Anwar (manwar@vu.edu.pk) |
| **Course** | CS619 – Final Year Project |
| **Version** | 1.0 |
| **Date** | July 10, 2026 |
| **Document Type** | High-Level Design (HLD) |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Architecture Design](#3-architecture-design)
4. [Technology Stack](#4-technology-stack)
5. [Module Design](#5-module-design)
6. [Database Design](#6-database-design)
7. [Use Case Design](#7-use-case-design)
8. [Sequence Diagrams](#8-sequence-diagrams)
9. [Class Diagram](#9-class-diagram)
10. [UI/UX Design](#10-uiux-design)
11. [Payment System Design](#11-payment-system-design)
12. [GPS Tracking Design](#12-gps-tracking-design)
13. [Security Design](#13-security-design)
14. [Notification System](#14-notification-system)
15. [Non-Functional Requirements](#15-non-functional-requirements)
16. [Deployment Architecture](#16-deployment-architecture)
17. [Risk Analysis & Mitigation](#17-risk-analysis--mitigation)
18. [Development Methodology](#18-development-methodology)

---

## 1. Introduction

### 1.1 Purpose
This High-Level Design document describes the architecture, modules, data models, and interaction flows for the **Smart Fleet & Logistics Management System** — a mobile application that automates commercial logistics including home shifting, freight transport, and last-mile delivery.

### 1.2 Scope
The system enables customers to book transport vehicles (bikes to heavy-duty trucks), select value-added services, manage staged payments, and track shipments in real time. Administrators manage fleet operations, assign drivers, and oversee trip lifecycles.

### 1.3 Target Users
| Role | Description |
|------|-------------|
| **Customer** | Books logistics services, makes payments, tracks shipments |
| **Driver** | Receives assigned routes, updates trip status, shares GPS location |
| **Loader** | Assists with loading/unloading (Loader 1, Loader 2) |
| **Admin** | Reviews bookings, assigns fleet, manages payments, closes trips |

### 1.4 Definitions & Acronyms
| Term | Definition |
|------|------------|
| POD | Proof of Delivery — digital signature at destination |
| SRS | Software Requirements Specification |
| HLD | High-Level Design |
| FCM | Firebase Cloud Messaging |
| GPS | Global Positioning System |

---

## 2. System Overview

### 2.1 Problem Statement
Traditional logistics booking relies on phone calls, manual quoting, and cash-based payments with no real-time visibility. This leads to inefficiency, pricing disputes, and poor customer experience.

### 2.2 Proposed Solution
A unified Android mobile application backed by Firebase that provides:
- Instant automated price quotes based on cargo dimensions and weight
- Three-stage payment lifecycle (10% deposit → 50% at pickup → final at delivery)
- Real-time GPS tracking via Google Maps Platform
- Admin-controlled fleet assignment and trip management
- Automated notifications and cancellation policies

### 2.3 System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SYSTEMS                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ Google Maps  │  │   Payment    │  │   Firebase   │  │   SMS/OTP   │ │
│  │   Platform   │  │   Gateway    │  │   Services   │  │  Provider   │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘ │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              SMART FLEET & LOGISTICS MANAGEMENT SYSTEM                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐ │
│  │  Customer   │  │   Driver    │  │   Admin     │  │   Backend     │ │
│  │    App      │  │    App      │  │  Dashboard  │  │  (Firebase)   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐
    │ Customer │      │  Driver  │      │  Admin   │
    │  (User)  │      │  (User)  │      │  (User)  │
    └──────────┘      └──────────┘      └──────────┘
```

---

## 3. Architecture Design

### 3.1 Architectural Style
**Client-Server Architecture** with **Backend-as-a-Service (BaaS)** using Firebase.

```
┌──────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Android Mobile Application                     │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │  Auth    │ │ Booking  │ │ Tracking │ │   Payment    │  │  │
│  │  │  Module  │ │  Module  │ │  Module  │ │   Module     │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │  Admin   │ │  Driver  │ │  Maps    │ │ Notification │  │  │
│  │  │ Dashboard│ │  Portal  │ │  Module  │ │   Module     │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTPS / WebSocket
┌──────────────────────────────▼───────────────────────────────────┐
│                      APPLICATION LAYER (Firebase)                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │ Firebase    │ │  Cloud      │ │  Cloud      │ │  Firebase   │ │
│  │ Auth        │ │  Firestore  │ │  Functions  │ │  Storage    │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
│  ┌─────────────┐ ┌─────────────┐                                 │
│  │  Firebase   │ │  Firebase   │                                 │
│  │  FCM        │ │  Analytics  │                                 │
│  └─────────────┘ └─────────────┘                                 │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                      EXTERNAL SERVICES LAYER                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │ Google Maps     │  │ Payment Gateway │  │ SMS/OTP         │   │
│  │ Platform API    │  │ (JazzCash/EasyPaisa/Stripe)           │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Layer Responsibilities

| Layer | Responsibility |
|-------|----------------|
| **Presentation** | UI rendering, user input validation, local caching, role-based views |
| **Application** | Business logic via Cloud Functions, real-time sync, auth enforcement |
| **Data** | Firestore collections, file storage for POD images, audit logs |
| **External** | Maps routing, payment processing, SMS verification |

---

## 4. Technology Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Mobile Frontend** | Android Studio (Kotlin) | Native performance, Google Maps SDK integration |
| **Authentication** | Firebase Authentication | Email/phone OTP, secure token management |
| **Database** | Cloud Firestore | Real-time sync for GPS tracking and booking status |
| **Server Logic** | Firebase Cloud Functions | Payment webhooks, auto-cancellation cron jobs |
| **File Storage** | Firebase Storage | POD signatures, cargo photos |
| **Push Notifications** | Firebase Cloud Messaging (FCM) | Real-time trip updates |
| **Maps & GPS** | Google Maps Platform | Route calculation, live tracking |
| **Payment** | JazzCash / EasyPaisa API | Local payment gateway integration |
| **Architecture Pattern** | MVVM (Model-View-ViewModel) | Separation of concerns, testability |

---

## 5. Module Design

### 5.1 Module Overview

```
Smart Fleet App
├── M1: Authentication Module
├── M2: Service Dashboard Module
├── M3: Search & Booking Module
├── M4: Quoting Engine Module
├── M5: Payment Module
├── M6: GPS Tracking Module
├── M7: Admin Management Module
├── M8: Driver Portal Module
├── M9: Notification Module
└── M10: Trip Lifecycle Module
```

### 5.2 Module Specifications

#### M1: Authentication Module
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Register and authenticate Customers, Drivers, and Admins |
| **Inputs** | Email, phone number, password, OTP |
| **Outputs** | Auth token, user profile, role assignment |
| **Components** | LoginActivity, RegisterActivity, OTPVerificationActivity, AuthViewModel |
| **Firebase** | Firebase Auth (Email/Phone providers) |

#### M2: Service Dashboard Module
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Display vehicle categories and value-added services |
| **Inputs** | Cargo type selection |
| **Outputs** | Filtered vehicle list with capacity and pricing base rates |
| **Vehicle Categories** | Bike, Small Van, Medium Truck, Heavy Truck, Refrigerated Truck |

#### M3: Search & Booking Module
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Search fleets and create logistics requests |
| **Inputs** | Pickup/drop-off locations, cargo details, urgency, add-on services |
| **Outputs** | Logistics Request ID, price quote |
| **Filters** | Location, load capacity, Standard vs Express |

#### M4: Quoting Engine Module
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Calculate automated price quotes |
| **Formula** | `Total = BaseRate + (Distance × PerKmRate) + WeightSurcharge + ServiceAddons` |
| **Inputs** | Dimensions (L×W×H), weight (kg), distance (km), services selected |
| **Outputs** | Itemized quote breakdown |

**Pricing Formula:**
```
BaseQuote = VehicleBaseRate
DistanceCost = GoogleMapsDistance(km) × PerKmRate
WeightCost = max(0, (weight - freeLimit)) × WeightRatePerKg
VolumeCost = (L × W × H) × VolumeRate
ServiceAddons = Σ(selectedService.price)
UrgencyMultiplier = Express ? 1.5 : 1.0

TotalQuote = (BaseQuote + DistanceCost + WeightCost + VolumeCost + ServiceAddons) × UrgencyMultiplier
```

#### M5: Payment Module
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Manage three-stage payment lifecycle |
| **Stages** | Phase 0: 10% Commitment Fee → Phase 1: 50% at Pickup → Phase 2: Final at Delivery |
| **Components** | PaymentActivity, PaymentViewModel, PaymentGatewayService |
| **Business Rules** | Auto-cancel if deposit not paid within 24h of admin approval |

#### M6: GPS Tracking Module
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Real-time shipment location monitoring |
| **Components** | TrackingActivity, LocationService, MapsFragment |
| **Update Frequency** | Every 10 seconds during active transit |
| **API** | Google Maps SDK + Directions API |

#### M7: Admin Management Module
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Review bookings, assign fleet, close trips |
| **Features** | Request approval, driver/vehicle assignment, route review, trip closure |
| **Components** | AdminDashboardActivity, AssignmentActivity, TripManagementActivity |

#### M8: Driver Portal Module
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Driver-specific interface for assigned tasks |
| **Features** | View assigned routes, cargo list, update trip status, share GPS |
| **Status Updates** | En Route → At Pickup → In Transit → At Destination → Delivered |

#### M9: Notification Module
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Automated push notifications |
| **Triggers** | Booking approval, payment reminders, driver arrival, delivery confirmation |
| **Technology** | Firebase Cloud Messaging (FCM) |

#### M10: Trip Lifecycle Module
| Attribute | Detail |
|-----------|--------|
| **Purpose** | Manage complete trip state machine |
| **States** | See Section 5.3 |
| **Rules** | Modification allowed up to 12h before pickup; cancellation fees apply |

### 5.3 Trip State Machine

```
                    ┌──────────────┐
                    │   REQUESTED  │
                    └──────┬───────┘
                           │ Admin Reviews
                    ┌──────▼───────┐
              ┌─────│   PENDING    │─────┐
              │     │   APPROVAL   │     │ Rejected
              │     └──────┬───────┘     ▼
              │            │        ┌──────────┐
              │            │        │ REJECTED │
              │            ▼        └──────────┘
              │     ┌──────────────┐
              │     │   APPROVED   │
              │     └──────┬───────┘
              │            │ Pay 10% Deposit
              │     ┌──────▼───────┐     24h timeout
              │     │   DEPOSIT    │─────────────┐
              │     │    PAID      │             │
              │     └──────┬───────┘             ▼
              │            │ Assign Fleet   ┌────────────┐
              │     ┌──────▼───────┐        │ AUTO-CANCEL│
              │     │   ASSIGNED   │        └────────────┘
              │     └──────┬───────┘
              │            │ Driver En Route
              │     ┌──────▼───────┐
              │     │  EN_ROUTE    │
              │     └──────┬───────┘
              │            │ Arrive at Pickup + Pay 50%
              │     ┌──────▼───────┐
              │     │ AT_PICKUP    │
              │     └──────┬───────┘
              │            │ Cargo Loaded
              │     ┌──────▼───────┐
              │     │ IN_TRANSIT   │◄── GPS Active
              │     └──────┬───────┘
              │            │ Arrive at Destination
              │     ┌──────▼───────┐
              │     │AT_DESTINATION│
              │     └──────┬───────┘
              │            │ POD Signed + Final Payment
              │     ┌──────▼───────┐
              │     │  DELIVERED   │
              │     └──────┬───────┘
              │            │ Admin Closes
              │     ┌──────▼───────┐
              └────►│   CLOSED     │
                    └──────────────┘
```

---

## 6. Database Design

### 6.1 Firestore Collection Structure

```
firestore/
├── users/
│   └── {userId}
│       ├── email: string
│       ├── phone: string
│       ├── name: string
│       ├── role: "customer" | "driver" | "loader" | "admin"
│       ├── profileImage: string (URL)
│       ├── createdAt: timestamp
│       └── isActive: boolean
│
├── vehicles/
│   └── {vehicleId}
│       ├── registrationNumber: string
│       ├── category: "bike" | "small_van" | "medium_truck" | "heavy_truck" | "refrigerated"
│       ├── capacityKg: number
│       ├── capacityVolume: number (cubic meters)
│       ├── baseRate: number
│       ├── perKmRate: number
│       ├── status: "available" | "assigned" | "in_transit" | "maintenance"
│       └── assignedDriverId: string (nullable)
│
├── services/
│   └── {serviceId}
│       ├── name: string (e.g., "Professional Packing", "Fragile Handling")
│       ├── description: string
│       ├── price: number
│       └── category: "packing" | "labor" | "insurance" | "handling"
│
├── bookings/
│   └── {bookingId}
│       ├── customerId: string
│       ├── status: TripStatus enum
│       ├── pickup: { address, lat, lng, scheduledAt }
│       ├── dropoff: { address, lat, lng }
│       ├── cargo: { type, length, width, height, weight, description }
│       ├── selectedServices: [serviceId]
│       ├── urgency: "standard" | "express"
│       ├── quote: { baseRate, distanceCost, weightCost, serviceCost, total }
│       ├── assignedVehicleId: string
│       ├── assignedDriverId: string
│       ├── assignedLoaders: [loaderId]
│       ├── payments: { deposit, pickup, final }
│       ├── createdAt: timestamp
│       ├── approvedAt: timestamp
│       ├── depositDeadline: timestamp (approvedAt + 24h)
│       └── modificationDeadline: timestamp (pickup - 12h)
│
├── payments/
│   └── {paymentId}
│       ├── bookingId: string
│       ├── userId: string
│       ├── phase: "deposit" | "pickup" | "final"
│       ├── amount: number
│       ├── status: "pending" | "completed" | "failed" | "refunded"
│       ├── gatewayRef: string
│       ├── paidAt: timestamp
│       └── createdAt: timestamp
│
├── tracking/
│   └── {bookingId}
│       ├── currentLocation: GeoPoint
│       ├── driverId: string
│       ├── lastUpdated: timestamp
│       ├── route: [GeoPoint] (breadcrumb trail)
│       └── speed: number
│
├── notifications/
│   └── {notificationId}
│       ├── userId: string
│       ├── title: string
│       ├── body: string
│       ├── type: NotificationType enum
│       ├── bookingId: string (nullable)
│       ├── isRead: boolean
│       └── createdAt: timestamp
│
└── proof_of_delivery/
    └── {podId}
        ├── bookingId: string
        ├── signatureImageUrl: string
        ├── recipientName: string
        ├── deliveredAt: timestamp
        ├── photos: [string] (URLs)
        └── notes: string
```

### 6.2 Entity Relationship Diagram

```
┌──────────┐       ┌───────────┐       ┌──────────┐
│  users   │──1:N──│ bookings  │──N:1──│ vehicles │
│          │       │           │       │          │
│ role     │       │ status    │       │ category │
│ email    │       │ quote     │       │ capacity │
└──────────┘       └─────┬─────┘       └──────────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────▼───┐ ┌────▼────┐ ┌───▼────┐
         │payments│ │tracking │ │  POD   │
         │        │ │         │ │        │
         │ phase  │ │location │ │signature│
         └────────┘ └─────────┘ └────────┘
```

### 6.3 Firestore Security Rules (Summary)

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read/write their own profile
    match /users/{userId} {
      allow read, write: if request.auth.uid == userId;
      allow read: if get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }
    
    // Bookings: customers see own, drivers see assigned, admin sees all
    match /bookings/{bookingId} {
      allow read: if resource.data.customerId == request.auth.uid
                  || resource.data.assignedDriverId == request.auth.uid
                  || isAdmin();
      allow create: if isCustomer();
      allow update: if isAdmin() || isAssignedDriver(bookingId);
    }
    
    // Tracking: real-time read for booking participants
    match /tracking/{bookingId} {
      allow read: if isBookingParticipant(bookingId);
      allow write: if isAssignedDriver(bookingId);
    }
  }
}
```

---

## 7. Use Case Design

### 7.1 Use Case Diagram

```
                        ┌─────────────────────────────────────┐
                        │   Smart Fleet & Logistics System    │
                        │                                     │
    ┌──────────┐        │  ┌─────────────────────────────┐   │
    │ Customer │──────────►│ Register / Login            │   │
    └──────────┘        │  └─────────────────────────────┘   │
         │              │  ┌─────────────────────────────┐   │
         │              │  │ Browse Vehicle Categories   │   │
         │              │  └─────────────────────────────┘   │
         │              │  ┌─────────────────────────────┐   │
         ├──────────────►│ Search & Book Shipment       │   │
         │              │  └─────────────────────────────┘   │
         │              │  ┌─────────────────────────────┐   │
         ├──────────────►│ Get Automated Quote          │   │
         │              │  └─────────────────────────────┘   │
         │              │  ┌─────────────────────────────┐   │
         ├──────────────►│ Make Staged Payments (UC-05) │   │
         │              │  └─────────────────────────────┘   │
         │              │  ┌─────────────────────────────┐   │
         ├──────────────►│ Track Shipment (GPS)         │   │
         │              │  └─────────────────────────────┘   │
         │              │  ┌─────────────────────────────┐   │
         └──────────────►│ Modify / Cancel Booking      │   │
                        │  └─────────────────────────────┘   │
                        │                                     │
    ┌──────────┐        │  ┌─────────────────────────────┐   │
    │  Driver  │──────────►│ View Assigned Tasks         │   │
    └──────────┘        │  └─────────────────────────────┘   │
         │              │  ┌─────────────────────────────┐   │
         ├──────────────►│ Update Trip Status           │   │
         │              │  └─────────────────────────────┘   │
         └──────────────►│ Share GPS Location           │   │
                        │                                     │
    ┌──────────┐        │  ┌─────────────────────────────┐   │
    │  Admin   │──────────►│ Review & Approve Bookings    │   │
    └──────────┘        │  └─────────────────────────────┘   │
         │              │  ┌─────────────────────────────┐   │
         ├──────────────►│ Assign Driver & Vehicle      │   │
         │              │  └─────────────────────────────┘   │
         ├──────────────►│ Manage Fleet                   │   │
         │              │  └─────────────────────────────┘   │
         └──────────────►│ Close Trip                     │   │
                        └─────────────────────────────────────┘
```

### 7.2 Use Case: UC-05 — Make Staged Payments

| Field | Detail |
|-------|--------|
| **Use Case ID** | UC-05 |
| **Title** | Make Staged Payments |
| **Actor** | Customer |
| **Description** | Handles the three-stage payment lifecycle for the shipment |
| **Pre-Condition** | Booking must be approved by Admin |
| **Post-Condition** | Payment is verified and trip status is updated |
| **Main Flow** | 1. User selects payment phase (10%, 50%, or final) → 2. System displays amount due → 3. User selects payment method → 4. Payment gateway processes transaction → 5. System verifies payment → 6. Trip status updated |
| **Alternate Flow** | Payment fails → System shows error, allows retry |
| **Exception Flow** | Deposit not paid within 24h → Auto-cancellation triggered |

---

## 8. Sequence Diagrams

### 8.1 Booking & Approval Flow

```
Customer          App              Firestore         Admin           FCM
   │               │                  │               │              │
   │──Fill Details─►│                  │               │              │
   │               │──Get Quote──────►│               │              │
   │               │◄─Quote Result───│               │              │
   │──Submit Req───►│                  │               │              │
   │               │──Create Booking─►│               │              │
   │               │                  │──Notify───────►│              │
   │               │                  │               │──Push Notif──►│
   │               │                  │◄─Approve──────│              │
   │               │                  │──Update Status│              │
   │◄─Approval Notif──────────────────────────────────────────────│
   │               │                  │               │              │
```

### 8.2 Staged Payment Flow (UC-05)

```
Customer       App           Payment GW      Cloud Fn       Firestore
   │            │                │              │              │
   │─Select Phase►│               │              │              │
   │            │─Init Payment────►│              │              │
   │            │◄─Payment URL────│              │              │
   │─Complete Pay────────────────►│              │              │
   │            │                │─Webhook──────►│              │
   │            │                │              │─Verify & Update►│
   │            │                │              │              │
   │            │◄───Payment Confirmed──────────────────────────│
   │◄─Success───│                │              │              │
```

### 8.3 Real-Time GPS Tracking Flow

```
Driver App    Location Svc    Firestore      Customer App    Maps API
    │              │              │               │              │
    │─GPS Update──►│              │               │              │
    │              │─Write Loc───►│               │              │
    │              │              │─Real-time Sub►│              │
    │              │              │               │─Render Map──►│
    │              │              │               │◄─Route Data──│
    │              │              │               │              │
    │  (every 10s) │              │               │              │
```

---

## 9. Class Diagram

```
┌─────────────────────┐     ┌─────────────────────┐
│      «interface»    │     │      «interface»    │
│   AuthRepository    │     │  BookingRepository  │
├─────────────────────┤     ├─────────────────────┤
│ +login()            │     │ +createBooking()    │
│ +register()         │     │ +getBookings()      │
│ +verifyOTP()        │     │ +updateStatus()     │
│ +logout()           │     │ +getQuote()         │
└─────────┬───────────┘     └─────────┬───────────┘
          │                           │
          ▼                           ▼
┌─────────────────────┐     ┌─────────────────────┐
│ FirebaseAuthRepo    │     │ FirestoreBookingRepo│
└─────────────────────┘     └─────────────────────┘

┌─────────────────────┐     ┌─────────────────────┐
│    AuthViewModel    │     │  BookingViewModel   │
├─────────────────────┤     ├─────────────────────┤
│ -authRepo           │     │ -bookingRepo        │
│ +loginState         │     │ +bookings           │
│ +login()            │     │ +createBooking()    │
│ +register()         │     │ +calculateQuote()   │
└─────────────────────┘     └─────────────────────┘

┌─────────────────────┐     ┌─────────────────────┐
│      Booking        │     │       Payment       │
├─────────────────────┤     ├─────────────────────┤
│ -id: String         │     │ -id: String         │
│ -customerId: String │     │ -bookingId: String  │
│ -status: TripStatus │     │ -phase: PaymentPhase│
│ -pickup: Location   │     │ -amount: Double     │
│ -dropoff: Location  │     │ -status: PayStatus  │
│ -cargo: CargoDetails│     │ -paidAt: Timestamp  │
│ -quote: Quote       │     └─────────────────────┘
│ -assignedVehicle    │
│ -assignedDriver     │     ┌─────────────────────┐
└─────────────────────┘     │      Vehicle        │
                            ├─────────────────────┤
┌─────────────────────┐     │ -id: String         │
│       User          │     │ -category: Category │
├─────────────────────┤     │ -capacityKg: Double │
│ -id: String         │     │ -baseRate: Double   │
│ -email: String      │     │ -status: VehStatus  │
│ -role: UserRole     │     └─────────────────────┘
│ -name: String       │
└─────────────────────┘     ┌─────────────────────┐
                            │   QuotingEngine     │
┌─────────────────────┐     ├─────────────────────┤
│   TrackingService   │     │ +calculate()        │
├─────────────────────┤     │ +getDistance()      │
│ +startTracking()    │     │ +applyUrgency()     │
│ +stopTracking()     │     └─────────────────────┘
│ +getCurrentLocation()│
└─────────────────────┘
```

---

## 10. UI/UX Design

### 10.1 Screen Inventory

| Screen ID | Screen Name | Role | Description |
|-----------|-------------|------|-------------|
| S01 | Splash Screen | All | App logo, loading animation |
| S02 | Login | All | Email/phone login with OTP |
| S03 | Register | All | Role selection, profile creation |
| S04 | Home Dashboard | Customer | Vehicle categories, quick book |
| S05 | Search & Filter | Customer | Location, capacity, urgency filters |
| S06 | Booking Form | Customer | Pickup/dropoff, cargo details, services |
| S07 | Quote Summary | Customer | Itemized price breakdown |
| S08 | Payment Screen | Customer | Phase selection, gateway integration |
| S09 | Tracking Map | Customer | Live GPS map with driver marker |
| S10 | Booking History | Customer | Past and active bookings |
| S11 | Driver Dashboard | Driver | Assigned tasks, status updates |
| S12 | Driver Navigation | Driver | Turn-by-turn route to pickup/dropoff |
| S13 | Admin Dashboard | Admin | Pending requests, fleet overview |
| S14 | Assignment Panel | Admin | Driver/vehicle assignment |
| S15 | Trip Management | Admin | Active trips, close trip action |
| S16 | Fleet Management | Admin | Vehicle CRUD, maintenance status |
| S17 | Notifications | All | Push notification history |
| S18 | Profile Settings | All | Edit profile, logout |

### 10.2 Navigation Flow (Customer)

```
Splash → Login/Register → Home Dashboard
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         Search & Filter   Quick Book    Booking History
              │               │
              ▼               ▼
         Booking Form ←───────┘
              │
              ▼
         Quote Summary → Submit Request → Wait for Approval
                                              │
                                              ▼
                                        Payment (10%)
                                              │
                                              ▼
                                        Track Shipment
                                              │
                                    ┌─────────┼─────────┐
                                    ▼         ▼         ▼
                              Pay at Pickup  Live Map  Notifications
                                    │
                                    ▼
                              Pay at Delivery (POD)
                                    │
                                    ▼
                              Trip Complete
```

### 10.3 Design Guidelines
| Element | Specification |
|---------|---------------|
| **Primary Color** | `#1565C0` (Professional Blue) |
| **Secondary Color** | `#FF6F00` (Action Orange) |
| **Success** | `#2E7D32` |
| **Error** | `#C62828` |
| **Typography** | Roboto (Material Design 3) |
| **Icons** | Material Icons |
| **Min SDK** | API 24 (Android 7.0) |
| **Target SDK** | API 34 (Android 14) |

---

## 11. Payment System Design

### 11.1 Payment Lifecycle

| Phase | Trigger | Amount | Status Update |
|-------|---------|--------|---------------|
| **Deposit** | Admin approves booking | 10% of total quote | `APPROVED` → `DEPOSIT_PAID` |
| **Pickup** | Driver arrives at pickup | 50% of remaining balance | `AT_PICKUP` → payment verified |
| **Final** | POD signed at destination | Remaining balance | `DELIVERED` → `CLOSED` |

### 11.2 Payment Calculation Example

```
Total Quote: PKR 50,000

Phase 0 (Deposit):     50,000 × 10% = PKR 5,000
Remaining:             50,000 - 5,000 = PKR 45,000
Phase 1 (Pickup):      45,000 × 50% = PKR 22,500
Phase 2 (Final):       45,000 - 22,500 = PKR 22,500
```

### 11.3 Auto-Cancellation Logic

```
Cloud Function: checkDepositDeadline (runs every hour)

IF booking.status == "APPROVED"
   AND booking.depositDeadline < NOW()
   AND booking.payments.deposit.status != "completed"
THEN
   booking.status = "AUTO_CANCELLED"
   releaseVehicle(booking.assignedVehicleId)
   notifyCustomer("Booking auto-cancelled: deposit not paid within 24 hours")
```

### 11.4 Cancellation Fee Policy

| Time Before Pickup | Cancellation Fee |
|--------------------|------------------|
| > 12 hours | Free cancellation |
| 6–12 hours | 25% of deposit forfeited |
| < 6 hours | 100% of deposit forfeited |

---

## 12. GPS Tracking Design

### 12.1 Tracking Architecture

```
Driver Device                    Firebase                    Customer Device
┌──────────────┐                ┌──────────┐                ┌──────────────┐
│ FusedLocation│──10s interval─►│ Firestore│──Real-time───►│ MapsFragment │
│ Provider     │                │ tracking/│   Listener     │ + Marker     │
│              │                │ {bookId} │                │ + Polyline   │
└──────────────┘                └──────────┘                └──────────────┘
                                       │
                                       ▼
                                ┌──────────────┐
                                │ Google Maps  │
                                │ Directions   │
                                │ API (Route)  │
                                └──────────────┘
```

### 12.2 Location Update Protocol
| Parameter | Value |
|-----------|-------|
| Update Interval | 10 seconds (active transit) |
| Fastest Interval | 5 seconds |
| Accuracy | HIGH_ACCURACY |
| Background | Foreground Service with notification |
| Data Stored | currentLocation (GeoPoint), route trail (array), speed, timestamp |

---

## 13. Security Design

### 13.1 Authentication Security
| Measure | Implementation |
|---------|----------------|
| Identity Verification | Firebase Auth (Email + Phone OTP) |
| Session Management | Firebase ID tokens with auto-refresh |
| Role-Based Access | Custom claims: customer, driver, admin |
| Password Policy | Min 8 chars, 1 uppercase, 1 number |

### 13.2 Data Security
| Measure | Implementation |
|---------|----------------|
| Data in Transit | HTTPS/TLS 1.3 |
| Data at Rest | Firestore encryption at rest |
| API Keys | Stored in Android Keystore / BuildConfig |
| Payment Data | PCI-compliant gateway (no card storage) |
| Firestore Rules | Role-based document access control |

### 13.3 Application Security
| Measure | Implementation |
|---------|----------------|
| Code Obfuscation | ProGuard/R8 enabled |
| Root Detection | SafetyNet/Play Integrity API |
| Certificate Pinning | OkHttp CertificatePinner |
| Input Validation | Server-side validation in Cloud Functions |

---

## 14. Notification System

### 14.1 Notification Triggers

| Event | Recipient | Message Template |
|-------|-----------|------------------|
| Booking submitted | Admin | "New logistics request #{id} awaiting review" |
| Booking approved | Customer | "Your booking #{id} has been approved. Pay deposit within 24h" |
| Deposit reminder | Customer | "Reminder: Pay PKR {amount} deposit for booking #{id}" |
| Deposit deadline | Customer | "Final reminder: Deposit due in 2 hours" |
| Auto-cancelled | Customer | "Booking #{id} cancelled — deposit not received" |
| Driver assigned | Customer | "Driver {name} assigned to your shipment" |
| Driver en route | Customer | "Driver is on the way to pickup location" |
| At pickup | Customer | "Driver arrived. Please complete 50% payment" |
| In transit | Customer | "Your shipment is on the way" |
| At destination | Customer | "Driver arrived at destination" |
| Delivered | Customer, Admin | "Shipment delivered. Please sign POD" |
| Payment received | Admin | "Payment of PKR {amount} received for #{id}" |

---

## 15. Non-Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| **Availability** | 99.9% uptime | Firebase SLA monitoring |
| **Response Time** | < 2 seconds for quotes | API latency benchmarks |
| **GPS Accuracy** | ± 10 meters | Fused Location Provider |
| **Concurrent Users** | 500+ simultaneous | Firestore auto-scaling |
| **Data Backup** | Daily automated | Firebase backup policies |
| **Scalability** | Horizontal via Firebase | Load testing with 1000 users |
| **Maintainability** | MVVM + modular code | Code review standards |
| **Usability** | Material Design 3 | User testing sessions |

---

## 16. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION ENVIRONMENT                     │
│                                                               │
│  ┌─────────────┐    ┌──────────────────────────────────┐   │
│  │ Google Play │    │         Firebase Project          │   │
│  │   Store     │    │  ┌──────────┐  ┌──────────────┐  │   │
│  │  (APK/AAB)  │    │  │ Firestore│  │ Cloud Funcs  │  │   │
│  └──────┬──────┘    │  └──────────┘  └──────────────┘  │   │
│         │           │  ┌──────────┐  ┌──────────────┐  │   │
│         │           │  │   Auth   │  │  FCM / Storage│  │   │
│  ┌──────▼──────┐    │  └──────────┘  └──────────────┘  │   │
│  │   Android   │◄───┤                                    │   │
│  │   Devices   │    └──────────────────────────────────┘   │
│  └─────────────┘                                             │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ Google Maps │    │  Payment    │    │  Firebase   │     │
│  │  Platform   │    │  Gateway    │    │  Console    │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### 16.1 Environment Configuration

| Environment | Purpose | Firebase Project |
|-------------|---------|-----------------|
| Development | Local testing | `smart-fleet-dev` |
| Staging | Pre-release testing | `smart-fleet-staging` |
| Production | Live deployment | `smart-fleet-prod` |

---

## 17. Risk Analysis & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| GPS inaccuracy in urban areas | Medium | High | Fused Location Provider + WiFi/cell tower fallback |
| Payment gateway downtime | Low | High | Retry logic + multiple gateway support |
| Firebase quota limits | Low | Medium | Monitor usage, implement caching |
| Poor network connectivity | High | Medium | Offline queue for status updates |
| Security breach | Low | Critical | Firestore rules, auth tokens, encryption |
| Scope creep | High | Medium | Strict SRS adherence, phased delivery |

---

## 18. Development Methodology

### 18.1 VU Process Model (Waterfall + Spiral)

```
Phase 1: Requirements Analysis ──────────── [Waterfall]
    │     SRS Document, Use Cases
    ▼
Phase 2: System Design ──────────────────── [Waterfall]
    │     HLD, Database Design, UI Mockups
    ▼
Phase 3: Implementation ─────────────────── [Spiral Iterations]
    │     ┌─ Iteration 1: Auth + Dashboard
    │     ├─ Iteration 2: Booking + Quoting
    │     ├─ Iteration 3: Payments + Notifications
    │     └─ Iteration 4: GPS Tracking + Admin
    ▼
Phase 4: Testing ──────────────────────────── [Spiral]
    │     Unit → Integration → System → UAT
    ▼
Phase 5: Deployment ─────────────────────── [Waterfall]
          Play Store + Firebase Production
```

### 18.2 Sprint Plan Overview

| Sprint | Duration | Deliverables |
|--------|----------|-------------|
| Sprint 1 | 2 weeks | Auth module, user registration, role management |
| Sprint 2 | 2 weeks | Service dashboard, vehicle categories, search/filter |
| Sprint 3 | 2 weeks | Booking form, quoting engine, request submission |
| Sprint 4 | 2 weeks | Admin approval, fleet assignment, notifications |
| Sprint 5 | 2 weeks | Payment integration (3-stage lifecycle) |
| Sprint 6 | 2 weeks | GPS tracking, real-time map, driver portal |
| Sprint 7 | 2 weeks | POD, trip closure, cancellation logic |
| Sprint 8 | 2 weeks | Testing, bug fixes, deployment |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| BaaS | Backend as a Service |
| FCM | Firebase Cloud Messaging |
| HLD | High-Level Design |
| MVVM | Model-View-ViewModel |
| POD | Proof of Delivery |
| SRS | Software Requirements Specification |
| VU | Virtual University of Pakistan |

---

## Appendix B: Document Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Student | BC220404864 | | |
| Supervisor | Muhammad Anwar | | |
| Reviewer | | | |

---

*End of High-Level Design Document*
