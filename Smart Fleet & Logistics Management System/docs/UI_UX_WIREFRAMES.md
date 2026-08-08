# UI/UX Wireframe Specifications
## Smart Fleet & Logistics Management System

---

## Color Palette

| Role | Color | Hex |
|------|-------|-----|
| Primary | Professional Blue | `#1565C0` |
| Primary Dark | Navy Blue | `#0D47A1` |
| Secondary | Action Orange | `#FF6F00` |
| Success | Green | `#2E7D32` |
| Error | Red | `#C62828` |
| Warning | Amber | `#F9A825` |
| Background | Light Gray | `#F5F5F5` |
| Surface | White | `#FFFFFF` |
| Text Primary | Dark Gray | `#212121` |
| Text Secondary | Medium Gray | `#757575` |

---

## Screen Wireframes

### S01: Splash Screen
```
┌─────────────────────────┐
│                         │
│                         │
│      [Truck Icon]       │
│                         │
│    SMART FLEET          │
│    & Logistics          │
│                         │
│    ─────────────        │
│    Loading...           │
│                         │
└─────────────────────────┘
```

### S02: Login Screen
```
┌─────────────────────────┐
│  ← Back                 │
│                         │
│    Welcome Back         │
│    Sign in to continue  │
│                         │
│  ┌───────────────────┐  │
│  │ 📧 Email          │  │
│  └───────────────────┘  │
│  ┌───────────────────┐  │
│  │ 🔒 Password       │  │
│  └───────────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │    SIGN IN        │  │
│  └───────────────────┘  │
│                         │
│  ─── OR ───             │
│                         │
│  ┌───────────────────┐  │
│  │ 📱 Phone Login    │  │
│  └───────────────────┘  │
│                         │
│  Don't have account?    │
│  Register               │
└─────────────────────────┘
```

### S04: Customer Home Dashboard
```
┌─────────────────────────┐
│ ☰  Smart Fleet    🔔 👤 │
│                         │
│  Hello, Muhammad! 👋    │
│  What do you need to    │
│  transport today?       │
│                         │
│  ┌─────┐ ┌─────┐ ┌────┐│
│  │ 🏠  │ │ 📦  │ │ 🚛 ││
│  │Home │ │Freight│ │Last││
│  │Shift│ │     │ │Mile││
│  └─────┘ └─────┘ └────┘│
│                         │
│  Vehicle Categories     │
│  ┌───────────────────┐  │
│  │ 🏍️ Bike    From ₨500│  │
│  ├───────────────────┤  │
│  │ 🚐 Small Van ₨2000│  │
│  ├───────────────────┤  │
│  │ 🚛 Med Truck ₨5000│  │
│  ├───────────────────┤  │
│  │ 🚚 Heavy   ₨10000 │  │
│  ├───────────────────┤  │
│  │ ❄️ Refrigerated   │  │
│  └───────────────────┘  │
│                         │
│ ┌────┐ ┌────┐ ┌────┐ ┌┐│
│ │Home│ │Book│ │Trip│ │⚙││
│ └────┘ └────┘ └────┘ └┘│
└─────────────────────────┘
```

### S06: Booking Form
```
┌─────────────────────────┐
│  ← New Booking          │
│                         │
│  📍 Pickup Location     │
│  ┌───────────────────┐  │
│  │ Select on map...  │  │
│  └───────────────────┘  │
│                         │
│  📍 Drop-off Location   │
│  ┌───────────────────┐  │
│  │ Select on map...  │  │
│  └───────────────────┘  │
│                         │
│  📦 Cargo Details       │
│  Type: [Furniture    ▼] │
│  L: [2m] W: [1m] H:[1m]│
│  Weight: [500] kg       │
│                         │
│  ⚡ Urgency             │
│  ○ Standard  ● Express  │
│                         │
│  🛠️ Add-on Services     │
│  ☑ Professional Packing │
│  ☑ Fragile Handling     │
│  ☐ Transit Insurance    │
│                         │
│  ┌───────────────────┐  │
│  │  GET QUOTE  →     │  │
│  └───────────────────┘  │
└─────────────────────────┘
```

### S07: Quote Summary
```
┌─────────────────────────┐
│  ← Quote Summary        │
│                         │
│  🚐 Small Van           │
│  Lahore → Islamabad     │
│  375 km | 500 kg        │
│                         │
│  ── Price Breakdown ──  │
│  Base Rate      ₨2,000  │
│  Distance (375km) ₨9,375│
│  Weight Surcharge ₨2,000│
│  Packing Service  ₨3,000│
│  Fragile Handling ₨1,500│
│  Express (1.5x)         │
│  ─────────────────────  │
│  TOTAL          ₨26,813 │
│                         │
│  Payment Schedule:      │
│  • Deposit (10%): ₨2,681│
│  • At Pickup (50%):     │
│    ₨12,066              │
│  • At Delivery: ₨12,066 │
│                         │
│  ┌───────────────────┐  │
│  │ SUBMIT REQUEST →  │  │
│  └───────────────────┘  │
└─────────────────────────┘
```

