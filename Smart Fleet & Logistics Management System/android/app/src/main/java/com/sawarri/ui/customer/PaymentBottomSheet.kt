package com.sawarri.ui.customer

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import com.sawarri.R
import com.sawarri.data.model.Booking
import com.sawarri.data.model.PaymentPhase
import com.sawarri.payment.PaymentGateway
import com.sawarri.payment.PaymentGatewayService
import com.sawarri.util.AppPreferences
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class PaymentBottomSheet : BottomSheetDialogFragment() {

    interface PaymentListener {
        fun onPaymentConfirmed(gateway: PaymentGateway, mobile: String, txnId: String)
    }

    companion object {
        private const val ARG_AMOUNT = "amount"
        private const val ARG_PHASE = "phase"

        fun newInstance(amount: Double, phase: PaymentPhase): PaymentBottomSheet {
            return PaymentBottomSheet().apply {
                arguments = Bundle().apply {
                    putDouble(ARG_AMOUNT, amount)
                    putString(ARG_PHASE, phase.name)
                }
            }
        }
    }

    var listener: PaymentListener? = null
    private var selectedGateway = PaymentGateway.JAZZCASH

    override fun onCreateView(inflater: LayoutInflater, container: android.view.ViewGroup?, savedInstanceState: Bundle?): View? {
        return inflater.inflate(R.layout.bottom_sheet_payment, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        val amount = arguments?.getDouble(ARG_AMOUNT) ?: 0.0
        val prefs = AppPreferences(requireContext())

        view.findViewById<TextView>(R.id.tvPayAmount).text =
            getString(R.string.pay_now, String.format("%,d", amount.toInt()))

        val etMobile = view.findViewById<TextInputEditText>(R.id.etWalletMobile)
        val etMpin = view.findViewById<TextInputEditText>(R.id.etMpin)
        etMobile.setText(prefs.savedWalletNumber)

        val cardJazz = view.findViewById<LinearLayout>(R.id.cardJazzCash)
        val cardEasy = view.findViewById<LinearLayout>(R.id.cardEasyPaisa)
        val progress = view.findViewById<ProgressBar>(R.id.progressPay)
        val btnConfirm = view.findViewById<MaterialButton>(R.id.btnConfirmPay)

        if (prefs.defaultGateway == "EasyPaisa") selectGateway(cardEasy, cardJazz, PaymentGateway.EASYPAISA)
        else selectGateway(cardJazz, cardEasy, PaymentGateway.JAZZCASH)

        cardJazz.setOnClickListener { selectGateway(cardJazz, cardEasy, PaymentGateway.JAZZCASH) }
        cardEasy.setOnClickListener { selectGateway(cardEasy, cardJazz, PaymentGateway.EASYPAISA) }

        btnConfirm.setOnClickListener {
            val mobile = etMobile.text.toString().trim()
            val mpin = etMpin.text.toString().trim()
            if (mpin.length < 4) {
                Toast.makeText(context, R.string.enter_mpin, Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            progress.visibility = View.VISIBLE
            btnConfirm.isEnabled = false

            CoroutineScope(Dispatchers.Main).launch {
                val result = withContext(Dispatchers.IO) {
                    PaymentGatewayService.processPayment(selectedGateway, mobile, amount)
                }
                progress.visibility = View.GONE
                btnConfirm.isEnabled = true

                result.onSuccess { paymentResult ->
                    prefs.savedWalletNumber = mobile
                    prefs.defaultGateway = selectedGateway.displayName
                    listener?.onPaymentConfirmed(
                        selectedGateway, paymentResult.mobileNumber, paymentResult.transactionId
                    )
                    dismiss()
                }.onFailure {
                    Toast.makeText(context, it.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun selectGateway(selected: LinearLayout, other: LinearLayout, gateway: PaymentGateway) {
        selected.isSelected = true
        other.isSelected = false
        selectedGateway = gateway
    }
}
