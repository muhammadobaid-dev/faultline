# Smart Fleet & Logistics Management System
## Software Requirements Specification (SRS)

| **Field** | **Details** |
|-----------|-------------|
| **Version** | 1.0 |
| **Group ID** | S26PROJECTD2A66 |
| **Student ID** | BC220404864 |
| **Supervisor** | Muhammad Anwar |
| **Date** | May 14, 2026 |

---

## 1. Introduction

### 1.1 Purpose
This SRS defines the functional and non-functional requirements for the Smart Fleet & Logistics Management System — a mobile application for commercial logistics automation.

### 1.2 Scope
The system streamlines booking and management of logistics services including home shifting, freight transport, and last-mile delivery. Users book vehicles from bikes to heavy-duty trucks with value-added services and staged payments.

---

## 2. Functional Requirements

### FR-01: User Authentication
- Customers and Drivers register/login via email or phone verification
- Firebase Authentication for secure identity management
- Role-based access: Customer, Driver, Loader, Admin

### FR-02: Service Dashboard
- Display vehicle categories based on cargo requirements
- Categories: Bike, Small Van, Medium Truck, Heavy Truck, Refrigerated Truck
- Show value-added services: packing, labor, insurance, fragile handling

### FR-03: Search & Filter
- Search fleets by pickup location, destination, load capacity
- Filter by urgency: Standard vs Express
- Real-time availability status

### FR-04: Booking & Service Selection
- Input pickup and drop-off points (with map picker)
- Select additional services (Fragile Handling, Insurance Coverage)
- Specify cargo type, dimensions, and estimated weight

### FR-05: Automated Quoting
- Instant price quote based on cargo dimensions and weight
- Factor in distance, vehicle type, services, and urgency multiplier
- Display itemized quote breakdown

### FR-06: Shipment Request Submission
- Submit formal Logistics Request after quote acceptance
- Generate unique booking ID
- Notify admin for review

### FR-07: Admin Review & Confirmation
- Admin reviews route and load details
- Approve or reject booking requests
- Push notification sent to customer on approval

### FR-08: Initial Security Deposit
- 10% commitment fee via integrated payment gateway
- Locks vehicle and driver assignment
- Auto-cancel if not paid within 24 hours of approval

### FR-09: Operational Breakdown
- Display assigned team: Driver, Loader 1, Loader 2
- Show vehicle registration details
- Trip timeline and milestones

### FR-10: Task Assignment
- Admin assigns routes and cargo lists to drivers
- Tasks visible in Driver-specific interface
- Vehicle-driver pairing management

### FR-11: Auto-Cancellation Logic
- Release vehicle slot if deposit unpaid within 24 hours
- Notify customer of auto-cancellation
- Return vehicle to available pool

### FR-12: Booking Modifications
- Reschedule or cancel up to 12 hours before pickup
- Cancellation fees based on proximity to start time
- Modification history tracking

### FR-13: Staged Payment Milestones
- **Phase 1:** 50% of remaining balance at pickup location
- **Phase 2:** Final balance upon digital Proof of Delivery (POD)
- Payment verification before status progression

### FR-14: Status Closure
- Admin formally closes trip after delivery and payment
- Free up driver and vehicle for new assignments
- Generate trip completion report

### FR-15: Automated Notifications
- Real-time updates: driver arrival, transit milestones, payment reminders
- Firebase Cloud Messaging (FCM) integration
- In-app notification history

### FR-16: Real-Time GPS Tracking
- Live shipment monitoring via Google Maps Platform
- Driver location updates every 10 seconds during transit
- Route visualization with breadcrumb trail

---

## 3. Non-Functional Requirements

### NFR-01: Security
- Firebase Authentication for all user data protection
- Role-based Firestore security rules
- Encrypted data in transit (HTTPS/TLS)

### NFR-02: Reliability
- 24/7 availability for booking and real-time transit updates
- 99.9% uptime target via Firebase infrastructure
- Offline queue for critical status updates

### NFR-03: Accuracy
- Precise price calculations matching manual quotes within 5%
- GPS location accuracy within ±10 meters
- Payment amount verification with zero tolerance

### NFR-04: Performance
- Quote generation under 2 seconds
- App launch under 3 seconds
- Map rendering under 1 second

### NFR-05: Usability
- Material Design 3 guidelines
- Intuitive navigation with max 3 taps to book
- Support for English and Urdu languages

### NFR-06: Scalability
- Support 500+ concurrent users
- Firebase auto-scaling for database and functions

---

## 4. Use Case: UC-05 — Make Staged Payments

| Field | Detail |
|-------|--------|
| **Use Case ID** | UC-05 |
| **Title** | Make Staged Payments |
| **Actor** | Customer |
| **Actions** | User selects payment phase (10%, 50%, or final) and completes transaction |
| **Description** | Handles the three-stage payment lifecycle for the shipment |
| **Pre-Condition** | Booking must be approved by the Admin |
| **Post-Condition** | Payment is verified and trip status is updated |

---

## 5. Tools & Technologies

| Component | Technology |
|-----------|------------|
| Frontend | Android Studio (Kotlin) |
| Backend/Database | Firebase (Firestore, Authentication) |
| APIs | Google Maps Platform |
| Notifications | Firebase Cloud Messaging |
| Payment | JazzCash / EasyPaisa |

---

## 6. Methodology

**VU Process Model** — combination of Waterfall and Spiral:
- **Waterfall:** Requirements analysis, system design (sequential phases)
- **Spiral:** Iterative development for GPS tracking and payment gateways

---

*End of SRS Document*
