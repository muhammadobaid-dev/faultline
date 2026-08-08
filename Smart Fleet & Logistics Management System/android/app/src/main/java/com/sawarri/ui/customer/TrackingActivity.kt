package com.sawarri.ui.customer

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Paint
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.sawarri.R
import com.sawarri.ui.settings.SettingsActivity
import com.sawarri.ui.viewmodel.AuthViewModel
import com.sawarri.ui.viewmodel.TrackingViewModel
import com.sawarri.util.NavigationHelper
import com.sawarri.util.QuotingEngine
import kotlinx.coroutines.launch
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polyline

class TrackingActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_BOOKING_ID = "booking_id"
    }

    private val trackingViewModel: TrackingViewModel by viewModels()
    private val authViewModel: AuthViewModel by viewModels()
    private lateinit var mapView: MapView
    private var driverMarker: Marker? = null
    private var routeDrawn = false

    private val locationPermission = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { /* customer view works without device GPS */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_tracking)

        val bookingId = intent.getStringExtra(EXTRA_BOOKING_ID)
            ?: run { finish(); return }

        setSupportActionBar(findViewById(R.id.toolbar))
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        findViewById<androidx.appcompat.widget.Toolbar>(R.id.toolbar)
            .setNavigationOnClickListener { finish() }

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED
        ) {
            locationPermission.launch(
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
            )
        }

        mapView = findViewById(R.id.mapView)
        mapView.setMultiTouchControls(true)
        mapView.controller.setZoom(11.0)
        mapView.controller.setCenter(GeoPoint(31.5204, 74.3587)) // Lahore default

        trackingViewModel.loadTracking(bookingId)

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                trackingViewModel.booking.collect { booking ->
                    booking?.let {
                        findViewById<TextView>(R.id.tvTripStatus).text =
                            getString(R.string.trip_status, it.status.name)
                        findViewById<TextView>(R.id.tvRoute).text =
                            "${it.pickup.address} → ${it.dropoff.address}"

                        if (!routeDrawn) {
                            drawRoute(
                                GeoPoint(it.pickup.lat, it.pickup.lng),
                                GeoPoint(it.dropoff.lat, it.dropoff.lng)
                            )
                            routeDrawn = true
                        }
                    }
                }
            }
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                trackingViewModel.trackingData.collect { data ->
                    val booking = trackingViewModel.booking.value ?: return@collect
                    val location = data?.currentLocation

                    if (location != null) {
                        val driverPoint = GeoPoint(location.latitude, location.longitude)
                        if (driverMarker == null) {
                            driverMarker = Marker(mapView).apply {
                                position = driverPoint
                                title = "Driver"
                                setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                            }
                            mapView.overlays.add(driverMarker)
                        } else {
                            driverMarker?.position = driverPoint
                        }
                        mapView.controller.animateTo(driverPoint)

                        val dist = QuotingEngine.haversineKm(
                            location.latitude, location.longitude,
                            booking.dropoff.lat, booking.dropoff.lng
                        )
                        findViewById<TextView>(R.id.tvLocationInfo).text =
                            "Driver: ${String.format("%.4f", location.latitude)}, ${String.format("%.4f", location.longitude)}"
                        findViewById<TextView>(R.id.tvDistance).text =
                            getString(R.string.eta_label, String.format("%.1f", dist))
                    } else {
                        findViewById<TextView>(R.id.tvLocationInfo).text =
                            getString(R.string.waiting_location)
                    }
                    mapView.invalidate()
                }
            }
        }
    }

    private fun drawRoute(pickup: GeoPoint, dropoff: GeoPoint) {
        mapView.overlays.add(Marker(mapView).apply {
            position = pickup
            title = "Pickup"
            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
        })
        mapView.overlays.add(Marker(mapView).apply {
            position = dropoff
            title = "Drop-off"
            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
        })

        val routeLine = Polyline().apply {
            setPoints(listOf(pickup, dropoff))
            outlinePaint.color = 0xFF1565C0.toInt()
            outlinePaint.strokeWidth = 8f
            outlinePaint.style = Paint.Style.STROKE
        }
        mapView.overlays.add(routeLine)
        mapView.invalidate()
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

    override fun onResume() {
        super.onResume()
        mapView.onResume()
    }

    override fun onPause() {
        super.onPause()
        mapView.onPause()
    }
}
