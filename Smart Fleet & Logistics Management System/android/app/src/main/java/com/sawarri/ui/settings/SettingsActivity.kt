package com.sawarri.ui.settings

import android.os.Bundle
import android.widget.RadioButton
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import com.google.android.material.switchmaterial.SwitchMaterial
import com.google.android.material.textfield.TextInputEditText
import com.google.firebase.firestore.FirebaseFirestore
import com.sawarri.R
import com.sawarri.data.model.UserRole
import com.sawarri.data.repository.AuthRepository
import com.sawarri.ui.viewmodel.AuthViewModel
import com.sawarri.util.AppPreferences
import com.sawarri.util.NavigationHelper
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

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

        val etName = findViewById<TextInputEditText>(R.id.etProfileName)
        val etEmail = findViewById<TextInputEditText>(R.id.etProfileEmail)
        val etPhone = findViewById<TextInputEditText>(R.id.etProfilePhone)
        val tvRole = findViewById<android.widget.TextView>(R.id.tvRole)
        val etWallet = findViewById<TextInputEditText>(R.id.etDefaultWallet)
        val switchNotif = findViewById<SwitchMaterial>(R.id.switchNotifications)
        val rbJazz = findViewById<RadioButton>(R.id.rbDefaultJazz)
        val rbEasy = findViewById<RadioButton>(R.id.rbDefaultEasy)

        switchNotif.isChecked = prefs.notificationsEnabled
        etWallet.setText(prefs.savedWalletNumber)
        if (prefs.defaultGateway == "EasyPaisa") rbEasy.isChecked = true else rbJazz.isChecked = true

        lifecycleScope.launch {
            val userId = authRepository.currentUserId ?: return@launch
            authRepository.getUserProfile(userId).onSuccess { user ->
                etName.setText(user.name)
                etEmail.setText(user.email)
                etPhone.setText(user.phone)
                tvRole.text = roleLabel(user.role)
            }
        }

        findViewById<MaterialButton>(R.id.btnSaveProfile).setOnClickListener {
            lifecycleScope.launch {
                val userId = authRepository.currentUserId ?: return@launch
                val updates = mapOf(
                    "name" to etName.text.toString().trim(),
                    "phone" to etPhone.text.toString().trim()
                )
                FirebaseFirestore.getInstance().collection("users")
                    .document(userId).update(updates).await()

                prefs.defaultGateway = if (rbEasy.isChecked) "EasyPaisa" else "JazzCash"
                prefs.savedWalletNumber = etWallet.text.toString().trim()
                prefs.notificationsEnabled = switchNotif.isChecked

                Toast.makeText(this@SettingsActivity, R.string.settings_saved, Toast.LENGTH_SHORT).show()
            }
        }

        findViewById<MaterialButton>(R.id.btnLogout).setOnClickListener {
            authViewModel.logout()
            NavigationHelper.goToLogin(this)
            finish()
        }
    }

    private fun roleLabel(role: UserRole) = when (role) {
        UserRole.CUSTOMER -> getString(R.string.role_customer)
        UserRole.DRIVER -> getString(R.string.role_driver)
        UserRole.ADMIN -> getString(R.string.role_admin)
        UserRole.LOADER -> "Loader"
    }
}
