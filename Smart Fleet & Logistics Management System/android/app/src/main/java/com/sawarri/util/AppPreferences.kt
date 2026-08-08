package com.sawarri.util

import android.content.Context
import android.content.SharedPreferences

class AppPreferences(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("sawarri_prefs", Context.MODE_PRIVATE)

    var notificationsEnabled: Boolean
        get() = prefs.getBoolean(KEY_NOTIFICATIONS, true)
        set(value) = prefs.edit().putBoolean(KEY_NOTIFICATIONS, value).apply()

    var defaultGateway: String
        get() = prefs.getString(KEY_GATEWAY, "JazzCash") ?: "JazzCash"
        set(value) = prefs.edit().putString(KEY_GATEWAY, value).apply()

    var savedWalletNumber: String
        get() = prefs.getString(KEY_WALLET, "") ?: ""
        set(value) = prefs.edit().putString(KEY_WALLET, value).apply()

    companion object {
        private const val KEY_NOTIFICATIONS = "notifications"
        private const val KEY_GATEWAY = "default_gateway"
        private const val KEY_WALLET = "wallet_number"
    }
}
