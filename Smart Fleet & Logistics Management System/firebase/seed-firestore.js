/**
 * Seed Firestore with vehicles and services for Sawarri project.
 *
 * Prerequisites:
 *   1. npm install firebase-admin (in firebase/functions or project root)
 *   2. Download service account key from Firebase Console
 *      → Project Settings → Service Accounts → Generate new private key
 *   3. Save as firebase/serviceAccountKey.json (DO NOT commit to git)
 *
 * Run:
 *   node firebase/seed-firestore.js
 */

const admin = require("firebase-admin");
const path = require("path");
const fs = require("fs");

const serviceAccountPath = path.join(__dirname, "serviceAccountKey.json");
if (!fs.existsSync(serviceAccountPath)) {
  console.error("Missing firebase/serviceAccountKey.json");
  console.error("Download from Firebase Console → Service Accounts");
  process.exit(1);
}

admin.initializeApp({
  credential: admin.credential.cert(require(serviceAccountPath)),
});
const db = admin.firestore();

const seedData = require("./seed-data.json");

async function seed() {
  console.log("Seeding vehicles...");
  for (const vehicle of seedData.vehicles) {
    await db.collection("vehicles").add(vehicle);
    console.log(`  + ${vehicle.registrationNumber}`);
  }

  console.log("Seeding services...");
  for (const service of seedData.services) {
    await db.collection("services").add(service);
    console.log(`  + ${service.name}`);
  }

  console.log("Done! Seeded", seedData.vehicles.length, "vehicles and", seedData.services.length, "services.");
  process.exit(0);
}

seed().catch((err) => {
  console.error(err);
  process.exit(1);
});
