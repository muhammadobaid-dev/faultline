package com.sawarri.data.repository

import android.content.Context
import com.google.firebase.Timestamp
import com.sawarri.data.model.User
import com.sawarri.data.model.UserRole
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/**
 * Offline / demo auth for when Firebase Auth is unreachable
 * (common on TECNO / devices without full Google Play Services).
 */
class LocalAuthStore(context: Context) {

    private val prefs = context.applicationContext
        .getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    val currentUserId: String?
        get() = prefs.getString(KEY_SESSION, null)

    fun logout() {
        prefs.edit().remove(KEY_SESSION).apply()
    }

    fun getUser(userId: String): User? =
        loadUsers().firstOrNull { it.id == userId }

    fun getUsersByRole(role: UserRole): List<User> =
        loadUsers().filter { it.role == role }

    fun register(
        name: String,
        username: String,
        email: String,
        password: String,
        address: String,
        phone: String,
        role: UserRole
    ): User {
        val users = loadUsers().toMutableList()
        val cleanUsername = username.trim().lowercase()
        val cleanEmail = email.trim().lowercase()

        if (users.any { it.username.equals(cleanUsername, true) }) {
            error("Username already taken")
        }
        if (users.any { it.email.equals(cleanEmail, true) }) {
            error("Email already registered")
        }

        val uid = "local-${UUID.randomUUID().toString().take(8)}"
        val user = User(
            id = uid,
            userId = "SWR-${uid.takeLast(8).uppercase()}",
            name = name.trim(),
            username = cleanUsername,
            email = cleanEmail,
            address = address.trim(),
            phone = phone.trim(),
            role = role,
            createdAt = Timestamp.now()
        )

        users.add(user)
        saveUsers(users)
        savePassword(uid, password)
        prefs.edit().putString(KEY_SESSION, uid).apply()
        return user
    }

    fun login(identifier: String, password: String): User {
        val key = identifier.trim().lowercase()
        val user = loadUsers().firstOrNull {
            it.email.equals(key, true) || it.username.equals(key, true)
        } ?: error("User not found. Register first (local demo mode).")

        val saved = prefs.getString(passKey(user.id), null)
            ?: error("Invalid password")
        if (saved != password) error("Invalid password")

        prefs.edit().putString(KEY_SESSION, user.id).apply()
        return user
    }

    private fun savePassword(uid: String, password: String) {
        prefs.edit().putString(passKey(uid), password).apply()
    }

    private fun passKey(uid: String) = "pass_$uid"

    private fun loadUsers(): List<User> {
        val raw = prefs.getString(KEY_USERS, "[]") ?: "[]"
        val arr = JSONArray(raw)
        val list = mutableListOf<User>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            list.add(
                User(
                    id = o.optString("id"),
                    userId = o.optString("userId"),
                    name = o.optString("name"),
                    username = o.optString("username"),
                    email = o.optString("email"),
                    address = o.optString("address"),
                    phone = o.optString("phone"),
                    role = runCatching {
                        UserRole.valueOf(o.optString("role", "CUSTOMER"))
                    }.getOrDefault(UserRole.CUSTOMER),
                    createdAt = Timestamp.now()
                )
            )
        }
        return list
    }

    private fun saveUsers(users: List<User>) {
        val arr = JSONArray()
        users.forEach { u ->
            arr.put(
                JSONObject()
                    .put("id", u.id)
                    .put("userId", u.userId)
                    .put("name", u.name)
                    .put("username", u.username)
                    .put("email", u.email)
                    .put("address", u.address)
                    .put("phone", u.phone)
                    .put("role", u.role.name)
            )
        }
        prefs.edit().putString(KEY_USERS, arr.toString()).apply()
    }

    companion object {
        private const val PREFS = "sawarri_local_auth"
        private const val KEY_USERS = "users"
        private const val KEY_SESSION = "session_uid"
    }
}
