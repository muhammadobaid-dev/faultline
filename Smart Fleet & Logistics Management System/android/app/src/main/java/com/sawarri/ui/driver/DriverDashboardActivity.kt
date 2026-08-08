package com.sawarri.ui.driver

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.core.content.ContextCompat
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.sawarri.R
import com.sawarri.data.model.Booking
import com.sawarri.data.model.TripStatus
import com.sawarri.data.repository.AuthRepository
import com.sawarri.data.repository.BookingRepository
import com.sawarri.service.LocationTrackingService
import com.sawarri.ui.adapter.BookingAdapter
import com.sawarri.ui.customer.TrackingActivity
import com.sawarri.ui.viewmodel.AuthViewModel
import com.sawarri.ui.viewmodel.BookingViewModel
import com.sawarri.ui.settings.SettingsActivity
import com.sawarri.util.NavigationHelper
import kotlinx.coroutines.launch

class DriverDashboardActivity : AppCompatActivity() {

    private val authViewModel: AuthViewModel by viewModels()
    private val bookingViewModel: BookingViewModel by viewModels()
    private val authRepository = AuthRepository()
    private val bookingRepository = BookingRepository()
    private lateinit var taskAdapter: BookingAdapter
    private var activeGpsBookingId: String? = null

    private val locationPermission = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { grants ->
        if (grants.values.any { it }) {
            activeGpsBookingId?.let { startGpsService(it) }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_driver_dashboard)

        setSupportActionBar(findViewById(R.id.toolbar))

        val tvDriverName = findViewById<TextView>(R.id.tvDriverName)
        val tvGpsStatus = findViewById<TextView>(R.id.tvGpsStatus)
        val rvTasks = findViewById<RecyclerView>(R.id.rvTasks)
        val tvNoTasks = findViewById<TextView>(R.id.tvNoTasks)

        taskAdapter = BookingAdapter(onItemClick = { booking ->
            showDriverOptions(booking, tvGpsStatus)
        })

        rvTasks.layoutManager = LinearLayoutManager(this)
        rvTasks.adapter = taskAdapter

        lifecycleScope.launch {
            val userId = authRepository.currentUserId ?: return@launch
            authRepository.getUserProfile(userId).onSuccess { user ->
                tvDriverName.text = getString(R.string.hello_user, user.name)
            }
            bookingViewModel.loadDriverBookings(userId)
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                bookingViewModel.bookings.collect { bookings ->
                    taskAdapter.submitList(bookings)
                    tvNoTasks.visibility = if (bookings.isEmpty()) View.VISIBLE else View.GONE
                }
            }
        }
    }

    private fun showDriverOptions(booking: Booking, tvGpsStatus: TextView) {
        val statuses = arrayOf(
            "Start GPS Sharing",
            "Mark: En Route",
            "Mark: At Pickup",
            "Mark: In Transit",
            "Mark: At Destination",
            "Open Live Map"
        )
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.booking_id, booking.id.take(8)))
            .setItems(statuses) { _, which ->
                when (which) {
                    0 -> requestGpsAndStart(booking.id, tvGpsStatus)
                    1 -> updateStatus(booking.id, TripStatus.EN_ROUTE)
                    2 -> updateStatus(booking.id, TripStatus.AT_PICKUP)
                    3 -> updateStatus(booking.id, TripStatus.IN_TRANSIT)
                    4 -> updateStatus(booking.id, TripStatus.AT_DESTINATION)
                    5 -> startActivity(Intent(this, TrackingActivity::class.java).apply {
                        putExtra(TrackingActivity.EXTRA_BOOKING_ID, booking.id)
                    })
                }
            }
            .show()
    }

    private fun requestGpsAndStart(bookingId: String, tvGpsStatus: TextView) {
        activeGpsBookingId = bookingId
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
            == PackageManager.PERMISSION_GRANTED
        ) {
            startGpsService(bookingId)
            tvGpsStatus.text = getString(R.string.gps_active)
            tvGpsStatus.setBackgroundResource(R.drawable.bg_chip_transit)
            tvGpsStatus.setTextColor(ContextCompat.getColor(this, R.color.teal))
        } else {
            locationPermission.launch(
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
            )
        }
    }

    private fun startGpsService(bookingId: String) {
        val driverId = authRepository.currentUserId ?: return
        val intent = Intent(this, LocationTrackingService::class.java).apply {
            putExtra(LocationTrackingService.EXTRA_BOOKING_ID, bookingId)
            putExtra(LocationTrackingService.EXTRA_DRIVER_ID, driverId)
        }
        ContextCompat.startForegroundService(this, intent)
        Toast.makeText(this, getString(R.string.gps_active), Toast.LENGTH_SHORT).show()
    }

    private fun updateStatus(bookingId: String, status: TripStatus) {
        lifecycleScope.launch {
            bookingRepository.updateBookingStatus(bookingId, status)
                .onSuccess { Toast.makeText(this@DriverDashboardActivity, "Status: ${status.name}", Toast.LENGTH_SHORT).show() }
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.menu_main, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean = when (item.itemId) {
        R.id.action_settings -> { startActivity(Intent(this, SettingsActivity::class.java)); true }
        R.id.action_logout -> {
            stopService(Intent(this, com.sawarri.service.LocationTrackingService::class.java))
            authViewModel.logout(); NavigationHelper.goToLogin(this); finish(); true
        }
        else -> super.onOptionsItemSelected(item)
    }
}
