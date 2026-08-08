package com.sawarri.util

import android.content.Context
import android.content.Intent
import com.sawarri.data.model.User
import com.sawarri.data.model.UserRole
import com.sawarri.ui.admin.AdminDashboardActivity
import com.sawarri.ui.auth.LoginActivity
import com.sawarri.ui.customer.HomeActivity
import com.sawarri.ui.driver.DriverDashboardActivity

object NavigationHelper {

    fun navigateByRole(context: Context, user: User) {
        val intent = when (user.role) {
            UserRole.ADMIN -> Intent(context, AdminDashboardActivity::class.java)
            UserRole.DRIVER -> Intent(context, DriverDashboardActivity::class.java)
            UserRole.CUSTOMER, UserRole.LOADER -> Intent(context, HomeActivity::class.java)
        }
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        context.startActivity(intent)
    }

    fun goToLogin(context: Context) {
        val intent = Intent(context, LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        context.startActivity(intent)
    }
}
