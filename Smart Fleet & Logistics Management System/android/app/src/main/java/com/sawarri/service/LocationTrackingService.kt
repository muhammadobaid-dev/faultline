package com.sawarri.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import com.google.android.gms.location.*
import com.google.firebase.firestore.GeoPoint
import com.sawarri.R
import com.sawarri.data.repository.TrackingRepository
import kotlinx.coroutines.*

class LocationTrackingService : Service() {

    companion object {
        const val EXTRA_BOOKING_ID = "booking_id"
        const val EXTRA_DRIVER_ID = "driver_id"
        private const val CHANNEL_ID = "gps_tracking"
        private const val NOTIFICATION_ID = 1001
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val trackingRepository = TrackingRepository()
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var locationCallback: LocationCallback
    private var bookingId: String = ""
    private var driverId: String = ""

    override fun onCreate() {
        super.onCreate()
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        bookingId = intent?.getStringExtra(EXTRA_BOOKING_ID) ?: ""
        driverId = intent?.getStringExtra(EXTRA_DRIVER_ID) ?: ""

        val notification = buildNotification()
        startForeground(NOTIFICATION_ID, notification)

        val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 10_000L)
            .setMinUpdateIntervalMillis(5_000L)
            .build()

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                val location = result.lastLocation ?: return
                scope.launch {
                    trackingRepository.updateLocation(
                        bookingId, driverId,
                        GeoPoint(location.latitude, location.longitude)
                    )
                }
            }
        }

        try {
            fusedLocationClient.requestLocationUpdates(
                request, locationCallback, Looper.getMainLooper()
            )
        } catch (_: SecurityException) { }

        return START_STICKY
    }

    override fun onDestroy() {
        fusedLocationClient.removeLocationUpdates(locationCallback)
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun buildNotification(): Notification =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.gps_sharing))
            .setContentText(getString(R.string.gps_active))
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true)
            .build()

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID, "GPS Tracking", NotificationManager.IMPORTANCE_LOW
        )
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }
}
