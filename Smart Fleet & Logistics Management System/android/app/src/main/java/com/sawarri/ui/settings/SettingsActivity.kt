package com.sawarri.ui.settings

import android.os.Bundle
import android.view.View
import android.widget.RadioButton
import android.widget.TextView
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.google.android.material.button.MaterialButton
import com.google.android.material.switchmaterial.SwitchMaterial
import com.google.android.material.textfield.TextInputEditText
import com.sawarri.R
import com.sawarri.data.model.UserRole
import com.sawarri.data.repository.AuthRepository
import com.sawarri.ui.viewmodel.AuthState
import com.sawarri.ui.viewmodel.AuthViewModel
import com.sawarri.util.AppPreferences
import com.sawarri.util.NavigationHelper
import kotlinx.coroutines.launch

class SettingsActivity : AppCompatActivity() {

    private val authViewModel: AuthViewModel by viewModels()
    private val authRepository = AuthRepository()
    private lateinit var prefs: AppPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)
        prefs = AppPreferences(this)

        findViewById<androidx.appcompat.widget.Toolbar>(R.id.toolbar)
            .setNavigationOnClickListener { finish() }

        val tvUserId = findViewById<TextView>(R.id.tvUserId)
        val etName = findViewById<TextInputEditText>(R.id.etProfileName)
        val etUsername = findViewById<TextInputEditText>(R.id.etProfileUsername)
        val etEmail = findViewById<TextInputEditText>(R.id.etProfileEmail)
        val etPhone = findViewById<TextInputEditText>(R.id.etProfilePhone)
        val etAddress = findViewById<TextInputEditText>(R.id.etProfileAddress)
        val tvRole = findViewById<TextView>(R.id.tvRole)
        val etWallet = findViewById<TextInputEditText>(R.id.etDefaultWallet)
        val switchNotif = findViewById<SwitchMaterial>(R.id.switchNotifications)
        val rbJazz = findViewById<RadioButton>(R.id.rbDefaultJazz)
        val rbEasy = findViewById<RadioButton>(R.id.rbDefaultEasy)
        val progress = findViewById<View>(R.id.progressProfile)

        switchNotif.isChecked = prefs.notificationsEnabled
        etWallet.setText(prefs.savedWalletNumber)
        if (prefs.defaultGateway == "EasyPaisa") rbEasy.isChecked = true else rbJazz.isChecked = true

        lifecycleScope.launch {
            val userId = authRepository.currentUserId ?: return@launch
            authRepository.getUserProfile(userId).onSuccess { user ->
                tvUserId.text = user.userId.ifBlank { "SWR-${user.id.take(8).uppercase()}" }
                etName.setText(user.name)
                etUsername.setText(user.username)
                etEmail.setText(user.email)
                etPhone.setText(user.phone)
                etAddress.setText(user.address)
                tvRole.text = roleLabel(user.role)
            }
        }

        findViewById<MaterialButton>(R.id.btnSaveProfile).setOnClickListener {
            val name = etName.text.toString().trim()
            val username = etUsername.text.toString().trim()
            val phone = etPhone.text.toString().trim()
            val address = etAddress.text.toString().trim()

            if (name.isEmpty() || username.isEmpty() || address.isEmpty() || phone.length < 11) {
                Toast.makeText(this, R.string.fill_required, Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            prefs.defaultGateway = if (rbEasy.isChecked) "EasyPaisa" else "JazzCash"
            prefs.savedWalletNumber = etWallet.text.toString().trim()
            prefs.notificationsEnabled = switchNotif.isChecked

            authViewModel.updateProfile(name, username, address, phone)
        }

        findViewById<MaterialButton>(R.id.btnLogout).setOnClickListener {
            authViewModel.logout()
            NavigationHelper.goToLogin(this)
            finish()
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                authViewModel.authState.collect { state ->
                    when (state) {
                        is AuthState.Loading -> progress.visibility = View.VISIBLE
                        is AuthState.Success -> {
                            progress.visibility = View.GONE
                            Toast.makeText(this@SettingsActivity, R.string.settings_saved, Toast.LENGTH_SHORT).show()
                            authViewModel.resetState()
                        }
                        is AuthState.Error -> {
                            progress.visibility = View.GONE
                            Toast.makeText(this@SettingsActivity, state.message, Toast.LENGTH_LONG).show()
                            authViewModel.resetState()
                        }
                        else -> progress.visibility = View.GONE
                    }
                }
            }
        }
    }

    private fun roleLabel(role: UserRole) = when (role) {
        UserRole.CUSTOMER -> getString(R.string.role_customer)
        UserRole.DRIVER -> getString(R.string.role_driver)
        UserRole.ADMIN -> getString(R.string.role_admin)
        UserRole.LOADER -> "Loader"
    }
}
