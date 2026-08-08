package com.sawarri.ui.auth

import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.sawarri.R
import com.sawarri.data.model.UserRole
import com.sawarri.ui.viewmodel.AuthState
import com.sawarri.ui.viewmodel.AuthViewModel
import com.sawarri.util.NavigationHelper
import kotlinx.coroutines.launch

class RegisterActivity : AppCompatActivity() {

    private val authViewModel: AuthViewModel by viewModels()
    private val roles = listOf(UserRole.CUSTOMER, UserRole.DRIVER, UserRole.ADMIN)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_register)

        val etName = findViewById<android.widget.EditText>(R.id.etName)
        val etEmail = findViewById<android.widget.EditText>(R.id.etEmail)
        val etPassword = findViewById<android.widget.EditText>(R.id.etPassword)
        val spinnerRole = findViewById<android.widget.Spinner>(R.id.spinnerRole)
        val progressBar = findViewById<android.widget.ProgressBar>(R.id.progressBar)
        val btnRegister = findViewById<android.widget.Button>(R.id.btnRegister)
        val tvLogin = findViewById<android.widget.TextView>(R.id.tvLogin)

        val roleLabels = listOf(
            getString(R.string.role_customer),
            getString(R.string.role_driver),
            getString(R.string.role_admin)
        )
        spinnerRole.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, roleLabels)

        btnRegister.setOnClickListener {
            val name = etName.text.toString().trim()
            val email = etEmail.text.toString().trim()
            val password = etPassword.text.toString().trim()
            if (name.isEmpty() || email.isEmpty() || password.length < 6) {
                Toast.makeText(this, "Name, email required. Password min 6 chars.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            val role = roles[spinnerRole.selectedItemPosition]
            authViewModel.register(email, password, name, role)
        }

        tvLogin.setOnClickListener { finish() }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                authViewModel.authState.collect { state ->
                    when (state) {
                        is AuthState.Loading -> progressBar.visibility = View.VISIBLE
                        is AuthState.Success -> {
                            progressBar.visibility = View.GONE
                            Toast.makeText(this@RegisterActivity, "Account created!", Toast.LENGTH_SHORT).show()
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
}
