package com.sawarri.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sawarri.data.model.*
import com.sawarri.data.repository.*
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class AuthViewModel(
    private val authRepository: AuthRepository = AuthRepository()
) : ViewModel() {

    private val _authState = MutableStateFlow<AuthState>(AuthState.Idle)
    val authState: StateFlow<AuthState> = _authState.asStateFlow()

    private val _currentUser = MutableStateFlow<User?>(null)
    val currentUser: StateFlow<User?> = _currentUser.asStateFlow()

    fun login(identifier: String, password: String) {
        viewModelScope.launch {
            _authState.value = AuthState.Loading
            authRepository.login(identifier, password)
                .onSuccess { user ->
                    _currentUser.value = user
                    _authState.value = AuthState.Success(user)
                }
                .onFailure { _authState.value = AuthState.Error(it.message ?: "Login failed") }
        }
    }

    fun register(
        name: String,
        username: String,
        email: String,
        password: String,
        address: String,
        phone: String,
        role: UserRole
    ) {
        viewModelScope.launch {
            _authState.value = AuthState.Loading
            authRepository.register(name, username, email, password, address, phone, role)
                .onSuccess { user ->
                    _currentUser.value = user
                    _authState.value = AuthState.Success(user)
                }
                .onFailure { _authState.value = AuthState.Error(it.message ?: "Registration failed") }
        }
    }

    fun updateProfile(name: String, username: String, address: String, phone: String) {
        viewModelScope.launch {
            _authState.value = AuthState.Loading
            authRepository.updateRegistrationInfo(name, username, address, phone)
                .onSuccess { user ->
                    _currentUser.value = user
                    _authState.value = AuthState.Success(user)
                }
                .onFailure { _authState.value = AuthState.Error(it.message ?: "Update failed") }
        }
    }

    fun logout() {
        authRepository.logout()
        _currentUser.value = null
        _authState.value = AuthState.Idle
    }

    fun resetState() {
        _authState.value = AuthState.Idle
    }

    fun checkSession() {
        viewModelScope.launch {
            _authState.value = AuthState.Loading
            val userId = authRepository.currentUserId
            if (userId == null) {
                _authState.value = AuthState.NoSession
                return@launch
            }
            authRepository.getUserProfile(userId)
                .onSuccess { user ->
                    _currentUser.value = user
                    _authState.value = AuthState.Success(user)
                }
                .onFailure {
                    _authState.value = AuthState.NoSession
                }
        }
    }
}

sealed class AuthState {
    object Idle : AuthState()
    object Loading : AuthState()
    object NoSession : AuthState()
    data class Success(val user: User) : AuthState()
    data class Error(val message: String) : AuthState()
}

class BookingViewModel(
    private val bookingRepository: BookingRepository = BookingRepository(),
    private val vehicleRepository: VehicleRepository = VehicleRepository()
) : ViewModel() {

    private val _bookings = MutableStateFlow<List<Booking>>(emptyList())
    val bookings: StateFlow<List<Booking>> = _bookings.asStateFlow()

    private val _quote = MutableStateFlow<Quote?>(null)
    val quote: StateFlow<Quote?> = _quote.asStateFlow()

    private val _bookingState = MutableStateFlow<BookingState>(BookingState.Idle)
    val bookingState: StateFlow<BookingState> = _bookingState.asStateFlow()

    private val _vehicles = MutableStateFlow<List<Vehicle>>(emptyList())
    val vehicles: StateFlow<List<Vehicle>> = _vehicles.asStateFlow()

    private val _services = MutableStateFlow<List<Service>>(emptyList())
    val services: StateFlow<List<Service>> = _services.asStateFlow()

    private var bookingsJob: kotlinx.coroutines.Job? = null

    fun loadCustomerBookings(customerId: String) {
        bookingsJob?.cancel()
        bookingsJob = viewModelScope.launch {
            bookingRepository.getCustomerBookings(customerId).collect {
                _bookings.value = it
            }
        }
    }

    fun loadDriverBookings(driverId: String) {
        bookingsJob?.cancel()
        bookingsJob = viewModelScope.launch {
            bookingRepository.getDriverBookings(driverId).collect {
                _bookings.value = it
            }
        }
    }

    fun loadVehicles(category: VehicleCategory? = null) {
        viewModelScope.launch {
            vehicleRepository.getAvailableVehicles(category).collect {
                _vehicles.value = it
            }
        }
    }

    fun loadServices() {
        viewModelScope.launch {
            vehicleRepository.getServices()
                .onSuccess { _services.value = it }
        }
    }

    fun calculateQuote(
        vehicleCategory: String, distanceKm: Double, weightKg: Double,
        lengthM: Double, widthM: Double, heightM: Double,
        selectedServiceIds: List<String>, urgency: String,
        services: List<Service> = emptyList()
    ) {
        viewModelScope.launch {
            _bookingState.value = BookingState.Loading
            bookingRepository.getQuote(
                vehicleCategory, distanceKm, weightKg,
                lengthM, widthM, heightM, selectedServiceIds, urgency
            ).onSuccess { quote ->
                _quote.value = quote
                _bookingState.value = BookingState.QuoteReady(quote)
            }.onFailure {
                val quote = bookingRepository.getQuoteLocal(
                    vehicleCategory, distanceKm, weightKg,
                    lengthM, widthM, heightM,
                    services.filter { selectedServiceIds.contains(it.id) },
                    urgency
                )
                _quote.value = quote
                _bookingState.value = BookingState.QuoteReady(quote)
            }
        }
    }

    fun submitBooking(booking: Booking) {
        viewModelScope.launch {
            _bookingState.value = BookingState.Loading
            bookingRepository.createBooking(booking)
                .onSuccess { id ->
                    _bookingState.value = BookingState.Submitted(id)
                }
                .onFailure {
                    _bookingState.value = BookingState.Error(it.message ?: "Submission failed")
                }
        }
    }
}

