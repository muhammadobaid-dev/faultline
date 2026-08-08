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
import com.sawarri.data.model.TripStatus
import com.sawarri.data.repository.AuthRepository
import com.sawarri.ui.adapter.BookingAdapter
import com.sawarri.ui.adapter.VehicleAdapter
import com.sawarri.ui.settings.SettingsActivity
import com.sawarri.ui.viewmodel.AuthViewModel
import com.sawarri.ui.viewmodel.BookingViewModel
import com.sawarri.util.NavigationHelper
import kotlinx.coroutines.launch

class HomeActivity : AppCompatActivity() {

    private val authViewModel: AuthViewModel by viewModels()
    private val bookingViewModel: BookingViewModel by viewModels()
    private val authRepository = AuthRepository()
    private lateinit var vehicleAdapter: VehicleAdapter
    private lateinit var bookingAdapter: BookingAdapter

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
        bookingAdapter = BookingAdapter(onItemClick = { booking ->
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
        })

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

                    val active = bookings.count {
                        it.status !in listOf(TripStatus.CLOSED, TripStatus.REJECTED,
                            TripStatus.CANCELLED, TripStatus.AUTO_CANCELLED)
                    }
                    val spent = bookings.filter {
                        it.status in listOf(TripStatus.DEPOSIT_PAID, TripStatus.CLOSED, TripStatus.DELIVERED)
                    }.sumOf { it.quote.total }

                    tvActiveCount.text = active.toString()
                    tvTotalSpent.text = getString(R.string.amount_pkr, String.format("%,d", spent.toInt()))
                }
            }
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.menu_main, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean = when (item.itemId) {
        R.id.action_settings -> { startActivity(Intent(this, SettingsActivity::class.java)); true }
        R.id.action_logout -> { authViewModel.logout(); NavigationHelper.goToLogin(this); finish(); true }
        else -> super.onOptionsItemSelected(item)
    }
}
