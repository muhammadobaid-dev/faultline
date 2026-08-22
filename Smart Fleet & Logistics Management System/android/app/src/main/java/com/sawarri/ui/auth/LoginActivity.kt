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
import com.google.android.material.textfield.TextInputEditText
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

        val etIdentifier = findViewById<TextInputEditText>(R.id.etEmail)
        val etPassword = findViewById<TextInputEditText>(R.id.etPassword)
        val progressBar = findViewById<View>(R.id.progressBar)

        findViewById<View>(R.id.btnSignIn).setOnClickListener {
            val identifier = etIdentifier.text.toString().trim()
            val password = etPassword.text.toString()
            if (identifier.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, R.string.fill_required, Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            authViewModel.login(identifier, password)
        }

        findViewById<View>(R.id.tvRegister).setOnClickListener {
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
