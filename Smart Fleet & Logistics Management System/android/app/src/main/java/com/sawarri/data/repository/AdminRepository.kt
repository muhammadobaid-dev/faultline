package com.sawarri.data.repository

import com.google.firebase.Timestamp
import com.google.firebase.firestore.FirebaseFirestore
import com.sawarri.data.model.Booking
import com.sawarri.data.model.TripStatus
import com.sawarri.data.model.UserRole
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.tasks.await
import java.util.Calendar

class AdminRepository(
    private val firestore: FirebaseFirestore = FirebaseFirestore.getInstance()
) {
    fun getPendingBookings(): Flow<List<Booking>> = callbackFlow {
        val listener = firestore.collection("bookings")
            .whereEqualTo("status", TripStatus.PENDING_APPROVAL.name)
            .addSnapshotListener { snapshot, error ->
                if (error != null) { close(error); return@addSnapshotListener }
                val bookings = snapshot?.documents?.mapNotNull { doc ->
                    doc.toObject(Booking::class.java)?.copy(id = doc.id)
                } ?: emptyList()
                trySend(bookings)
            }
        awaitClose { listener.remove() }
    }

    fun getActiveBookings(): Flow<List<Booking>> = callbackFlow {
        val activeStatuses = listOf(
            TripStatus.APPROVED.name,
            TripStatus.DEPOSIT_PAID.name,
            TripStatus.ASSIGNED.name,
            TripStatus.EN_ROUTE.name,
            TripStatus.AT_PICKUP.name,
            TripStatus.IN_TRANSIT.name,
            TripStatus.AT_DESTINATION.name
        )
        val listener = firestore.collection("bookings")
            .whereIn("status", activeStatuses)
            .addSnapshotListener { snapshot, error ->
                if (error != null) { close(error); return@addSnapshotListener }
                val bookings = snapshot?.documents?.mapNotNull { doc ->
                    doc.toObject(Booking::class.java)?.copy(id = doc.id)
                } ?: emptyList()
                trySend(bookings)
            }
        awaitClose { listener.remove() }
    }

    suspend fun approveBooking(bookingId: String): Result<Unit> = runCatching {
        val deadline = Calendar.getInstance().apply { add(Calendar.HOUR, 24) }.time
        val updates = mutableMapOf<String, Any>(
            "status" to TripStatus.APPROVED.name,
            "approvedAt" to Timestamp.now(),
            "depositDeadline" to Timestamp(deadline)
        )
        val drivers = firestore.collection("users")
            .whereEqualTo("role", UserRole.DRIVER.name)
            .limit(1).get().await()
        drivers.documents.firstOrNull()?.id?.let { updates["assignedDriverId"] = it }
        firestore.collection("bookings").document(bookingId).update(updates).await()
    }

    suspend fun rejectBooking(bookingId: String): Result<Unit> = runCatching {
        firestore.collection("bookings").document(bookingId)
            .update("status", TripStatus.REJECTED.name).await()
    }
}
