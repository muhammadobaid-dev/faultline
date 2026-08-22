package com.sawarri.data.repository

import com.google.firebase.Timestamp
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.PhoneAuthCredential
import com.google.firebase.firestore.DocumentReference
import com.google.firebase.firestore.DocumentSnapshot
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.FirebaseFirestoreException
import com.google.firebase.firestore.Source
import com.google.firebase.functions.FirebaseFunctions
import com.sawarri.SawarriApp
import com.sawarri.data.model.*
import com.sawarri.util.QuotingEngine
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withTimeout

class AuthRepository(
    private val auth: FirebaseAuth = FirebaseAuth.getInstance(),
    private val firestore: FirebaseFirestore = FirebaseFirestore.getInstance(),
    private val localAuth: LocalAuthStore = SawarriApp.instance.localAuthStore
) {
    val currentUserId: String?
        get() = auth.currentUser?.uid ?: localAuth.currentUserId

    val isLoggedIn: Boolean
        get() = currentUserId != null

    /** Login: local demo accounts first (instant), then Firebase. */
    suspend fun login(identifier: String, password: String): Result<User> = runCatching {
        val localResult = runCatching { localAuth.login(identifier, password) }
        if (localResult.isSuccess) return@runCatching localResult.getOrThrow()

        val localMsg = localResult.exceptionOrNull()?.message.orEmpty()
        if (localMsg.contains("Invalid password", ignoreCase = true)) {
            error("Invalid password")
        }

        try {
            withTimeout(AUTH_TIMEOUT_MS) {
                val trimmed = identifier.trim()
                val email = if (trimmed.contains("@")) {
                    trimmed.lowercase()
                } else {
                    resolveEmail(trimmed)
                }
                auth.signInWithEmailAndPassword(email, password).await()
                fetchFirebaseProfile(auth.currentUser!!.uid)
            }
        } catch (e: Exception) {
            if (!shouldFallbackLocal(e)) throw e
            throw localResult.exceptionOrNull() ?: e
        }
    }.recoverCatching { e -> throw friendlyAuthError(e) }

    suspend fun loginWithEmail(email: String, password: String): Result<User> =
        login(email, password)

    /**
     * Register: try Firebase quickly; if unreachable, save account locally
     * so the app still works for demo / submission on TECNO devices.
     */
    suspend fun register(
        name: String,
        username: String,
        email: String,
        password: String,
        address: String,
        phone: String,
        role: UserRole
    ): Result<User> = runCatching {
        val cleanUsername = username.trim().lowercase()
        val cleanEmail = email.trim().lowercase()
        val cleanPhone = normalizePkMobile(phone)

        require(cleanUsername.matches(Regex("^[a-z0-9._]{3,20}$"))) {
            "Username: 3–20 chars, letters/numbers/._ only"
        }
        require(cleanPhone.matches(Regex("03[0-9]{9}"))) {
            "Enter valid mobile: 03XXXXXXXXX"
        }

        try {
            withTimeout(AUTH_TIMEOUT_MS) {
                registerOnFirebase(
                    name.trim(), cleanUsername, cleanEmail, password,
                    address.trim(), cleanPhone, role
                )
            }
        } catch (e: Exception) {
            if (!shouldFallbackLocal(e)) throw e
            localAuth.register(
                name.trim(), cleanUsername, cleanEmail, password,
                address.trim(), cleanPhone, role
            )
        }
    }.recoverCatching { e -> throw friendlyAuthError(e) }

    private suspend fun registerOnFirebase(
        name: String,
        cleanUsername: String,
        cleanEmail: String,
        password: String,
        address: String,
        cleanPhone: String,
        role: UserRole
    ): User {
        val usernameRef = firestore.collection("usernames").document(cleanUsername)
        val result = auth.createUserWithEmailAndPassword(cleanEmail, password).await()
        val uid = result.user!!.uid
        val systemUserId = "SWR-${uid.take(8).uppercase()}"

        val user = User(
            id = uid,
            userId = systemUserId,
            name = name,
            username = cleanUsername,
            email = cleanEmail,
            address = address,
            phone = cleanPhone,
            role = role,
            createdAt = Timestamp.now()
        )

        try {
            val batch = firestore.batch()
            batch.set(firestore.collection("users").document(uid), user)
            batch.set(
                usernameRef,
                mapOf(
                    "email" to cleanEmail,
                    "userId" to uid,
                    "username" to cleanUsername
                )
            )
            batch.commit().await()
            return user
        } catch (e: Exception) {
            try {
                result.user?.delete()?.await()
            } catch (_: Exception) {
            }
            auth.signOut()
            if (isPermissionDenied(e)) error("Username already taken")
            throw e
        }
    }

    suspend fun registerWithEmail(
        email: String, password: String, name: String, role: UserRole
    ): Result<User> = register(
        name = name,
        username = email.substringBefore("@").lowercase().take(20),
        email = email,
        password = password,
        address = "",
        phone = "03000000000",
        role = role
    )

    suspend fun updateRegistrationInfo(
        name: String,
        username: String,
        address: String,
        phone: String
    ): Result<User> = runCatching {
        val uid = currentUserId ?: error("Not logged in")
        if (uid.startsWith("local-")) {
            error("Local demo account — profile edit Firebase ke baad available hoga")
        }
        withTimeout(AUTH_TIMEOUT_MS) {
            val profile = fetchFirebaseProfile(uid)
            val cleanUsername = username.trim().lowercase()
            val cleanPhone = normalizePkMobile(phone)

            require(cleanUsername.matches(Regex("^[a-z0-9._]{3,20}$"))) {
                "Username: 3–20 chars, letters/numbers/._ only"
            }
            require(cleanPhone.matches(Regex("03[0-9]{9}"))) {
                "Enter valid mobile: 03XXXXXXXXX"
            }

            if (cleanUsername != profile.username) {
                val newRef = firestore.collection("usernames").document(cleanUsername)
                val taken = tryGetDocument(newRef)
                if (taken?.exists() == true) error("Username already taken")
                if (profile.username.isNotBlank()) {
                    firestore.collection("usernames").document(profile.username).delete().await()
                }
                newRef.set(
                    mapOf(
                        "email" to profile.email,
                        "userId" to uid,
                        "username" to cleanUsername
                    )
                ).await()
            }

            val updates = mapOf(
                "name" to name.trim(),
                "username" to cleanUsername,
                "address" to address.trim(),
                "phone" to cleanPhone
            )
            firestore.collection("users").document(uid).update(updates).await()
            fetchFirebaseProfile(uid)
        }
    }.recoverCatching { e -> throw friendlyAuthError(e) }

    suspend fun verifyPhone(credential: PhoneAuthCredential): Result<User> = runCatching {
        withTimeout(AUTH_TIMEOUT_MS) {
            auth.signInWithCredential(credential).await()
            fetchFirebaseProfile(auth.currentUser!!.uid)
        }
    }.recoverCatching { e -> throw friendlyAuthError(e) }

    suspend fun getUserProfile(userId: String): Result<User> = runCatching {
        if (userId.startsWith("local-")) {
            localAuth.getUser(userId) ?: error("Local session expired. Register again.")
        } else {
            withTimeout(PROFILE_TIMEOUT_MS) {
                fetchFirebaseProfile(userId)
            }
        }
    }.recoverCatching { e -> throw friendlyAuthError(e) }

    private suspend fun fetchFirebaseProfile(userId: String): User {
        val doc = getDocumentFast(firestore.collection("users").document(userId))
        require(doc.exists()) { "User profile not found" }
        return doc.toObject(User::class.java)!!.copy(id = doc.id)
    }

    private suspend fun resolveEmail(identifier: String): String {
        if (identifier.contains("@")) return identifier.lowercase()
        val snap = getDocumentFast(
            firestore.collection("usernames").document(identifier.lowercase())
        )
        if (!snap.exists()) error("Username not found")
        return snap.getString("email") ?: error("Username not found")
    }

    fun logout() {
        auth.signOut()
        localAuth.logout()
    }

    private fun shouldFallbackLocal(e: Throwable): Boolean {
        if (e is TimeoutCancellationException) return true
        if (isOfflineError(e)) return true
        val msg = e.message.orEmpty()
        return msg.contains("network", ignoreCase = true) ||
            msg.contains("unreachable", ignoreCase = true) ||
            msg.contains("Unable to resolve host", ignoreCase = true)
    }

    private suspend fun tryGetDocument(ref: DocumentReference): DocumentSnapshot? {
        return try {
            withTimeout(5_000) { ref.get().await() }
        } catch (e: Exception) {
            if (e is TimeoutCancellationException || isOfflineError(e)) null else throw e
        }
    }

    private suspend fun getDocumentFast(ref: DocumentReference): DocumentSnapshot {
        return try {
            withTimeout(8_000) { ref.get().await() }
        } catch (e: Exception) {
            if (!isOfflineError(e) && e !is TimeoutCancellationException) throw e
            ref.get(Source.CACHE).await()
        }
    }

    private fun isOfflineError(e: Throwable): Boolean {
        val msg = e.message.orEmpty()
        if (msg.contains("offline", ignoreCase = true) ||
            msg.contains("UNAVAILABLE", ignoreCase = true)
        ) return true
        return (e as? FirebaseFirestoreException)?.code?.name == "UNAVAILABLE"
    }

    private fun isPermissionDenied(e: Throwable): Boolean {
        val msg = e.message.orEmpty()
        if (msg.contains("PERMISSION_DENIED", ignoreCase = true) ||
            msg.contains("permission-denied", ignoreCase = true)
        ) return true
        return (e as? FirebaseFirestoreException)?.code?.name == "PERMISSION_DENIED"
    }

    private fun friendlyAuthError(e: Throwable): Throwable {
        // Do not remap errors already meant for the user (validation / local auth)
        val msg = e.message.orEmpty()
        if (msg.contains("Username") ||
            msg.contains("Email") ||
            msg.contains("password", ignoreCase = true) ||
            msg.contains("mobile", ignoreCase = true) ||
            msg.contains("not found", ignoreCase = true) ||
            msg.contains("Local demo")
        ) return e

        return when {
            e is TimeoutCancellationException || isOfflineError(e) ->
                IllegalStateException(
                    "Firebase phone pe block hai. App ne local demo account use kiya / try again."
                )
            else -> e
        }
    }

    companion object {
        // Short so local fallback kicks in fast for demo/submission
        private const val AUTH_TIMEOUT_MS = 8_000L
        private const val PROFILE_TIMEOUT_MS = 8_000L

        fun normalizePkMobile(raw: String): String {
            var digits = raw.replace(Regex("[^0-9]"), "")
            when {
                digits.startsWith("9203") && digits.length == 13 ->
                    digits = digits.removePrefix("92")
                digits.startsWith("92") && digits.length == 12 ->
                    digits = "0" + digits.removePrefix("92")
                digits.length == 10 && digits.startsWith("3") ->
                    digits = "0$digits"
            }
            return digits
        }
    }
}

