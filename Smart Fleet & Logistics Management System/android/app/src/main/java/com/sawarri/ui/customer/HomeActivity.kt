package com.sawarri.ui.customer

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.TextView
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.button.MaterialButton
import com.sawarri.R
import com.sawarri.data.model.Booking
import com.sawarri.data.model.TripStatus
import com.sawarri.data.repository.AuthRepository
import com.sawarri.ui.adapter.BookingAdapter
import com.sawarri.ui.adapter.VehicleAdapter
import com.sawarri.ui.settings.SettingsActivity
import com.sawarri.ui.viewmodel.AuthViewModel
import com.sawarri.ui.viewmodel.BookingViewModel
import com.sawarri.util.NavigationHelper
import com.sawarri.util.UiHelper
import kotlinx.coroutines.launch

class HomeActivity : AppCompatActivity() {

    private val authViewModel: AuthViewModel by viewModels()
    private val bookingViewModel: BookingViewModel by viewModels()
    private val authRepository = AuthRepository()
    private lateinit var vehicleAdapter: VehicleAdapter
    private lateinit var bookingAdapter: BookingAdapter
    private var activeTrip: Booking? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)
        setSupportActionBar(findViewById(R.id.toolbar))

        val tvGreeting = findViewById<TextView>(R.id.tvGreeting)
        val tvActiveCount = findViewById<TextView>(R.id.tvActiveBookings)
        val tvTotalSpent = findViewById<TextView>(R.id.tvTotalSpent)
        val rvVehicles = findViewById<RecyclerView>(R.id.rvVehicles)
        val rvBookings = findViewById<RecyclerView>(R.id.rvBookings)
        val tvNoBookings = findViewById<TextView>(R.id.tvNoBookings)
        val btnNewBooking = findViewById<MaterialButton>(R.id.btnNewBooking)

        vehicleAdapter = VehicleAdapter { vehicle ->
            startActivity(Intent(this, BookingActivity::class.java).apply {
                putExtra(BookingActivity.EXTRA_VEHICLE_CATEGORY, vehicle.category.name)
            })
        }
        bookingAdapter = BookingAdapter(onItemClick = { booking -> openBooking(booking) })

        rvVehicles.layoutManager = LinearLayoutManager(this)
        rvVehicles.adapter = vehicleAdapter
        rvBookings.layoutManager = LinearLayoutManager(this)
        rvBookings.adapter = bookingAdapter

        btnNewBooking.setOnClickListener {
            startActivity(Intent(this, BookingActivity::class.java))
        }
        findViewById<View>(R.id.cardBookCta).setOnClickListener {
            startActivity(Intent(this, BookingActivity::class.java))
        }
        findViewById<MaterialButton>(R.id.btnActiveTripAction).setOnClickListener {
            activeTrip?.let { openBooking(it) }
        }
        findViewById<View>(R.id.cardActiveTrip).setOnClickListener {
            activeTrip?.let { openBooking(it) }
        }

        lifecycleScope.launch {
            val userId = authRepository.currentUserId ?: return@launch
            authRepository.getUserProfile(userId).onSuccess { user ->
                tvGreeting.text = getString(R.string.hello_user, user.name)
            }
            bookingViewModel.loadVehicles()
            bookingViewModel.loadCustomerBookings(userId)
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                bookingViewModel.vehicles.collect { vehicleAdapter.submitList(it) }
            }
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                bookingViewModel.bookings.collect { bookings ->
                    bookingAdapter.submitList(bookings)
                    tvNoBookings.visibility = if (bookings.isEmpty()) View.VISIBLE else View.GONE

                    val activeList = bookings.filter { UiHelper.isActiveTrip(it.status) }
                    val spent = bookings
                        .filter {
                            it.status in listOf(
                                TripStatus.DEPOSIT_PAID, TripStatus.DELIVERED,
                                TripStatus.CLOSED, TripStatus.IN_TRANSIT,
                                TripStatus.AT_PICKUP, TripStatus.AT_DESTINATION
                            )
                        }
                        .sumOf { it.quote.total * 0.1 } // approx paid so far for demo stats

                    tvActiveCount.text = activeList.size.toString()
                    tvTotalSpent.text = getString(
                        R.string.amount_pkr,
                        String.format("%,d", spent.toInt())
                    )
                    bindActiveTrip(activeList.firstOrNull())
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        authRepository.currentUserId?.let { bookingViewModel.loadCustomerBookings(it) }
    }

    private fun bindActiveTrip(booking: Booking?) {
        activeTrip = booking
        val section = findViewById<View>(R.id.sectionActiveTrip)
        if (booking == null) {
            section.visibility = View.GONE
            return
        }
        section.visibility = View.VISIBLE
        findViewById<TextView>(R.id.tvActiveTripId).text =
            getString(R.string.booking_id, booking.id.take(8).uppercase())
        findViewById<TextView>(R.id.tvActiveTripRoute).text =
            "${booking.pickup.address}  →  ${booking.dropoff.address}"
        findViewById<TextView>(R.id.tvActiveTripMessage).text =
            UiHelper.customerOrderMessage(booking.status)

        val statusTv = findViewById<TextView>(R.id.tvActiveTripStatus)
        statusTv.text = UiHelper.statusLabel(booking.status)
        statusTv.setBackgroundResource(R.drawable.bg_chip_default)

        val btn = findViewById<MaterialButton>(R.id.btnActiveTripAction)
        btn.text = when (booking.status) {
            TripStatus.APPROVED, TripStatus.AT_PICKUP, TripStatus.AT_DESTINATION ->
                getString(R.string.pay_now_action)
            TripStatus.ASSIGNED, TripStatus.EN_ROUTE, TripStatus.IN_TRANSIT ->
                getString(R.string.track_trip_action)
            else -> getString(R.string.view_trip_details)
        }
    }

    private fun openBooking(booking: Booking) {
        val trackable = listOf(
            TripStatus.ASSIGNED, TripStatus.EN_ROUTE,
            TripStatus.IN_TRANSIT, TripStatus.AT_PICKUP
        )
        if (booking.status in trackable) {
            startActivity(Intent(this, TrackingActivity::class.java).apply {
                putExtra(TrackingActivity.EXTRA_BOOKING_ID, booking.id)
            })
        } else {
            startActivity(Intent(this, PaymentActivity::class.java).apply {
                putExtra(PaymentActivity.EXTRA_BOOKING_ID, booking.id)
            })
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.menu_main, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean = when (item.itemId) {
        R.id.action_settings -> {
            startActivity(Intent(this, SettingsActivity::class.java)); true
        }
        R.id.action_logout -> {
            authViewModel.logout(); NavigationHelper.goToLogin(this); finish(); true
        }
        else -> super.onOptionsItemSelected(item)
    }
}
