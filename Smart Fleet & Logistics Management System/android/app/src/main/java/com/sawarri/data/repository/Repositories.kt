package com.sawarri.data.repository

import com.google.firebase.Timestamp
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.PhoneAuthCredential
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.functions.FirebaseFunctions
import com.sawarri.data.model.*
import com.sawarri.util.QuotingEngine
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.tasks.await

class AuthRepository(
    private val auth: FirebaseAuth = FirebaseAuth.getInstance(),
    private val firestore: FirebaseFirestore = FirebaseFirestore.getInstance()
) {
    val currentUserId: String? get() = auth.currentUser?.uid
    val isLoggedIn: Boolean get() = auth.currentUser != null

    suspend fun loginWithEmail(email: String, password: String): Result<User> = runCatching {
        auth.signInWithEmailAndPassword(email, password).await()
        getUserProfile(auth.currentUser!!.uid).getOrThrow()
    }

    suspend fun registerWithEmail(
        email: String, password: String, name: String, role: UserRole
    ): Result<User> = runCatching {
        val result = auth.createUserWithEmailAndPassword(email, password).await()
        val user = User(
            id = result.user!!.uid,
            email = email,
            name = name,
            role = role,
            createdAt = Timestamp.now()
        )
        firestore.collection("users").document(user.id).set(user).await()
        user
    }

    suspend fun verifyPhone(credential: PhoneAuthCredential): Result<User> = runCatching {
        auth.signInWithCredential(credential).await()
        getUserProfile(auth.currentUser!!.uid).getOrThrow()
    }

    suspend fun getUserProfile(userId: String): Result<User> = runCatching {
        val doc = firestore.collection("users").document(userId).get().await()
        doc.toObject(User::class.java)!!.copy(id = doc.id)
    }

    fun logout() = auth.signOut()
}

class BookingRepository(
    private val firestore: FirebaseFirestore = FirebaseFirestore.getInstance(),
    private val functions: FirebaseFunctions = FirebaseFunctions.getInstance()
) {
    suspend fun createBooking(booking: Booking): Result<String> = runCatching {
        val docRef = firestore.collection("bookings").document()
        val bookingWithId = booking.copy(
            id = docRef.id,
            status = TripStatus.PENDING_APPROVAL,
            createdAt = Timestamp.now()
        )
        docRef.set(bookingWithId).await()
        docRef.id
    }

    suspend fun getBookingById(bookingId: String): Result<Booking> = runCatching {
        val doc = firestore.collection("bookings").document(bookingId).get().await()
        doc.toObject(Booking::class.java)!!.copy(id = doc.id)
    }

    suspend fun getQuoteLocal(
        vehicleCategory: String,
        distanceKm: Double,
        weightKg: Double,
        lengthM: Double,
        widthM: Double,
        heightM: Double,
        services: List<Service>,
        urgency: String
    ): Quote = QuotingEngine.calculate(
        vehicleCategory, distanceKm, weightKg, lengthM, widthM, heightM, services, urgency
    )

    suspend fun getQuote(
        vehicleCategory: String,
        distanceKm: Double,
        weightKg: Double,
        lengthM: Double,
        widthM: Double,
        heightM: Double,
        selectedServiceIds: List<String>,
        urgency: String
    ): Result<Quote> = runCatching {
        try {
            val data = hashMapOf(
                "vehicleCategory" to vehicleCategory,
                "distanceKm" to distanceKm,
                "weightKg" to weightKg,
                "lengthM" to lengthM,
                "widthM" to widthM,
                "heightM" to heightM,
                "selectedServiceIds" to selectedServiceIds,
                "urgency" to urgency
            )
            val result = functions.getHttpsCallable("calculateQuote").call(data).await()
            @Suppress("UNCHECKED_CAST")
            val map = result.data as Map<String, Any>
            Quote(
                baseRate = (map["baseRate"] as Number).toDouble(),
                distanceCost = (map["distanceCost"] as Number).toDouble(),
                weightCost = (map["weightCost"] as Number).toDouble(),
                volumeCost = (map["volumeCost"] as Number).toDouble(),
                serviceCost = (map["serviceCost"] as Number).toDouble(),
                urgencyMultiplier = (map["urgencyMultiplier"] as Number).toDouble(),
                total = (map["total"] as Number).toDouble()
            )
        } catch (_: Exception) {
            throw QuoteFallbackException()
        }
    }

    class QuoteFallbackException : Exception()

    fun getCustomerBookings(customerId: String): Flow<List<Booking>> = callbackFlow {
        val listener = firestore.collection("bookings")
            .whereEqualTo("customerId", customerId)
            .addSnapshotListener { snapshot, error ->
                if (error != null) { close(error); return@addSnapshotListener }
                val bookings = snapshot?.documents?.mapNotNull { doc ->
                    doc.toObject(Booking::class.java)?.copy(id = doc.id)
                } ?: emptyList()
                trySend(bookings)
            }
        awaitClose { listener.remove() }
    }

    fun getDriverBookings(driverId: String): Flow<List<Booking>> = callbackFlow {
        val listener = firestore.collection("bookings")
            .whereEqualTo("assignedDriverId", driverId)
            .addSnapshotListener { snapshot, error ->
                if (error != null) { close(error); return@addSnapshotListener }
                val bookings = snapshot?.documents?.mapNotNull { doc ->
                    doc.toObject(Booking::class.java)?.copy(id = doc.id)
                } ?: emptyList()
                trySend(bookings)
            }
        awaitClose { listener.remove() }
    }

    suspend fun updateBookingStatus(bookingId: String, status: TripStatus): Result<Unit> =
        runCatching {
            firestore.collection("bookings").document(bookingId)
                .update("status", status.name).await()
        }
}

