import * as functions from "firebase-functions";
import * as admin from "firebase-admin";

admin.initializeApp();
const db = admin.firestore();

// ─── Auto-Cancel Unpaid Bookings (runs every hour) ───────────────────
export const checkDepositDeadline = functions.pubsub
  .schedule("every 1 hours")
  .onRun(async () => {
    const now = admin.firestore.Timestamp.now();
    const snapshot = await db
      .collection("bookings")
      .where("status", "==", "APPROVED")
      .where("depositDeadline", "<", now)
      .get();

    const batch = db.batch();
    const notifications: Promise<void>[] = [];

    snapshot.forEach((doc) => {
      const booking = doc.data();
      if (booking.payments?.deposit?.status !== "completed") {
        batch.update(doc.ref, { status: "AUTO_CANCELLED" });

        if (booking.assignedVehicleId) {
          batch.update(
            db.collection("vehicles").doc(booking.assignedVehicleId),
            { status: "available", assignedDriverId: null }
          );
        }

        notifications.push(
          sendNotification(
            booking.customerId,
            "Booking Auto-Cancelled",
            `Booking #${doc.id} cancelled — deposit not paid within 24 hours.`,
            "auto_cancelled",
            doc.id
          )
        );
      }
    });

    await batch.commit();
    await Promise.all(notifications);
    functions.logger.info(`Processed ${snapshot.size} expired bookings`);
  });

// ─── Send Notification on Booking Status Change ─────────────────────
export const onBookingStatusChange = functions.firestore
  .document("bookings/{bookingId}")
  .onUpdate(async (change, context) => {
    const before = change.before.data();
    const after = change.after.data();
    const bookingId = context.params.bookingId;

    if (before.status === after.status) return;

    const statusMessages: Record<string, string> = {
      APPROVED: "Your booking has been approved. Pay 10% deposit within 24 hours.",
      DEPOSIT_PAID: "Deposit received. Driver will be assigned shortly.",
      ASSIGNED: `Driver assigned to your shipment #${bookingId}.`,
      EN_ROUTE: "Driver is on the way to pickup location.",
      AT_PICKUP: "Driver arrived at pickup. Please complete 50% payment.",
      IN_TRANSIT: "Your shipment is on the way!",
      AT_DESTINATION: "Driver arrived at destination.",
      DELIVERED: "Shipment delivered. Please sign Proof of Delivery.",
      CLOSED: `Trip #${bookingId} completed successfully.`,
      AUTO_CANCELLED: "Booking auto-cancelled due to unpaid deposit.",
      REJECTED: "Your booking request was rejected.",
    };

    const message = statusMessages[after.status];
    if (message) {
      await sendNotification(
        after.customerId,
        `Booking Update — ${after.status}`,
        message,
        "status_update",
        bookingId
      );
    }
  });

// ─── Calculate Quote (Callable Function) ───────────────────────────
export const calculateQuote = functions.https.onCall(async (data) => {
  const {
    vehicleCategory,
    distanceKm,
    weightKg,
    lengthM,
    widthM,
    heightM,
    selectedServiceIds,
    urgency,
  } = data;

  const vehicleRates: Record<string, { base: number; perKm: number }> = {
    bike: { base: 500, perKm: 15 },
    small_van: { base: 2000, perKm: 25 },
    medium_truck: { base: 5000, perKm: 40 },
    heavy_truck: { base: 10000, perKm: 60 },
    refrigerated: { base: 8000, perKm: 55 },
  };

  const rates = vehicleRates[vehicleCategory] || vehicleRates.small_van;
  const baseRate = rates.base;
  const distanceCost = distanceKm * rates.perKm;
  const weightCost = Math.max(0, weightKg - 100) * 5;
  const volumeCost = lengthM * widthM * heightM * 200;

  let serviceCost = 0;
  if (selectedServiceIds?.length > 0) {
    const servicesSnap = await db
      .collection("services")
      .where(admin.firestore.FieldPath.documentId(), "in", selectedServiceIds)
      .get();
    servicesSnap.forEach((doc) => {
      serviceCost += doc.data().price || 0;
    });
  }

  const subtotal = baseRate + distanceCost + weightCost + volumeCost + serviceCost;
  const urgencyMultiplier = urgency === "express" ? 1.5 : 1.0;
  const total = Math.round(subtotal * urgencyMultiplier);

  return {
    baseRate,
    distanceCost,
    weightCost,
    volumeCost,
    serviceCost,
    urgencyMultiplier,
    total,
  };
});

// ─── Helper: Send FCM Notification ─────────────────────────────────
async function sendNotification(
  userId: string,
  title: string,
  body: string,
  type: string,
  bookingId?: string
): Promise<void> {
  await db.collection("notifications").add({
    userId,
    title,
    body,
    type,
    bookingId: bookingId || null,
    isRead: false,
    createdAt: admin.firestore.FieldValue.serverTimestamp(),
  });

  const userDoc = await db.collection("users").doc(userId).get();
  const fcmToken = userDoc.data()?.fcmToken;
  if (fcmToken) {
    await admin.messaging().send({
      token: fcmToken,
      notification: { title, body },
      data: { type, bookingId: bookingId || "" },
    });
  }
}
