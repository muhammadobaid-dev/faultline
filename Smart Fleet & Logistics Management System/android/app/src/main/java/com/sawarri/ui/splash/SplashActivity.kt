package com.sawarri.ui.splash

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.sawarri.R
import com.sawarri.ui.auth.LoginActivity
import com.sawarri.ui.viewmodel.AuthState
import com.sawarri.ui.viewmodel.AuthViewModel
import com.sawarri.util.NavigationHelper
import kotlinx.coroutines.launch

class SplashActivity : AppCompatActivity() {

    private val authViewModel: AuthViewModel by viewModels()
    private var navigated = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_splash)

        Handler(Looper.getMainLooper()).postDelayed({
            authViewModel.checkSession()
        }, 1500)

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                authViewModel.authState.collect { state ->
                    if (navigated) return@collect
                    when (state) {
                        is AuthState.Success -> {
                            navigated = true
                            NavigationHelper.navigateByRole(this@SplashActivity, state.user)
                            finish()
                        }
                        is AuthState.NoSession -> {
                            navigated = true
                            startActivity(Intent(this@SplashActivity, LoginActivity::class.java))
                            finish()
                        }
                        else -> Unit
                    }
                }
            }
        }
    }
}