sealed class BookingState {
    object Idle : BookingState()
    object Loading : BookingState()
    data class QuoteReady(val quote: Quote) : BookingState()
    data class Submitted(val bookingId: String) : BookingState()
    data class Error(val message: String) : BookingState()
}

class TrackingViewModel(
    private val trackingRepository: TrackingRepository = TrackingRepository(),
    private val bookingRepository: BookingRepository = BookingRepository()
) : ViewModel() {

    private val _trackingData = MutableStateFlow<TrackingData?>(null)
    val trackingData: StateFlow<TrackingData?> = _trackingData.asStateFlow()

    private val _booking = MutableStateFlow<Booking?>(null)
    val booking: StateFlow<Booking?> = _booking.asStateFlow()

    fun loadTracking(bookingId: String) {
        viewModelScope.launch {
            bookingRepository.getBookingById(bookingId).onSuccess { _booking.value = it }
            trackingRepository.observeTracking(bookingId).collect {
                _trackingData.value = it
            }
        }
    }
}

class PaymentViewModel(
    private val paymentRepository: PaymentRepository = PaymentRepository(),
    private val bookingRepository: BookingRepository = BookingRepository()
) : ViewModel() {

    private val _paymentState = MutableStateFlow<PaymentState>(PaymentState.Idle)
    val paymentState: StateFlow<PaymentState> = _paymentState.asStateFlow()

    private val _booking = MutableStateFlow<Booking?>(null)
    val booking: StateFlow<Booking?> = _booking.asStateFlow()

    private val _payments = MutableStateFlow<List<Payment>>(emptyList())
    val payments: StateFlow<List<Payment>> = _payments.asStateFlow()

    fun loadPaymentData(bookingId: String) {
        viewModelScope.launch {
            bookingRepository.getBookingById(bookingId).onSuccess { _booking.value = it }
            paymentRepository.getPaymentsForBooking(bookingId).collect {
                _payments.value = it
            }
        }
    }

    fun payPhase(booking: Booking, phase: PaymentPhase, gatewayRef: String) {
        viewModelScope.launch {
            _paymentState.value = PaymentState.Loading
            val amount = paymentRepository.getPaymentAmount(booking.quote, phase)
            paymentRepository.completePayment(
                booking.id, phase, amount, booking.customerId, gatewayRef
            ).onSuccess {
                bookingRepository.getBookingById(booking.id).onSuccess { _booking.value = it }
                _paymentState.value = PaymentState.Completed(phase.name)
            }.onFailure {
                _paymentState.value = PaymentState.Error(it.message ?: "Payment failed")
            }
        }
    }

    fun resetPaymentState() {
        _paymentState.value = PaymentState.Idle
    }

    fun getAmount(quote: Quote, phase: PaymentPhase) =
        paymentRepository.getPaymentAmount(quote, phase)

    fun isPhasePaid(phase: PaymentPhase): Boolean =
        _payments.value.any { it.phase == phase && it.status == PaymentStatus.COMPLETED }
}

sealed class PaymentState {
    object Idle : PaymentState()
    object Loading : PaymentState()
    data class Completed(val phase: String) : PaymentState()
    data class Error(val message: String) : PaymentState()
}

class AdminViewModel(
    private val adminRepository: AdminRepository = AdminRepository()
) : ViewModel() {

    private val _pendingBookings = MutableStateFlow<List<Booking>>(emptyList())
    val pendingBookings: StateFlow<List<Booking>> = _pendingBookings.asStateFlow()

    private val _activeBookings = MutableStateFlow<List<Booking>>(emptyList())
    val activeBookings: StateFlow<List<Booking>> = _activeBookings.asStateFlow()

    private val _adminMessage = MutableStateFlow<String?>(null)
    val adminMessage: StateFlow<String?> = _adminMessage.asStateFlow()

    fun loadDashboard() {
        viewModelScope.launch {
            launch {
                adminRepository.getPendingBookings().collect { _pendingBookings.value = it }
            }
            launch {
                adminRepository.getActiveBookings().collect { _activeBookings.value = it }
            }
        }
    }

    fun approveBooking(bookingId: String) {
        viewModelScope.launch {
            adminRepository.approveBooking(bookingId)
                .onSuccess { _adminMessage.value = "Approved — driver assigned. Customer ab deposit pay kare." }
                .onFailure { _adminMessage.value = it.message ?: "Approve failed" }
        }
    }

    fun rejectBooking(bookingId: String) {
        viewModelScope.launch {
            adminRepository.rejectBooking(bookingId)
                .onSuccess { _adminMessage.value = "Booking rejected" }
                .onFailure { _adminMessage.value = it.message ?: "Reject failed" }
        }
    }

    fun consumeMessage() {
        _adminMessage.value = null
    }
}