class BookingRepository(
    private val firestore: FirebaseFirestore = FirebaseFirestore.getInstance(),
    private val functions: FirebaseFunctions = FirebaseFunctions.getInstance(),
    private val localData: LocalDataStore = SawarriApp.instance.localDataStore
) {
    suspend fun createBooking(booking: Booking): Result<String> = runCatching {
        // Always persist locally so demo works on TECNO; also try Firebase
        val localId = localData.createBooking(booking)
        if (!SawarriApp.isLocalUser(booking.customerId)) {
            try {
                val docRef = firestore.collection("bookings").document(localId)
                docRef.set(
                    booking.copy(
                        id = localId,
                        status = TripStatus.PENDING_APPROVAL,
                        createdAt = Timestamp.now()
                    )
                ).await()
            } catch (_: Exception) {
            }
        }
        localId
    }

    suspend fun getBookingById(bookingId: String): Result<Booking> = runCatching {
        localData.getBooking(bookingId)
            ?: run {
                val doc = firestore.collection("bookings").document(bookingId).get().await()
                doc.toObject(Booking::class.java)?.copy(id = doc.id)
                    ?: error("Booking not found")
            }
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

    fun getCustomerBookings(customerId: String): Flow<List<Booking>> {
        if (SawarriApp.isLocalUser(customerId)) {
            return localData.customerBookings(customerId)
        }
        return callbackFlow {
            // Emit local first, then Firestore
            trySend(localData.bookingsFlow.value.filter { it.customerId == customerId })
            val listener = firestore.collection("bookings")
                .whereEqualTo("customerId", customerId)
                .addSnapshotListener { snapshot, error ->
                    if (error != null) {
                        trySend(localData.bookingsFlow.value.filter { it.customerId == customerId })
                        return@addSnapshotListener
                    }
                    val bookings = snapshot?.documents?.mapNotNull { doc ->
                        doc.toObject(Booking::class.java)?.copy(id = doc.id)
                    } ?: emptyList()
                    trySend(bookings.ifEmpty {
                        localData.bookingsFlow.value.filter { it.customerId == customerId }
                    })
                }
            awaitClose { listener.remove() }
        }
    }

    fun getDriverBookings(driverId: String): Flow<List<Booking>> {
        if (SawarriApp.isLocalUser(driverId)) {
            return localData.driverBookings(driverId)
        }
        return callbackFlow {
            trySend(localData.bookingsFlow.value.filter { it.assignedDriverId == driverId })
            val listener = firestore.collection("bookings")
                .whereEqualTo("assignedDriverId", driverId)
                .addSnapshotListener { snapshot, error ->
                    if (error != null) {
                        trySend(localData.bookingsFlow.value.filter { it.assignedDriverId == driverId })
                        return@addSnapshotListener
                    }
                    val bookings = snapshot?.documents?.mapNotNull { doc ->
                        doc.toObject(Booking::class.java)?.copy(id = doc.id)
                    } ?: emptyList()
                    trySend(bookings.ifEmpty {
                        localData.bookingsFlow.value.filter { it.assignedDriverId == driverId }
                    })
                }
            awaitClose { listener.remove() }
        }
    }

    suspend fun updateBookingStatus(bookingId: String, status: TripStatus): Result<Unit> =
        runCatching {
            localData.updateBookingStatus(bookingId, status)
            try {
                firestore.collection("bookings").document(bookingId)
                    .update("status", status.name).await()
            } catch (_: Exception) {
            }
        }
}

class VehicleRepository(
    private val firestore: FirebaseFirestore = FirebaseFirestore.getInstance()
) {
    private val defaultVehicles = listOf(
        Vehicle(id = "v1", registrationNumber = "BIKE-01", category = VehicleCategory.BIKE, capacityKg = 20.0, baseRate = 500.0, perKmRate = 15.0),
        Vehicle(id = "v2", registrationNumber = "VAN-01", category = VehicleCategory.SMALL_VAN, capacityKg = 500.0, baseRate = 2000.0, perKmRate = 25.0),
        Vehicle(id = "v3", registrationNumber = "TRK-01", category = VehicleCategory.MEDIUM_TRUCK, capacityKg = 3000.0, baseRate = 5000.0, perKmRate = 40.0),
        Vehicle(id = "v4", registrationNumber = "HVY-01", category = VehicleCategory.HEAVY_TRUCK, capacityKg = 10000.0, baseRate = 10000.0, perKmRate = 60.0),
        Vehicle(id = "v5", registrationNumber = "REF-01", category = VehicleCategory.REFRIGERATED, capacityKg = 2000.0, baseRate = 8000.0, perKmRate = 55.0)
    )

    fun getAvailableVehicles(category: VehicleCategory? = null): Flow<List<Vehicle>> =
        callbackFlow {
            trySend(defaultVehicles.filter { category == null || it.category == category })
            var query = firestore.collection("vehicles")
                .whereEqualTo("status", VehicleStatus.AVAILABLE.name)
            if (category != null) {
                query = query.whereEqualTo("category", category.name)
            }
            val listener = query.addSnapshotListener { snapshot, error ->
                if (error != null) {
                    trySend(defaultVehicles.filter { category == null || it.category == category })
                    return@addSnapshotListener
                }
                val vehicles = snapshot?.documents?.mapNotNull { doc ->
                    doc.toObject(Vehicle::class.java)?.copy(id = doc.id)
                } ?: emptyList()
                trySend(
                    vehicles.ifEmpty {
                        defaultVehicles.filter { category == null || it.category == category }
                    }
                )
            }
            awaitClose { listener.remove() }
        }

    suspend fun getServices(): Result<List<Service>> = runCatching {
        try {
            firestore.collection("services").get().await()
                .documents.mapNotNull { doc ->
                    doc.toObject(Service::class.java)?.copy(id = doc.id)
                }.ifEmpty { defaultServices() }
        } catch (_: Exception) {
            defaultServices()
        }
    }

    private fun defaultServices() = listOf(
        Service(id = "s1", name = "Loading Help", description = "Helpers at pickup", price = 500.0),
        Service(id = "s2", name = "Packaging", description = "Basic packaging", price = 800.0)
    )
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
    private val firestore: FirebaseFirestore = FirebaseFirestore.getInstance(),
    private val localData: LocalDataStore = SawarriApp.instance.localDataStore
) {
    suspend fun createPayment(payment: Payment): Result<String> = runCatching {
        val id = "pay-${System.currentTimeMillis()}"
        localData.completePayment(
            bookingId = payment.bookingId,
            phase = payment.phase,
            amount = payment.amount,
            userId = payment.userId,
            gatewayRef = payment.gatewayRef
        )
        id
    }

    fun getPaymentsForBooking(bookingId: String): Flow<List<Payment>> =
        localData.paymentsForBooking(bookingId)

    suspend fun completePayment(
        bookingId: String,
        phase: PaymentPhase,
        amount: Double,
        userId: String,
        gatewayRef: String
    ): Result<Unit> = runCatching {
        localData.completePayment(bookingId, phase, amount, userId, gatewayRef)
        if (!SawarriApp.isLocalUser(userId)) {
            try {
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
            } catch (_: Exception) {
            }
        }
    }

    fun getPaymentAmount(quote: Quote, phase: PaymentPhase): Double = when (phase) {
        PaymentPhase.DEPOSIT -> quote.total * 0.10
        PaymentPhase.PICKUP -> (quote.total - quote.total * 0.10) * 0.50
        PaymentPhase.FINAL -> quote.total - (quote.total * 0.10) - ((quote.total - quote.total * 0.10) * 0.50)
    }
}
