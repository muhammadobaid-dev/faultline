package com.sawarri.ui.admin

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.TextView
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.sawarri.R
import com.sawarri.ui.adapter.BookingAdapter
import com.sawarri.ui.viewmodel.AdminViewModel
import com.sawarri.ui.viewmodel.AuthViewModel
import com.sawarri.ui.settings.SettingsActivity
import com.sawarri.util.NavigationHelper
import kotlinx.coroutines.launch

class AdminDashboardActivity : AppCompatActivity() {

    private val adminViewModel: AdminViewModel by viewModels()
    private val authViewModel: AuthViewModel by viewModels()
    private lateinit var pendingAdapter: BookingAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_admin_dashboard)

        setSupportActionBar(findViewById(R.id.toolbar))

        val tvPendingCount = findViewById<TextView>(R.id.tvPendingCount)
        val tvActiveCount = findViewById<TextView>(R.id.tvActiveCount)
        val rvPending = findViewById<RecyclerView>(R.id.rvPending)
        val tvNoPending = findViewById<TextView>(R.id.tvNoPending)

        pendingAdapter = BookingAdapter(
            showActions = true,
            onApprove = { booking -> adminViewModel.approveBooking(booking.id) },
            onReject = { booking -> adminViewModel.rejectBooking(booking.id) }
        )

        rvPending.layoutManager = LinearLayoutManager(this)
        rvPending.adapter = pendingAdapter

        adminViewModel.loadDashboard()

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                adminViewModel.adminMessage.collect { msg ->
                    if (msg != null) {
                        Toast.makeText(this@AdminDashboardActivity, msg, Toast.LENGTH_LONG).show()
                        adminViewModel.consumeMessage()
                    }
                }
            }
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                adminViewModel.pendingBookings.collect { bookings ->
                    pendingAdapter.submitList(bookings)
                    tvPendingCount.text = bookings.size.toString()
                    tvNoPending.visibility = if (bookings.isEmpty()) View.VISIBLE else View.GONE
                }
            }
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                adminViewModel.activeBookings.collect { bookings ->
                    tvActiveCount.text = bookings.size.toString()
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
