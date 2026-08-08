package com.sawarri.ui.customer

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.TextView
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.button.MaterialButton
import com.sawarri.R
import com.sawarri.data.model.PaymentPhase
import com.sawarri.data.model.TripStatus
import com.sawarri.payment.PaymentGateway
import com.sawarri.ui.settings.SettingsActivity
import com.sawarri.ui.viewmodel.AuthViewModel
import com.sawarri.ui.viewmodel.PaymentState
import com.sawarri.ui.viewmodel.PaymentViewModel
import com.sawarri.util.NavigationHelper
import com.sawarri.util.UiHelper
import kotlinx.coroutines.launch

class PaymentActivity : AppCompatActivity(), PaymentBottomSheet.PaymentListener {

    companion object {
        const val EXTRA_BOOKING_ID = "booking_id"
    }

    private val paymentViewModel: PaymentViewModel by viewModels()
    private val authViewModel: AuthViewModel by viewModels()
    private var currentPhase: PaymentPhase? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_payment)

        val bookingId = intent.getStringExtra(EXTRA_BOOKING_ID)
            ?: run { finish(); return }

        setSupportActionBar(findViewById(R.id.toolbar))
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        findViewById<androidx.appcompat.widget.Toolbar>(R.id.toolbar)
            .setNavigationOnClickListener { finish() }

        paymentViewModel.loadPaymentData(bookingId)

        findViewById<MaterialButton>(R.id.btnPay).setOnClickListener {
            val booking = paymentViewModel.booking.value ?: return@setOnClickListener
            val phase = currentPhase ?: return@setOnClickListener
            val amount = paymentViewModel.getAmount(booking.quote, phase)
            PaymentBottomSheet.newInstance(amount, phase).apply {
                listener = this@PaymentActivity
            }.show(supportFragmentManager, "payment")
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                paymentViewModel.booking.collect { booking ->
                    booking?.let { updateUI(it) }
                }
            }
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                paymentViewModel.payments.collect {
                    paymentViewModel.booking.value?.let { updateUI(it) }
                }
            }
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                paymentViewModel.paymentState.collect { state ->
                    val progress = findViewById<View>(R.id.progressBar)
                    when (state) {
                        is PaymentState.Loading -> progress.visibility = View.VISIBLE
                        is PaymentState.Completed -> {
                            progress.visibility = View.GONE
                            Toast.makeText(this@PaymentActivity, R.string.payment_success, Toast.LENGTH_LONG).show()
                            paymentViewModel.resetPaymentState()
                        }
                        is PaymentState.Error -> {
                            progress.visibility = View.GONE
                            Toast.makeText(this@PaymentActivity, state.message, Toast.LENGTH_LONG).show()
                            paymentViewModel.resetPaymentState()
                        }
                        else -> progress.visibility = View.GONE
                    }
                }
            }
        }
    }

    override fun onPaymentConfirmed(gateway: PaymentGateway, mobile: String, txnId: String) {
        val booking = paymentViewModel.booking.value ?: return
        val phase = currentPhase ?: return
        val ref = "${gateway.displayName}|$mobile|$txnId"
        paymentViewModel.payPhase(booking, phase, ref)
    }

    private fun updateUI(booking: com.sawarri.data.model.Booking) {
        findViewById<TextView>(R.id.tvBookingInfo).text =
            getString(R.string.booking_id, booking.id.take(8).uppercase())
        findViewById<TextView>(R.id.tvBookingStatus).text =
            UiHelper.statusLabel(booking.status)

        val depositAmt = paymentViewModel.getAmount(booking.quote, PaymentPhase.DEPOSIT).toInt()
        val pickupAmt = paymentViewModel.getAmount(booking.quote, PaymentPhase.PICKUP).toInt()
        val finalAmt = paymentViewModel.getAmount(booking.quote, PaymentPhase.FINAL).toInt()

        findViewById<TextView>(R.id.tvDepositAmount).text = "₨${String.format("%,d", depositAmt)}"
        findViewById<TextView>(R.id.tvPickupAmount).text = "₨${String.format("%,d", pickupAmt)}"
        findViewById<TextView>(R.id.tvFinalAmount).text = "₨${String.format("%,d", finalAmt)}"

        val depositPaid = paymentViewModel.isPhasePaid(PaymentPhase.DEPOSIT)
        val pickupPaid = paymentViewModel.isPhasePaid(PaymentPhase.PICKUP)
        val finalPaid = paymentViewModel.isPhasePaid(PaymentPhase.FINAL)

        setPhaseStatus(R.id.tvDepositStatus, depositPaid, PaymentPhase.DEPOSIT, booking)
        setPhaseStatus(R.id.tvPickupStatus, pickupPaid, PaymentPhase.PICKUP, booking)
        setPhaseStatus(R.id.tvFinalStatus, finalPaid, PaymentPhase.FINAL, booking)

        currentPhase = when {
            !depositPaid && booking.status == TripStatus.APPROVED -> PaymentPhase.DEPOSIT
            !pickupPaid && depositPaid && booking.status == TripStatus.AT_PICKUP -> PaymentPhase.PICKUP
            !finalPaid && pickupPaid && booking.status == TripStatus.AT_DESTINATION -> PaymentPhase.FINAL
            else -> null
        }

        val btnPay = findViewById<MaterialButton>(R.id.btnPay)
        if (currentPhase != null) {
            val amt = paymentViewModel.getAmount(booking.quote, currentPhase!!).toInt()
            btnPay.text = getString(R.string.pay_via_wallet, String.format("%,d", amt))
            btnPay.isEnabled = true
        } else {
            btnPay.text = getString(R.string.payment_not_available)
            btnPay.isEnabled = false
        }
    }

    private fun setPhaseStatus(
        viewId: Int, paid: Boolean, phase: PaymentPhase,
        booking: com.sawarri.data.model.Booking
    ) {
        val tv = findViewById<TextView>(viewId)
        tv.text = if (paid) getString(R.string.paid) else statusForPhase(phase, booking)
        tv.setBackgroundResource(if (paid) R.drawable.bg_chip_success else R.drawable.bg_chip_default)
        tv.setTextColor(ContextCompat.getColor(this, if (paid) R.color.success else R.color.text_secondary))
        tv.setPadding(24, 8, 24, 8)
    }

    private fun statusForPhase(phase: PaymentPhase, booking: com.sawarri.data.model.Booking): String =
        when (phase) {
            PaymentPhase.DEPOSIT -> if (booking.status == TripStatus.APPROVED) getString(R.string.due) else getString(R.string.locked)
            PaymentPhase.PICKUP -> if (booking.status == TripStatus.AT_PICKUP) getString(R.string.due) else getString(R.string.locked)
            PaymentPhase.FINAL -> if (booking.status == TripStatus.AT_DESTINATION) getString(R.string.due) else getString(R.string.locked)
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
