package com.sawarri

import android.app.Application
import com.google.firebase.FirebaseApp
import org.osmdroid.config.Configuration

class SawarriApp : Application() {
    override fun onCreate() {
        super.onCreate()
        FirebaseApp.initializeApp(this)
        Configuration.getInstance().userAgentValue = packageName
    }
}
