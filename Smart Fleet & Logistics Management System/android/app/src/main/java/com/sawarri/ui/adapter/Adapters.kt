package com.sawarri.ui.adapter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.button.MaterialButton
import com.sawarri.R
import com.sawarri.data.model.Booking
import com.sawarri.data.model.Vehicle
import com.sawarri.data.model.VehicleCategory
import com.sawarri.util.UiHelper

class VehicleAdapter(
    private val onItemClick: (Vehicle) -> Unit = {}
) : RecyclerView.Adapter<VehicleAdapter.ViewHolder>() {

    private val items = mutableListOf<Vehicle>()

    fun submitList(list: List<Vehicle>) {
        items.clear()
        items.addAll(list)
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_vehicle_category, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(items[position], onItemClick)
    }

    override fun getItemCount() = items.size

    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val iconContainer: FrameLayout = itemView.findViewById(R.id.iconContainer)
        private val tvIcon: TextView = itemView.findViewById(R.id.tvVehicleIcon)
        private val tvName: TextView = itemView.findViewById(R.id.tvVehicleName)
        private val tvRate: TextView = itemView.findViewById(R.id.tvVehicleRate)

        fun bind(vehicle: Vehicle, onClick: (Vehicle) -> Unit) {
            UiHelper.applyCategoryIcon(iconContainer, tvIcon, vehicle.category)
            tvName.text = labelFor(vehicle.category, itemView.context)
            tvRate.text = itemView.context.getString(
                R.string.from_rate,
                vehicle.baseRate.toInt().toString()
            )
            itemView.setOnClickListener { onClick(vehicle) }
        }

        private fun labelFor(category: VehicleCategory, context: android.content.Context) =
            when (category) {
                VehicleCategory.BIKE -> context.getString(R.string.cat_bike)
                VehicleCategory.SMALL_VAN -> context.getString(R.string.cat_small_van)
                VehicleCategory.MEDIUM_TRUCK -> context.getString(R.string.cat_medium_truck)
                VehicleCategory.HEAVY_TRUCK -> context.getString(R.string.cat_heavy_truck)
                VehicleCategory.REFRIGERATED -> context.getString(R.string.cat_refrigerated)
            }
    }
}

class BookingAdapter(
    private val showActions: Boolean = false,
    private val onApprove: (Booking) -> Unit = {},
    private val onReject: (Booking) -> Unit = {},
    private val onItemClick: (Booking) -> Unit = {}
) : RecyclerView.Adapter<BookingAdapter.ViewHolder>() {

    private val items = mutableListOf<Booking>()

    fun submitList(list: List<Booking>) {
        items.clear()
        items.addAll(list)
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_booking, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(items[position], showActions, onApprove, onReject, onItemClick)
    }

    override fun getItemCount() = items.size

    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvId: TextView = itemView.findViewById(R.id.tvBookingId)
        private val tvRoute: TextView = itemView.findViewById(R.id.tvRoute)
        private val tvStatus: TextView = itemView.findViewById(R.id.tvStatus)
        private val tvAmount: TextView = itemView.findViewById(R.id.tvAmount)
        private val layoutActions: LinearLayout = itemView.findViewById(R.id.layoutActions)
        private val btnApprove: MaterialButton = itemView.findViewById(R.id.btnApprove)
        private val btnReject: MaterialButton = itemView.findViewById(R.id.btnReject)

        fun bind(
            booking: Booking,
            showActions: Boolean,
            onApprove: (Booking) -> Unit,
            onReject: (Booking) -> Unit,
            onItemClick: (Booking) -> Unit
        ) {
            val ctx = itemView.context
            tvId.text = ctx.getString(R.string.booking_id, booking.id.take(8).uppercase())
            tvRoute.text = "${booking.pickup.address}  →  ${booking.dropoff.address}"
            UiHelper.applyStatusChip(tvStatus, booking.status)
            tvAmount.text = ctx.getString(
                R.string.total_amount,
                String.format("%,d", booking.quote.total.toInt())
            )

            layoutActions.visibility = if (showActions) View.VISIBLE else View.GONE
            btnApprove.setOnClickListener { onApprove(booking) }
            btnReject.setOnClickListener { onReject(booking) }
            itemView.setOnClickListener { onItemClick(booking) }
        }
    }
}
