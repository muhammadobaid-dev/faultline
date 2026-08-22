package com.sawarri.ui.auth

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.google.android.material.chip.Chip
import com.google.android.material.textfield.TextInputEditText
import com.sawarri.R
import com.sawarri.data.model.UserRole
import com.sawarri.ui.viewmodel.AuthState
import com.sawarri.ui.viewmodel.AuthViewModel
import com.sawarri.util.NavigationHelper
import kotlinx.coroutines.launch

class RegisterActivity : AppCompatActivity() {

    private val authViewModel: AuthViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_register)

        val etName = findViewById<TextInputEditText>(R.id.etName)
        val etUsername = findViewById<TextInputEditText>(R.id.etUsername)
        val etEmail = findViewById<TextInputEditText>(R.id.etEmail)
        val etPhone = findViewById<TextInputEditText>(R.id.etPhone)
        val etAddress = findViewById<TextInputEditText>(R.id.etAddress)
        val etPassword = findViewById<TextInputEditText>(R.id.etPassword)
        val progressBar = findViewById<View>(R.id.progressBar)
        val btnRegister = findViewById<View>(R.id.btnRegister)
        val chipCustomer = findViewById<Chip>(R.id.chipCustomer)
        val chipDriver = findViewById<Chip>(R.id.chipDriver)
        val chipAdmin = findViewById<Chip>(R.id.chipAdmin)

        btnRegister.setOnClickListener {
            val name = etName.text.toString().trim()
            val username = etUsername.text.toString().trim()
            val email = etEmail.text.toString().trim()
            val phone = etPhone.text.toString().trim()
            val address = etAddress.text.toString().trim()
            val password = etPassword.text.toString()

            when {
                name.isEmpty() -> toast(R.string.fill_name)
                username.isEmpty() -> toast(R.string.fill_username)
                email.isEmpty() || !email.contains("@") -> toast(R.string.fill_email)
                phone.length < 11 -> toast(R.string.fill_mobile)
                address.isEmpty() -> toast(R.string.fill_address)
                password.length < 6 -> toast(R.string.password_hint)
                else -> {
                    val role = when {
                        chipAdmin.isChecked -> UserRole.ADMIN
                        chipDriver.isChecked -> UserRole.DRIVER
                        else -> UserRole.CUSTOMER
                    }
                    authViewModel.register(name, username, email, password, address, phone, role)
                }
            }
        }

        findViewById<View>(R.id.tvLogin).setOnClickListener { finish() }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                authViewModel.authState.collect { state ->
                    when (state) {
                        is AuthState.Loading -> progressBar.visibility = View.VISIBLE
                        is AuthState.Success -> {
                            progressBar.visibility = View.GONE
                            Toast.makeText(
                                this@RegisterActivity,
                                getString(R.string.account_created, state.user.userId),
                                Toast.LENGTH_LONG
                            ).show()
                            NavigationHelper.navigateByRole(this@RegisterActivity, state.user)
                            finish()
                        }
                        is AuthState.Error -> {
                            progressBar.visibility = View.GONE
                            Toast.makeText(this@RegisterActivity, state.message, Toast.LENGTH_LONG).show()
                            authViewModel.resetState()
                        }
                        else -> progressBar.visibility = View.GONE
                    }
                }
            }
        }
    }

    private fun toast(res: Int) =
        Toast.makeText(this, res, Toast.LENGTH_SHORT).show()
}