### S08: Payment Screen (UC-05)
```
┌─────────────────────────┐
│  ← Payment              │
│                         │
│  Booking #SF-2026-0042  │
│                         │
│  ┌───────────────────┐  │
│  │ Phase 1: DEPOSIT  │  │
│  │ ₨2,681  ✅ PAID   │  │
│  └───────────────────┘  │
│  ┌───────────────────┐  │
│  │ Phase 2: PICKUP   │  │
│  │ ₨12,066  ⏳ DUE   │  │
│  └───────────────────┘  │
│  ┌───────────────────┐  │
│  │ Phase 3: FINAL    │  │
│  │ ₨12,066  🔒 LOCKED│  │
│  └───────────────────┘  │
│                         │
│  Select Payment Method  │
│  ┌──────┐ ┌──────┐     │
│  │JazzCa│ │EasyPa│     │
│  │  sh  │ │ isa  │     │
│  └──────┘ └──────┘     │
│                         │
│  ┌───────────────────┐  │
│  │  PAY ₨12,066  →   │  │
│  └───────────────────┘  │
└─────────────────────────┘
```

### S09: Live Tracking Map
```
┌─────────────────────────┐
│  ← Track Shipment       │
│                         │
│  ┌───────────────────┐  │
│  │                   │  │
│  │    [Google Map]   │  │
│  │      🚛 ←driver   │  │
│  │    ──────route    │  │
│  │         📍dest    │  │
│  │                   │  │
│  └───────────────────┘  │
│                         │
│  Status: IN TRANSIT 🟢  │
│  Driver: Ahmed Khan     │
│  Vehicle: LHR-5678      │
│  ETA: 2h 15m            │
│                         │
│  ┌─────┬─────┬─────┐   │
│  │ 📞  │ 💬  │ ℹ️  │   │
│  │Call │Chat │Info │   │
│  └─────┴─────┴─────┘   │
└─────────────────────────┘
```

### S13: Admin Dashboard
```
┌─────────────────────────┐
│  Admin Dashboard   🔔   │
│                         │
│  ┌────┐ ┌────┐ ┌────┐  │
│  │ 12 │ │ 5  │ │ 8  │  │
│  │Pend│ │Actv│ │Done│  │
│  └────┘ └────┘ └────┘  │
│                         │
│  Pending Approvals (12) │
│  ┌───────────────────┐  │
│  │ #SF-042 | Lahore  │  │
│  │ ₨26,813 | Van     │  │
│  │ [Approve][Reject] │  │
│  ├───────────────────┤  │
│  │ #SF-041 | Karachi │  │
│  │ ₨45,000 | Truck   │  │
│  │ [Approve][Reject] │  │
│  └───────────────────┘  │
│                         │
│ ┌────┐ ┌────┐ ┌────┐ ┌┐│
│ │Dash│ │Flee│ │Trip│ │⚙││
│ └────┘ └────┘ └────┘ └┘│
└─────────────────────────┘
```

### S11: Driver Dashboard
```
┌─────────────────────────┐
│  Driver Portal     🔔   │
│                         │
│  Welcome, Ahmed! 🚛     │
│                         │
│  Active Task            │
│  ┌───────────────────┐  │
│  │ #SF-038           │  │
│  │ Lahore → Islamabad│  │
│  │ Status: EN ROUTE  │  │
│  │                   │  │
│  │ [Navigate] [Update│  │
│  │  Status]          │  │
│  └───────────────────┘  │
│                         │
│  Update Status:         │
│  ┌───────────────────┐  │
│  │ ● En Route        │  │
│  │ ○ At Pickup       │  │
│  │ ○ In Transit      │  │
│  │ ○ At Destination  │  │
│  │ ○ Delivered       │  │
│  └───────────────────┘  │
│                         │
│  GPS: 🟢 Sharing Active │
└─────────────────────────┘
```

---

## Component Library

| Component | Usage |
|-----------|-------|
| `PrimaryButton` | Main CTAs (Sign In, Submit, Pay) |
| `SecondaryButton` | Alternative actions (Phone Login, Cancel) |
| `VehicleCard` | Vehicle category display with icon, name, price |
| `BookingCard` | Booking summary in history list |
| `StatusBadge` | Colored pill showing trip status |
| `PaymentPhaseCard` | Payment milestone with status indicator |
| `MapContainer` | Google Maps fragment wrapper |
| `QuoteBreakdown` | Itemized price list |
| `NotificationItem` | Push notification list item |

---

## Typography Scale

| Style | Size | Weight | Usage |
|-------|------|--------|-------|
| Headline Large | 32sp | Bold | Splash title |
| Headline Medium | 24sp | Bold | Screen titles |
| Title Large | 20sp | SemiBold | Section headers |
| Body Large | 16sp | Regular | Main content |
| Body Medium | 14sp | Regular | Secondary text |
| Label Small | 12sp | Medium | Captions, badges |

---

*End of UI/UX Wireframe Specifications*
