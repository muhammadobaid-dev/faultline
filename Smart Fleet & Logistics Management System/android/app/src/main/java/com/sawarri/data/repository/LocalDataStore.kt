package com.sawarri.data.repository

import android.content.Context
import com.google.firebase.Timestamp
import com.sawarri.data.model.Booking
import com.sawarri.data.model.CargoDetails
import com.sawarri.data.model.Location
import com.sawarri.data.model.Payment
import com.sawarri.data.model.PaymentPhase
import com.sawarri.data.model.PaymentStatus
import com.sawarri.data.model.Quote
import com.sawarri.data.model.TripStatus
import com.sawarri.data.model.Urgency
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/**
 * SharedPreferences-backed bookings + payments so the full demo flow works
 * when Firebase Auth/Firestore is unreachable (TECNO / offline).
 */
class LocalDataStore(context: Context) {

    private val prefs = context.applicationContext
        .getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    private val _bookings = MutableStateFlow(loadBookings())
    private val _payments = MutableStateFlow(loadPayments())

    val bookingsFlow = _bookings.asStateFlow()
    val paymentsFlow = _payments.asStateFlow()

    fun createBooking(booking: Booking): String {
        val id = booking.id.ifBlank { "bk-${UUID.randomUUID().toString().take(8)}" }
        val saved = booking.copy(
            id = id,
            status = TripStatus.PENDING_APPROVAL,
            createdAt = booking.createdAt ?: Timestamp.now()
        )
        val list = _bookings.value.toMutableList()
        list.removeAll { it.id == id }
        list.add(0, saved)
        persistBookings(list)
        return id
    }

    fun getBooking(bookingId: String): Booking? =
        _bookings.value.firstOrNull { it.id == bookingId }

    fun updateBookingStatus(bookingId: String, status: TripStatus) {
        val list = _bookings.value.map {
            if (it.id == bookingId) it.copy(status = status) else it
        }
        persistBookings(list)
    }

    fun approveBooking(bookingId: String, driverId: String?): Booking? {
        val deadline = Timestamp(java.util.Date(System.currentTimeMillis() + 24 * 60 * 60 * 1000L))
        var updated: Booking? = null
        val list = _bookings.value.map { b ->
            if (b.id == bookingId) {
                b.copy(
                    status = TripStatus.APPROVED,
                    assignedDriverId = driverId ?: b.assignedDriverId,
                    approvedAt = Timestamp.now(),
                    depositDeadline = deadline
                ).also { updated = it }
            } else b
        }
        persistBookings(list)
        return updated
    }

    fun rejectBooking(bookingId: String) {
        updateBookingStatus(bookingId, TripStatus.REJECTED)
    }

    fun customerBookings(customerId: String): Flow<List<Booking>> =
        _bookings.map { list -> list.filter { it.customerId == customerId } }

    fun driverBookings(driverId: String): Flow<List<Booking>> =
        _bookings.map { list ->
            list.filter {
                it.assignedDriverId == driverId &&
                    it.status != TripStatus.REJECTED &&
                    it.status != TripStatus.CANCELLED
            }
        }

    fun pendingBookings(): Flow<List<Booking>> =
        _bookings.map { list -> list.filter { it.status == TripStatus.PENDING_APPROVAL } }

    fun activeBookings(): Flow<List<Booking>> {
        val active = setOf(
            TripStatus.APPROVED, TripStatus.DEPOSIT_PAID, TripStatus.ASSIGNED,
            TripStatus.EN_ROUTE, TripStatus.AT_PICKUP, TripStatus.IN_TRANSIT,
            TripStatus.AT_DESTINATION
        )
        return _bookings.map { list -> list.filter { it.status in active } }
    }

    fun paymentsForBooking(bookingId: String): Flow<List<Payment>> =
        _payments.map { list -> list.filter { it.bookingId == bookingId } }

    fun completePayment(
        bookingId: String,
        phase: PaymentPhase,
        amount: Double,
        userId: String,
        gatewayRef: String
    ) {
        val payment = Payment(
            id = "pay-${UUID.randomUUID().toString().take(8)}",
            bookingId = bookingId,
            userId = userId,
            phase = phase,
            amount = amount,
            status = PaymentStatus.COMPLETED,
            gatewayRef = gatewayRef,
            paidAt = Timestamp.now(),
            createdAt = Timestamp.now()
        )
        val pays = _payments.value.toMutableList()
        pays.add(0, payment)
        persistPayments(pays)

        val newStatus = when (phase) {
            PaymentPhase.DEPOSIT -> TripStatus.DEPOSIT_PAID
            PaymentPhase.PICKUP -> TripStatus.IN_TRANSIT
            PaymentPhase.FINAL -> TripStatus.DELIVERED
        }
        updateBookingStatus(bookingId, newStatus)
    }

