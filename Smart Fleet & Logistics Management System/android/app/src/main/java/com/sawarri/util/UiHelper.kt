package com.sawarri.util

import android.graphics.drawable.GradientDrawable
import android.widget.FrameLayout
import android.widget.TextView
import androidx.core.content.ContextCompat
import com.sawarri.R
import com.sawarri.data.model.TripStatus
import com.sawarri.data.model.VehicleCategory

object UiHelper {

    data class CategoryStyle(val abbr: String, val colorRes: Int, val bgRes: Int)

    fun categoryStyle(category: VehicleCategory): CategoryStyle = when (category) {
        VehicleCategory.BIKE -> CategoryStyle("BK", R.color.cat_bike, R.color.cat_bike_bg)
        VehicleCategory.SMALL_VAN -> CategoryStyle("SV", R.color.cat_van, R.color.cat_van_bg)
        VehicleCategory.MEDIUM_TRUCK -> CategoryStyle("MT", R.color.cat_truck, R.color.cat_truck_bg)
        VehicleCategory.HEAVY_TRUCK -> CategoryStyle("HT", R.color.cat_heavy, R.color.cat_heavy_bg)
        VehicleCategory.REFRIGERATED -> CategoryStyle("RF", R.color.cat_cold, R.color.cat_cold_bg)
    }

    fun applyCategoryIcon(container: FrameLayout, iconText: TextView, category: VehicleCategory) {
        val style = categoryStyle(category)
        val ctx = container.context
        val bg = GradientDrawable()
        bg.shape = GradientDrawable.OVAL
        bg.setColor(ContextCompat.getColor(ctx, style.bgRes))
        container.background = bg
        iconText.text = style.abbr
        iconText.setTextColor(ContextCompat.getColor(ctx, style.colorRes))
    }

    fun statusLabel(status: TripStatus): String = when (status) {
        TripStatus.PENDING_APPROVAL -> "Pending"
        TripStatus.APPROVED -> "Approved"
        TripStatus.DEPOSIT_PAID -> "Deposit Paid"
        TripStatus.ASSIGNED -> "Assigned"
        TripStatus.EN_ROUTE -> "En Route"
        TripStatus.AT_PICKUP -> "At Pickup"
        TripStatus.IN_TRANSIT -> "In Transit"
        TripStatus.AT_DESTINATION -> "At Destination"
        TripStatus.DELIVERED -> "Delivered"
        TripStatus.CLOSED -> "Completed"
        TripStatus.REJECTED -> "Rejected"
        TripStatus.AUTO_CANCELLED -> "Cancelled"
        TripStatus.CANCELLED -> "Cancelled"
        else -> status.name.replace('_', ' ')
    }

    /** Customer-facing explanation of what is happening with their order. */
    fun customerOrderMessage(status: TripStatus): String = when (status) {
        TripStatus.PENDING_APPROVAL -> "Waiting for admin approval"
        TripStatus.APPROVED -> "Approved — please pay 10% deposit"
        TripStatus.DEPOSIT_PAID -> "Deposit paid — driver will start soon"
        TripStatus.ASSIGNED -> "Driver assigned to your trip"
        TripStatus.EN_ROUTE -> "Driver is on the way to pickup"
        TripStatus.AT_PICKUP -> "Driver at pickup — pay 50% now"
        TripStatus.IN_TRANSIT -> "Cargo in transit to destination"
        TripStatus.AT_DESTINATION -> "Arrived — pay final settlement"
        TripStatus.DELIVERED -> "Delivered successfully"
        TripStatus.CLOSED -> "Trip completed"
        TripStatus.REJECTED -> "Booking was rejected"
        TripStatus.CANCELLED, TripStatus.AUTO_CANCELLED -> "Booking cancelled"
        else -> statusLabel(status)
    }

    fun isActiveTrip(status: TripStatus): Boolean = status !in listOf(
        TripStatus.CLOSED, TripStatus.REJECTED,
        TripStatus.CANCELLED, TripStatus.AUTO_CANCELLED, TripStatus.DELIVERED
    )

    fun applyStatusChip(textView: TextView, status: TripStatus) {
        val ctx = textView.context
        textView.text = statusLabel(status)
        val (bgRes, colorRes) = when (status) {
            TripStatus.PENDING_APPROVAL -> R.drawable.bg_chip_pending to R.color.warning
            TripStatus.APPROVED, TripStatus.DEPOSIT_PAID -> R.drawable.bg_chip_success to R.color.success
            TripStatus.ASSIGNED, TripStatus.EN_ROUTE,
            TripStatus.AT_PICKUP, TripStatus.IN_TRANSIT,
            TripStatus.AT_DESTINATION -> R.drawable.bg_chip_transit to R.color.teal
            TripStatus.DELIVERED, TripStatus.CLOSED -> R.drawable.bg_chip_success to R.color.success
            TripStatus.REJECTED, TripStatus.AUTO_CANCELLED,
            TripStatus.CANCELLED -> R.drawable.bg_chip_error to R.color.error
            else -> R.drawable.bg_chip_default to R.color.info
        }
        textView.setBackgroundResource(bgRes)
        textView.setTextColor(ContextCompat.getColor(ctx, colorRes))
    }
}
