package com.sawarri

import android.app.Application
import android.util.Log
import com.google.android.gms.security.ProviderInstaller
import com.google.firebase.FirebaseApp
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.FirebaseFirestoreSettings
import com.sawarri.data.repository.LocalAuthStore
import com.sawarri.data.repository.LocalDataStore
import org.osmdroid.config.Configuration

class SawarriApp : Application() {

    lateinit var localAuthStore: LocalAuthStore
        private set

    lateinit var localDataStore: LocalDataStore
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        localAuthStore = LocalAuthStore(this)
        localDataStore = LocalDataStore(this)

        FirebaseApp.initializeApp(this)

        try {
            ProviderInstaller.installIfNeeded(this)
        } catch (e: Exception) {
            Log.w("SawarriApp", "ProviderInstaller skipped: ${e.message}")
        }

        val firestore = FirebaseFirestore.getInstance()
        firestore.firestoreSettings = FirebaseFirestoreSettings.Builder()
            .setPersistenceEnabled(true)
            .build()
        firestore.enableNetwork()

        Configuration.getInstance().userAgentValue = packageName
    }

    companion object {
        lateinit var instance: SawarriApp
            private set

        fun isLocalUser(userId: String?): Boolean =
            userId.isNullOrBlank() || userId.startsWith("local-")
    }
}
