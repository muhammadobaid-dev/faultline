package com.sawarri.data.model

import com.google.firebase.Timestamp
import com.google.firebase.firestore.GeoPoint

enum class UserRole { CUSTOMER, DRIVER, LOADER, ADMIN }

data class User(
    val id: String = "",
    val email: String = "",
    val phone: String = "",
    val name: String = "",
    val role: UserRole = UserRole.CUSTOMER,
    val profileImage: String = "",
    val fcmToken: String = "",
    val isActive: Boolean = true,
    val createdAt: Timestamp? = null
)

enum class VehicleCategory {
    BIKE, SMALL_VAN, MEDIUM_TRUCK, HEAVY_TRUCK, REFRIGERATED
}

enum class VehicleStatus { AVAILABLE, ASSIGNED, IN_TRANSIT, MAINTENANCE }

data class Vehicle(
    val id: String = "",
    val registrationNumber: String = "",
    val category: VehicleCategory = VehicleCategory.SMALL_VAN,
    val capacityKg: Double = 0.0,
    val capacityVolume: Double = 0.0,
    val baseRate: Double = 0.0,
    val perKmRate: Double = 0.0,
    val status: VehicleStatus = VehicleStatus.AVAILABLE,
    val assignedDriverId: String? = null
)

data class Service(
    val id: String = "",
    val name: String = "",
    val description: String = "",
    val price: Double = 0.0,
    val category: String = ""
)

data class Location(
    val address: String = "",
    val lat: Double = 0.0,
    val lng: Double = 0.0,
    val scheduledAt: Timestamp? = null
)

data class CargoDetails(
    val type: String = "",
    val length: Double = 0.0,
    val width: Double = 0.0,
    val height: Double = 0.0,
    val weight: Double = 0.0,
    val description: String = ""
)

data class Quote(
    val baseRate: Double = 0.0,
    val distanceCost: Double = 0.0,
    val weightCost: Double = 0.0,
    val volumeCost: Double = 0.0,
    val serviceCost: Double = 0.0,
    val urgencyMultiplier: Double = 1.0,
    val total: Double = 0.0
)

enum class TripStatus {
    REQUESTED, PENDING_APPROVAL, APPROVED, DEPOSIT_PAID,
    ASSIGNED, EN_ROUTE, AT_PICKUP, IN_TRANSIT,
    AT_DESTINATION, DELIVERED, CLOSED,
    REJECTED, AUTO_CANCELLED, CANCELLED
}

enum class Urgency { STANDARD, EXPRESS }

data class Booking(
    val id: String = "",
    val customerId: String = "",
    val status: TripStatus = TripStatus.REQUESTED,
    val pickup: Location = Location(),
    val dropoff: Location = Location(),
    val cargo: CargoDetails = CargoDetails(),
    val selectedServices: List<String> = emptyList(),
    val urgency: Urgency = Urgency.STANDARD,
    val quote: Quote = Quote(),
    val assignedVehicleId: String? = null,
    val assignedDriverId: String? = null,
    val assignedLoaders: List<String> = emptyList(),
    val createdAt: Timestamp? = null,
    val approvedAt: Timestamp? = null,
    val depositDeadline: Timestamp? = null
)

enum class PaymentPhase { DEPOSIT, PICKUP, FINAL }

enum class PaymentStatus { PENDING, COMPLETED, FAILED, REFUNDED }

data class Payment(
    val id: String = "",
    val bookingId: String = "",
    val userId: String = "",
    val phase: PaymentPhase = PaymentPhase.DEPOSIT,
    val amount: Double = 0.0,
    val status: PaymentStatus = PaymentStatus.PENDING,
    val gatewayRef: String = "",
    val paidAt: Timestamp? = null,
    val createdAt: Timestamp? = null
)

data class TrackingData(
    val bookingId: String = "",
    val currentLocation: GeoPoint? = null,
    val driverId: String = "",
    val lastUpdated: Timestamp? = null,
    val speed: Double = 0.0
)

data class ProofOfDelivery(
    val id: String = "",
    val bookingId: String = "",
    val signatureImageUrl: String = "",
    val recipientName: String = "",
    val deliveredAt: Timestamp? = null,
    val photos: List<String> = emptyList(),
    val notes: String = ""
)

data class AppNotification(
    val id: String = "",
    val userId: String = "",
    val title: String = "",
    val body: String = "",
    val type: String = "",
    val bookingId: String? = null,
    val isRead: Boolean = false,
    val createdAt: Timestamp? = null
)