    private fun persistBookings(list: List<Booking>) {
        _bookings.value = list
        val arr = JSONArray()
        list.forEach { arr.put(bookingToJson(it)) }
        prefs.edit().putString(KEY_BOOKINGS, arr.toString()).apply()
    }

    private fun persistPayments(list: List<Payment>) {
        _payments.value = list
        val arr = JSONArray()
        list.forEach { p ->
            arr.put(
                JSONObject()
                    .put("id", p.id)
                    .put("bookingId", p.bookingId)
                    .put("userId", p.userId)
                    .put("phase", p.phase.name)
                    .put("amount", p.amount)
                    .put("status", p.status.name)
                    .put("gatewayRef", p.gatewayRef)
            )
        }
        prefs.edit().putString(KEY_PAYMENTS, arr.toString()).apply()
    }

    private fun loadBookings(): List<Booking> {
        val raw = prefs.getString(KEY_BOOKINGS, "[]") ?: "[]"
        val arr = JSONArray(raw)
        val out = mutableListOf<Booking>()
        for (i in 0 until arr.length()) {
            runCatching { out.add(bookingFromJson(arr.getJSONObject(i))) }
        }
        return out
    }

    private fun loadPayments(): List<Payment> {
        val raw = prefs.getString(KEY_PAYMENTS, "[]") ?: "[]"
        val arr = JSONArray(raw)
        val out = mutableListOf<Payment>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            out.add(
                Payment(
                    id = o.optString("id"),
                    bookingId = o.optString("bookingId"),
                    userId = o.optString("userId"),
                    phase = runCatching { PaymentPhase.valueOf(o.optString("phase")) }
                        .getOrDefault(PaymentPhase.DEPOSIT),
                    amount = o.optDouble("amount"),
                    status = runCatching { PaymentStatus.valueOf(o.optString("status")) }
                        .getOrDefault(PaymentStatus.COMPLETED),
                    gatewayRef = o.optString("gatewayRef")
                )
            )
        }
        return out
    }

    private fun bookingToJson(b: Booking): JSONObject = JSONObject()
        .put("id", b.id)
        .put("customerId", b.customerId)
        .put("status", b.status.name)
        .put("pickup", b.pickup.address)
        .put("dropoff", b.dropoff.address)
        .put("cargoType", b.cargo.type)
        .put("length", b.cargo.length)
        .put("width", b.cargo.width)
        .put("height", b.cargo.height)
        .put("weight", b.cargo.weight)
        .put("urgency", b.urgency.name)
        .put("quoteTotal", b.quote.total)
        .put("quoteBase", b.quote.baseRate)
        .put("quoteDistance", b.quote.distanceCost)
        .put("quoteWeight", b.quote.weightCost)
        .put("quoteVolume", b.quote.volumeCost)
        .put("quoteService", b.quote.serviceCost)
        .put("quoteUrgency", b.quote.urgencyMultiplier)
        .put("assignedDriverId", b.assignedDriverId ?: "")

    private fun bookingFromJson(o: JSONObject): Booking = Booking(
        id = o.optString("id"),
        customerId = o.optString("customerId"),
        status = runCatching { TripStatus.valueOf(o.optString("status")) }
            .getOrDefault(TripStatus.PENDING_APPROVAL),
        pickup = Location(address = o.optString("pickup")),
        dropoff = Location(address = o.optString("dropoff")),
        cargo = CargoDetails(
            type = o.optString("cargoType"),
            length = o.optDouble("length"),
            width = o.optDouble("width"),
            height = o.optDouble("height"),
            weight = o.optDouble("weight")
        ),
        urgency = runCatching { Urgency.valueOf(o.optString("urgency", "STANDARD")) }
            .getOrDefault(Urgency.STANDARD),
        quote = Quote(
            baseRate = o.optDouble("quoteBase"),
            distanceCost = o.optDouble("quoteDistance"),
            weightCost = o.optDouble("quoteWeight"),
            volumeCost = o.optDouble("quoteVolume"),
            serviceCost = o.optDouble("quoteService"),
            urgencyMultiplier = o.optDouble("quoteUrgency", 1.0),
            total = o.optDouble("quoteTotal")
        ),
        assignedDriverId = o.optString("assignedDriverId").ifBlank { null },
        createdAt = Timestamp.now()
    )

    companion object {
        private const val PREFS = "sawarri_local_data"
        private const val KEY_BOOKINGS = "bookings"
        private const val KEY_PAYMENTS = "payments"
    }
}
