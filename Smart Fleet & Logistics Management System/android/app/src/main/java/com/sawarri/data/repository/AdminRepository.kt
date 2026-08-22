package com.sawarri.data.repository

import com.google.firebase.Timestamp
import com.google.firebase.firestore.FirebaseFirestore
import com.sawarri.SawarriApp
import com.sawarri.data.model.Booking
import com.sawarri.data.model.TripStatus
import com.sawarri.data.model.UserRole
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.tasks.await
import java.util.Calendar

class AdminRepository(
    private val firestore: FirebaseFirestore = FirebaseFirestore.getInstance(),
    private val localData: LocalDataStore = SawarriApp.instance.localDataStore,
    private val localAuth: LocalAuthStore = SawarriApp.instance.localAuthStore
) {
    fun getPendingBookings(): Flow<List<Booking>> = localData.pendingBookings()

    fun getActiveBookings(): Flow<List<Booking>> = localData.activeBookings()

    suspend fun approveBooking(bookingId: String): Result<Unit> = runCatching {
        val driverId = localAuth.getUsersByRole(UserRole.DRIVER).firstOrNull()?.id
            ?: try {
                firestore.collection("users")
                    .whereEqualTo("role", UserRole.DRIVER.name)
                    .limit(1).get().await()
                    .documents.firstOrNull()?.id
            } catch (_: Exception) {
                null
            }

        require(driverId != null) {
            "No driver registered. Pehle Driver role se account banao, phir approve karo."
        }

        localData.approveBooking(bookingId, driverId)

        try {
            val deadline = Calendar.getInstance().apply { add(Calendar.HOUR, 24) }.time
            firestore.collection("bookings").document(bookingId).update(
                mapOf(
                    "status" to TripStatus.APPROVED.name,
                    "approvedAt" to Timestamp.now(),
                    "depositDeadline" to Timestamp(deadline),
                    "assignedDriverId" to driverId
                )
            ).await()
        } catch (_: Exception) {
        }
    }

    suspend fun rejectBooking(bookingId: String): Result<Unit> = runCatching {
        localData.rejectBooking(bookingId)
        try {
            firestore.collection("bookings").document(bookingId)
                .update("status", TripStatus.REJECTED.name).await()
        } catch (_: Exception) {
        }
    }
}
