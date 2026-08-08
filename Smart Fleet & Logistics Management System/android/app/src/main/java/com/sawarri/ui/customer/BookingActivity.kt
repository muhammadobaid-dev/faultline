package com.sawarri.ui.customer

import android.location.Geocoder
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.google.android.material.button.MaterialButton
import com.google.android.material.card.MaterialCardView
import com.google.android.material.chip.Chip
import com.sawarri.R
import com.sawarri.data.model.*
import com.sawarri.data.repository.AuthRepository
import com.sawarri.ui.viewmodel.BookingState
import com.sawarri.ui.viewmodel.BookingViewModel
import com.sawarri.util.QuotingEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.Locale

class BookingActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_VEHICLE_CATEGORY = "vehicle_category"
    }

    private val bookingViewModel: BookingViewModel by viewModels()
    private val authRepository = AuthRepository()

    private var currentQuote: Quote? = null
    private val serviceCheckboxes = mutableListOf<Pair<CheckBox, Service>>()
    private lateinit var categoryValues: Array<String>

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_booking)

        findViewById<androidx.appcompat.widget.Toolbar>(R.id.toolbar).apply {
            setNavigationOnClickListener { finish() }
        }

        categoryValues = resources.getStringArray(R.array.vehicle_category_values)
        val spinnerVehicle = findViewById<Spinner>(R.id.spinnerVehicle)
        spinnerVehicle.adapter = ArrayAdapter(
            this, android.R.layout.simple_spinner_dropdown_item,
            resources.getStringArray(R.array.vehicle_categories)
        )

        intent.getStringExtra(EXTRA_VEHICLE_CATEGORY)?.let { cat ->
            val idx = categoryValues.indexOf(cat.uppercase())
            if (idx >= 0) spinnerVehicle.setSelection(idx)
        }

        val layoutServices = findViewById<LinearLayout>(R.id.layoutServices)
        val btnGetQuote = findViewById<MaterialButton>(R.id.btnGetQuote)
        val btnSubmit = findViewById<MaterialButton>(R.id.btnSubmit)
        val layoutQuote = findViewById<MaterialCardView>(R.id.layoutQuote)
        val progressBar = findViewById<ProgressBar>(R.id.progressBar)
        val chipExpress = findViewById<Chip>(R.id.chipExpress)

        bookingViewModel.loadServices()
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                bookingViewModel.services.collect { services ->
                    layoutServices.removeAllViews()
                    serviceCheckboxes.clear()
                    services.forEach { service ->
                        val cb = CheckBox(this@BookingActivity).apply {
                            text = "${service.name} — ₨${service.price.toInt()}"
                            tag = service.id
                        }
                        serviceCheckboxes.add(cb to service)
                        layoutServices.addView(cb)
                    }
                }
            }
        }

        btnGetQuote.setOnClickListener {
            val pickup = findViewById<EditText>(R.id.etPickup).text.toString().trim()
            val dropoff = findViewById<EditText>(R.id.etDropoff).text.toString().trim()
            val cargoType = findViewById<EditText>(R.id.etCargoType).text.toString().trim()
            val weight = findViewById<EditText>(R.id.etWeight).text.toString().toDoubleOrNull() ?: 0.0
            val length = findViewById<EditText>(R.id.etLength).text.toString().toDoubleOrNull() ?: 1.0
            val width = findViewById<EditText>(R.id.etWidth).text.toString().toDoubleOrNull() ?: 1.0
            val height = findViewById<EditText>(R.id.etHeight).text.toString().toDoubleOrNull() ?: 1.0

            if (pickup.isEmpty() || dropoff.isEmpty() || cargoType.isEmpty() || weight <= 0) {
                Toast.makeText(this, R.string.fill_required, Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            lifecycleScope.launch {
                val (pickupLat, pickupLng) = geocode(pickup)
                val (dropoffLat, dropoffLng) = geocode(dropoff)
                val distance = QuotingEngine.haversineKm(pickupLat, pickupLng, dropoffLat, dropoffLng)
                    .coerceAtLeast(5.0)

                val category = categoryValues[spinnerVehicle.selectedItemPosition]
                val urgency = if (chipExpress.isChecked) "express" else "standard"
                val selectedIds = serviceCheckboxes.filter { it.first.isChecked }.map { it.second.id }

                bookingViewModel.calculateQuote(
                    category, distance, weight, length, width, height,
                    selectedIds, urgency,
                    bookingViewModel.services.value
                )
            }
        }

        btnSubmit.setOnClickListener {
            val quote = currentQuote ?: return@setOnClickListener
            val userId = authRepository.currentUserId ?: return@setOnClickListener

            lifecycleScope.launch {
                val pickup = findViewById<EditText>(R.id.etPickup).text.toString().trim()
                val dropoff = findViewById<EditText>(R.id.etDropoff).text.toString().trim()
                val (pickupLat, pickupLng) = geocode(pickup)
                val (dropoffLat, dropoffLng) = geocode(dropoff)

                val booking = Booking(
                    customerId = userId,
                    pickup = Location(pickup, pickupLat, pickupLng),
                    dropoff = Location(dropoff, dropoffLat, dropoffLng),
                    cargo = CargoDetails(
                        type = findViewById<EditText>(R.id.etCargoType).text.toString().trim(),
                        length = findViewById<EditText>(R.id.etLength).text.toString().toDoubleOrNull() ?: 1.0,
                        width = findViewById<EditText>(R.id.etWidth).text.toString().toDoubleOrNull() ?: 1.0,
                        height = findViewById<EditText>(R.id.etHeight).text.toString().toDoubleOrNull() ?: 1.0,
                        weight = findViewById<EditText>(R.id.etWeight).text.toString().toDoubleOrNull() ?: 0.0
                    ),
                    selectedServices = serviceCheckboxes.filter { it.first.isChecked }.map { it.second.id },
                    urgency = if (chipExpress.isChecked) Urgency.EXPRESS else Urgency.STANDARD,
                    quote = quote
                )
                bookingViewModel.submitBooking(booking)
            }
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                bookingViewModel.bookingState.collect { state ->
                    when (state) {
                        is BookingState.Loading -> progressBar.visibility = View.VISIBLE
                        is BookingState.QuoteReady -> {
                            progressBar.visibility = View.GONE
                            currentQuote = state.quote
                            showQuote(state.quote)
                            layoutQuote.visibility = View.VISIBLE
                            btnSubmit.visibility = View.VISIBLE
                        }
                        is BookingState.Submitted -> {
                            progressBar.visibility = View.GONE
                            Toast.makeText(this@BookingActivity, R.string.booking_submitted, Toast.LENGTH_LONG).show()
                            finish()
                        }
                        is BookingState.Error -> {
                            progressBar.visibility = View.GONE
                            Toast.makeText(this@BookingActivity, state.message, Toast.LENGTH_LONG).show()
                        }
                        else -> progressBar.visibility = View.GONE
                    }
                }
            }
        }
    }

    private fun showQuote(quote: Quote) {
        findViewById<TextView>(R.id.tvQuoteBreakdown).text = buildString {
            append("${getString(R.string.base_rate)}: ₨${quote.baseRate.toInt()}\n")
            append("${getString(R.string.distance_cost)}: ₨${quote.distanceCost.toInt()}\n")
            append("${getString(R.string.weight_cost)}: ₨${quote.weightCost.toInt()}\n")
            append("${getString(R.string.service_cost)}: ₨${quote.serviceCost.toInt()}")
            if (quote.urgencyMultiplier > 1) append("\nExpress: x${quote.urgencyMultiplier}")
        }
        findViewById<TextView>(R.id.tvTotalQuote).text =
            "${getString(R.string.total_quote)}: ₨${quote.total.toInt()}"

        val deposit = (quote.total * 0.10).toInt()
        val pickup = (quote.total * 0.50).toInt()
        val final = quote.total.toInt() - deposit - pickup
        findViewById<TextView>(R.id.tvPaymentSchedule).text = buildString {
            append(getString(R.string.payment_schedule))
            append("\n")
            append(getString(R.string.payment_schedule_detail, deposit, pickup, final))
        }
    }

    private suspend fun geocode(address: String): Pair<Double, Double> = withContext(Dispatchers.IO) {
        try {
            val geocoder = Geocoder(this@BookingActivity, Locale.getDefault())
            @Suppress("DEPRECATION")
            val results = geocoder.getFromLocationName(address, 1)
            if (!results.isNullOrEmpty()) {
                Pair(results[0].latitude, results[0].longitude)
            } else {
                Pair(31.5204, 74.3587)
            }
        } catch (_: Exception) {
            Pair(31.5204, 74.3587)
        }
    }
}