class VehicleRepository(
    private val firestore: FirebaseFirestore = FirebaseFirestore.getInstance()
) {
    fun getAvailableVehicles(category: VehicleCategory? = null): Flow<List<Vehicle>> =
        callbackFlow {
            var query = firestore.collection("vehicles")
                .whereEqualTo("status", VehicleStatus.AVAILABLE.name)
            if (category != null) {
                query = query.whereEqualTo("category", category.name)
            }
            val listener = query.addSnapshotListener { snapshot, error ->
                if (error != null) { close(error); return@addSnapshotListener }
                val vehicles = snapshot?.documents?.mapNotNull { doc ->
                    doc.toObject(Vehicle::class.java)?.copy(id = doc.id)
                } ?: emptyList()
                trySend(vehicles)
            }
            awaitClose { listener.remove() }
        }

    suspend fun getServices(): Result<List<Service>> = runCatching {
        firestore.collection("services").get().await()
            .documents.mapNotNull { doc ->
                doc.toObject(Service::class.java)?.copy(id = doc.id)
            }
    }
}

class TrackingRepository(
    private val firestore: FirebaseFirestore = FirebaseFirestore.getInstance()
) {
    fun observeTracking(bookingId: String): Flow<TrackingData?> = callbackFlow {
        val listener = firestore.collection("tracking").document(bookingId)
            .addSnapshotListener { snapshot, error ->
                if (error != null) { close(error); return@addSnapshotListener }
                val data = snapshot?.toObject(TrackingData::class.java)
                    ?.copy(bookingId = bookingId)
                trySend(data)
            }
        awaitClose { listener.remove() }
    }

    suspend fun updateLocation(
        bookingId: String, driverId: String, location: com.google.firebase.firestore.GeoPoint
    ): Result<Unit> = runCatching {
        firestore.collection("tracking").document(bookingId).set(
            mapOf(
                "bookingId" to bookingId,
                "driverId" to driverId,
                "currentLocation" to location,
                "lastUpdated" to com.google.firebase.firestore.FieldValue.serverTimestamp()
            )
        ).await()
    }
}

class PaymentRepository(
    private val firestore: FirebaseFirestore = FirebaseFirestore.getInstance()
) {
    suspend fun createPayment(payment: Payment): Result<String> = runCatching {
        val docRef = firestore.collection("payments").document()
        val paymentData = payment.copy(
            id = docRef.id,
            createdAt = Timestamp.now()
        )
        docRef.set(paymentData).await()
        docRef.id
    }

    fun getPaymentsForBooking(bookingId: String): Flow<List<Payment>> = callbackFlow {
        val listener = firestore.collection("payments")
            .whereEqualTo("bookingId", bookingId)
            .addSnapshotListener { snapshot, error ->
                if (error != null) { close(error); return@addSnapshotListener }
                val payments = snapshot?.documents?.mapNotNull { doc ->
                    doc.toObject(Payment::class.java)?.copy(id = doc.id)
                } ?: emptyList()
                trySend(payments)
            }
        awaitClose { listener.remove() }
    }

    suspend fun completePayment(
        bookingId: String,
        phase: PaymentPhase,
        amount: Double,
        userId: String,
        gatewayRef: String
    ): Result<Unit> = runCatching {
        val paymentRef = firestore.collection("payments").document()
        paymentRef.set(
            Payment(
                id = paymentRef.id,
                bookingId = bookingId,
                userId = userId,
                phase = phase,
                amount = amount,
                status = PaymentStatus.COMPLETED,
                gatewayRef = gatewayRef,
                paidAt = Timestamp.now(),
                createdAt = Timestamp.now()
            )
        ).await()

        val newStatus = when (phase) {
            PaymentPhase.DEPOSIT -> TripStatus.DEPOSIT_PAID.name
            PaymentPhase.PICKUP -> TripStatus.IN_TRANSIT.name
            PaymentPhase.FINAL -> TripStatus.DELIVERED.name
        }
        firestore.collection("bookings").document(bookingId)
            .update("status", newStatus).await()
    }

    fun getPaymentAmount(quote: Quote, phase: PaymentPhase): Double = when (phase) {
        PaymentPhase.DEPOSIT -> quote.total * 0.10
        PaymentPhase.PICKUP -> (quote.total - quote.total * 0.10) * 0.50
        PaymentPhase.FINAL -> quote.total - (quote.total * 0.10) - ((quote.total - quote.total * 0.10) * 0.50)
    }
}
