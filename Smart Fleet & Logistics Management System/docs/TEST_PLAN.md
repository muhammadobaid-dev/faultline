# Test Plan
## Smart Fleet & Logistics Management System

| Version | 1.0 |
|---------|-----|
| Group ID | S26PROJECTD2A66 |
| Student ID | BC220404864 |

---

## 1. Test Strategy

| Level | Scope | Tools |
|-------|-------|-------|
| Unit Testing | ViewModels, Repositories, Quoting Engine | JUnit, Mockito |
| Integration Testing | Firebase Auth, Firestore CRUD, Cloud Functions | Firebase Emulator |
| System Testing | End-to-end user flows | Android Emulator, Physical Device |
| UAT | Supervisor and peer review | Manual testing checklist |

---

## 2. Test Cases

### TC-01: User Registration
| Field | Value |
|-------|-------|
| **ID** | TC-01 |
| **Feature** | User Authentication |
| **Pre-condition** | App installed, no existing account |
| **Steps** | 1. Open app → 2. Tap Register → 3. Enter name, email, password → 4. Select role "Customer" → 5. Tap Register |
| **Expected** | Account created, redirected to Home Dashboard |
| **Priority** | High |

### TC-02: User Login
| Field | Value |
|-------|-------|
| **ID** | TC-02 |
| **Feature** | User Authentication |
| **Pre-condition** | Registered account exists |
| **Steps** | 1. Open app → 2. Enter email and password → 3. Tap Sign In |
| **Expected** | Login successful, Home Dashboard displayed |
| **Priority** | High |

### TC-03: Browse Vehicle Categories
| Field | Value |
|-------|-------|
| **ID** | TC-03 |
| **Feature** | Service Dashboard |
| **Pre-condition** | User logged in as Customer |
| **Steps** | 1. Navigate to Home → 2. View vehicle categories list |
| **Expected** | All 5 categories displayed with base rates |
| **Priority** | High |

### TC-04: Get Automated Quote
| Field | Value |
|-------|-------|
| **ID** | TC-04 |
| **Feature** | Automated Quoting |
| **Pre-condition** | User logged in, booking form filled |
| **Steps** | 1. Select Small Van → 2. Enter pickup/dropoff → 3. Enter cargo: 2×1×1m, 500kg → 4. Tap Get Quote |
| **Expected** | Itemized quote displayed within 2 seconds |
| **Priority** | High |

### TC-05: Submit Booking Request
| Field | Value |
|-------|-------|
| **ID** | TC-05 |
| **Feature** | Shipment Request |
| **Pre-condition** | Quote generated and accepted |
| **Steps** | 1. Review quote → 2. Tap Submit Request |
| **Expected** | Booking created with status PENDING_APPROVAL, admin notified |
| **Priority** | High |

### TC-06: Admin Approve Booking
| Field | Value |
|-------|-------|
| **ID** | TC-06 |
| **Feature** | Admin Review |
| **Pre-condition** | Pending booking exists |
| **Steps** | 1. Login as Admin → 2. View pending requests → 3. Tap Approve |
| **Expected** | Status changes to APPROVED, customer receives notification |
| **Priority** | High |

### TC-07: Make Deposit Payment (UC-05)
| Field | Value |
|-------|-------|
| **ID** | TC-07 |
| **Feature** | Staged Payments |
| **Pre-condition** | Booking approved by admin |
| **Steps** | 1. Customer opens payment screen → 2. Select deposit phase → 3. Complete payment via gateway |
| **Expected** | 10% deposit verified, status updated to DEPOSIT_PAID |
| **Priority** | Critical |

### TC-08: Auto-Cancellation (24h)
| Field | Value |
|-------|-------|
| **ID** | TC-08 |
| **Feature** | Auto-Cancellation |
| **Pre-condition** | Booking approved, deposit not paid, 24h elapsed |
| **Steps** | 1. Wait for Cloud Function cron → 2. Check booking status |
| **Expected** | Status = AUTO_CANCELLED, vehicle released, customer notified |
| **Priority** | High |

### TC-09: Driver Assignment
| Field | Value |
|-------|-------|
| **ID** | TC-09 |
| **Feature** | Task Assignment |
| **Pre-condition** | Deposit paid |
| **Steps** | 1. Admin assigns driver and vehicle → 2. Driver opens app |
| **Expected** | Task visible in Driver Dashboard with route details |
| **Priority** | High |

### TC-10: Real-Time GPS Tracking
| Field | Value |
|-------|-------|
| **ID** | TC-10 |
| **Feature** | GPS Tracking |
| **Pre-condition** | Trip status IN_TRANSIT |
| **Steps** | 1. Driver shares location → 2. Customer opens tracking screen |
| **Expected** | Live map shows driver marker updating every 10 seconds |
| **Priority** | Critical |

### TC-11: Pickup Payment (50%)
| Field | Value |
|-------|-------|
| **ID** | TC-11 |
| **Feature** | Staged Payments |
| **Pre-condition** | Driver at pickup location |
| **Steps** | 1. Driver updates status to AT_PICKUP → 2. Customer pays 50% |
| **Expected** | Payment verified, status progresses |
| **Priority** | Critical |

### TC-12: Proof of Delivery
| Field | Value |
|-------|-------|
| **ID** | TC-12 |
| **Feature** | POD |
| **Pre-condition** | Driver at destination |
| **Steps** | 1. Customer signs POD → 2. Pay final balance |
| **Expected** | POD saved, final payment verified, status = DELIVERED |
| **Priority** | High |

### TC-13: Trip Closure
| Field | Value |
|-------|-------|
| **ID** | TC-13 |
| **Feature** | Status Closure |
| **Pre-condition** | Delivery and payment complete |
| **Steps** | 1. Admin closes trip |
| **Expected** | Status = CLOSED, driver and vehicle freed |
| **Priority** | Medium |

### TC-14: Booking Cancellation
| Field | Value |
|-------|-------|
| **ID** | TC-14 |
| **Feature** | Booking Modifications |
| **Pre-condition** | Booking exists, >12h before pickup |
| **Steps** | 1. Customer cancels booking |
| **Expected** | Free cancellation, deposit refunded |
| **Priority** | Medium |

### TC-15: Push Notifications
| Field | Value |
|-------|-------|
| **ID** | TC-15 |
| **Feature** | Notifications |
| **Pre-condition** | FCM token registered |
| **Steps** | 1. Trigger status change → 2. Check device notification |
| **Expected** | Push notification received with correct message |
| **Priority** | Medium |

---

## 3. Performance Benchmarks

| Metric | Target | Test Method |
|--------|--------|-------------|
| App launch time | < 3 seconds | Android Profiler |
| Quote generation | < 2 seconds | Cloud Function latency |
| GPS update interval | 10 seconds | Logcat timestamps |
| Map render time | < 1 second | Systrace |
| Payment processing | < 5 seconds | Gateway response time |

---

## 4. Security Test Cases

| ID | Test | Expected |
|----|------|----------|
| SEC-01 | Access booking of another user | Denied by Firestore rules |
| SEC-02 | Driver updates unassigned booking | Denied by Firestore rules |
| SEC-03 | Unauthenticated API access | 401 Unauthorized |
| SEC-04 | SQL/NoSQL injection in booking form | Input sanitized, no breach |
| SEC-05 | Payment amount tampering | Server-side verification rejects |

---

*End of Test Plan*
