package com.sawarri.payment

import kotlinx.coroutines.delay
import kotlin.random.Random

enum class PaymentGateway(val displayName: String, val packageName: String) {
    JAZZCASH("JazzCash", "com.techlogix.mobilinkcustomer"),
    EASYPAISA("EasyPaisa", "pk.com.telenor.phoenix")
}

object PaymentGatewayService {

    data class PaymentResult(
        val transactionId: String,
        val gateway: PaymentGateway,
        val mobileNumber: String,
        val amount: Double
    )

    /**
     * Processes payment via JazzCash or EasyPaisa wallet.
     * Validates Pakistani mobile format and returns a transaction reference.
     */
    suspend fun processPayment(
        gateway: PaymentGateway,
        mobileNumber: String,
        amount: Double
    ): Result<PaymentResult> {
        val cleaned = mobileNumber.replace(Regex("[^0-9]"), "")
        if (!cleaned.matches(Regex("03[0-9]{9}"))) {
            return Result.failure(IllegalArgumentException("Enter valid mobile: 03XX-XXXXXXX"))
        }
        if (amount <= 0) {
            return Result.failure(IllegalArgumentException("Invalid payment amount"))
        }

        // Simulate gateway API round-trip
        delay(2000)

        val prefix = when (gateway) {
            PaymentGateway.JAZZCASH -> "JC"
            PaymentGateway.EASYPAISA -> "EP"
        }
        val txnId = "$prefix${System.currentTimeMillis()}${Random.nextInt(1000, 9999)}"

        return Result.success(
            PaymentResult(txnId, gateway, cleaned, amount)
        )
    }
}
