package com.sawarri.util

import com.sawarri.data.model.Quote
import com.sawarri.data.model.Service
import kotlin.math.*

object QuotingEngine {

    private val vehicleRates = mapOf(
        "BIKE" to Pair(500.0, 15.0),
        "SMALL_VAN" to Pair(2000.0, 25.0),
        "MEDIUM_TRUCK" to Pair(5000.0, 40.0),
        "HEAVY_TRUCK" to Pair(10000.0, 60.0),
        "REFRIGERATED" to Pair(8000.0, 55.0)
    )

    fun haversineKm(lat1: Double, lng1: Double, lat2: Double, lng2: Double): Double {
        val r = 6371.0
        val dLat = Math.toRadians(lat2 - lat1)
        val dLng = Math.toRadians(lng2 - lng1)
        val a = sin(dLat / 2).pow(2) +
                cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLng / 2).pow(2)
        return r * 2 * atan2(sqrt(a), sqrt(1 - a))
    }

    fun calculate(
        vehicleCategory: String,
        distanceKm: Double,
        weightKg: Double,
        lengthM: Double,
        widthM: Double,
        heightM: Double,
        services: List<Service>,
        urgency: String
    ): Quote {
        val rates = vehicleRates[vehicleCategory.uppercase()] ?: vehicleRates["SMALL_VAN"]!!
        val baseRate = rates.first
        val distanceCost = distanceKm * rates.second
        val weightCost = max(0.0, weightKg - 100) * 5
        val volumeCost = lengthM * widthM * heightM * 200
        val serviceCost = services.sumOf { it.price }
        val subtotal = baseRate + distanceCost + weightCost + volumeCost + serviceCost
        val urgencyMultiplier = if (urgency.equals("express", true)) 1.5 else 1.0
        val total = (subtotal * urgencyMultiplier).roundToInt().toDouble()
        return Quote(baseRate, distanceCost, weightCost, volumeCost, serviceCost, urgencyMultiplier, total)
    }
}
