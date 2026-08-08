package com.sawarri.ui.auth

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.sawarri.R
import com.sawarri.ui.viewmodel.AuthState
import com.sawarri.ui.viewmodel.AuthViewModel
import com.sawarri.util.NavigationHelper
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {

    private val authViewModel: AuthViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        val etEmail = findViewById<android.widget.EditText>(R.id.etEmail)
        val etPassword = findViewById<android.widget.EditText>(R.id.etPassword)
        val progressBar = findViewById<android.widget.ProgressBar>(R.id.progressBar)
        val btnSignIn = findViewById<android.widget.Button>(R.id.btnSignIn)
        val tvRegister = findViewById<android.widget.TextView>(R.id.tvRegister)

        btnSignIn.setOnClickListener {
            val email = etEmail.text.toString().trim()
            val password = etPassword.text.toString().trim()
            if (email.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Please fill all fields", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            authViewModel.login(email, password)
        }

        tvRegister.setOnClickListener {
            startActivity(Intent(this, RegisterActivity::class.java))
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                authViewModel.authState.collect { state ->
                    when (state) {
                        is AuthState.Loading -> progressBar.visibility = View.VISIBLE
                        is AuthState.Success -> {
                            progressBar.visibility = View.GONE
                            NavigationHelper.navigateByRole(this@LoginActivity, state.user)
                            finish()
                        }
                        is AuthState.Error -> {
                            progressBar.visibility = View.GONE
                            Toast.makeText(this@LoginActivity, state.message, Toast.LENGTH_LONG).show()
                            authViewModel.resetState()
                        }
                        else -> progressBar.visibility = View.GONE
                    }
                }
            }
        }
    }
}
