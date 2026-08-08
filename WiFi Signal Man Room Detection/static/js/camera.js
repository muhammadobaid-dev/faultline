(() => {
  const state = {
    devices: [],
    rooms: [],
    scannedAt: null,
    scanning: false,
    localIp: null,
    view: "grid",
    selectedMac: null,
  };

  const el = {
    clock: document.getElementById("clock"),
    viewTitle: document.getElementById("view-title"),
    quadView: document.getElementById("quad-view"),
    floorView: document.getElementById("floor-view"),
    floorRooms: document.getElementById("floor-rooms"),
    floorMarkers: document.getElementById("floor-markers"),
    floorStats: document.getElementById("floor-stats"),
    deviceList: document.getElementById("device-list"),
    unassignedList: document.getElementById("unassigned-list"),
    scanStatus: document.getElementById("scan-status"),
    scanMeta: document.getElementById("scan-meta"),
    footerLocal: document.getElementById("footer-local"),
    footerCount: document.getElementById("footer-count"),
    btnGrid: document.getElementById("btn-grid"),
    btnFloor: document.getElementById("btn-floor"),
    btnScan: document.getElementById("btn-scan"),
    form: document.getElementById("assign-form"),
    formMac: document.getElementById("form-mac"),
    formName: document.getElementById("form-name"),
    formPerson: document.getElementById("form-person"),
    formRoom: document.getElementById("form-room"),
  };

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function tickClock() {
    const now = new Date();
    const t = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    el.clock.textContent = t;
    document.querySelectorAll(".pane-ts").forEach((node) => {
      node.textContent = t;
    });
  }

  function iconFor(device) {
    if (device.person) return "P";
    if (device.is_local) return "PC";
    const icon = (device.icon || "").toLowerCase();
    if (icon === "phone") return "PH";
    if (icon === "laptop") return "LT";
    if (icon === "tv") return "TV";
    return "DV";
  }

  function signalHtml(bars) {
    const n = Math.max(0, Math.min(4, Number(bars) || 0));
    let html = '<div class="signal" title="Signal estimate">';
    for (let i = 1; i <= 4; i += 1) {
      html += `<span class="${i <= n ? "on" : ""}"></span>`;
    }
    html += "</div>";
    return html;
  }

  function setView(view) {
    state.view = view;
    const isGrid = view === "grid";
    el.quadView.classList.toggle("hidden", !isGrid);
    el.floorView.classList.toggle("hidden", isGrid);
    el.btnGrid.classList.toggle("active", isGrid);
    el.btnFloor.classList.toggle("active", !isGrid);
    el.viewTitle.textContent = isGrid ? "QUAD VIEW — ROOMS" : "FLOOR PLAN — COVERAGE";
  }

  function renderRoomsSelect() {
    const current = el.formRoom.value;
    el.formRoom.innerHTML = '<option value="unassigned">Unassigned</option>';
    state.rooms.forEach((room) => {
      const opt = document.createElement("option");
      opt.value = room.id;
      opt.textContent = room.name;
      el.formRoom.appendChild(opt);
    });
    if (current) el.formRoom.value = current;
  }

  function renderFloorRooms() {
    el.floorRooms.innerHTML = "";
    state.rooms.forEach((room) => {
      const div = document.createElement("div");
      div.className = "floor-room";
      div.style.left = `${room.x}%`;
      div.style.top = `${room.y}%`;
      div.style.width = `${room.w}%`;
      div.style.height = `${room.h}%`;
      div.innerHTML = `<span>${room.label || room.name}</span>`;
      el.floorRooms.appendChild(div);
    });
  }

  function roomById(id) {
    return state.rooms.find((r) => r.id === id);
  }

  function markerPosition(device, indexInRoom) {
    const room = roomById(device.room);
    if (!room) {
      return { left: 8 + (indexInRoom % 4) * 6, top: 92 };
    }
    const cols = 3;
    const col = indexInRoom % cols;
    const row = Math.floor(indexInRoom / cols);
    const left = room.x + 12 + col * ((room.w - 20) / cols);
    const top = room.y + 28 + row * 14;
    return {
      left: Math.min(room.x + room.w - 8, left),
      top: Math.min(room.y + room.h - 8, top),
    };
  }

  function renderQuad() {
    const panes = document.querySelectorAll(".cam-pane");
    panes.forEach((pane) => {
      const roomId = pane.dataset.room;
      const scene = pane.querySelector("[data-scene]");
      const countEl = pane.querySelector("[data-count]");
      const inRoom = state.devices.filter((d) => d.room === roomId);
      countEl.textContent = String(inRoom.length);
      if (!inRoom.length) {
        scene.innerHTML = '<div class="pane-empty">NO SIGNAL TARGETS</div>';
        return;
      }
      scene.innerHTML = inRoom
        .map(
          (d) => `
        <div class="marker" data-mac="${d.mac}">
          <div class="marker-dot ${d.person ? "person" : ""}">${iconFor(d)}</div>
          <div class="marker-name">${escapeHtml(d.display_name || d.hostname || d.mac)}</div>
          <div class="marker-sub">${escapeHtml(d.person || d.ip)}</div>
          ${signalHtml(d.signal_bars)}
        </div>`
        )
        .join("");
    });
  }

  function renderFloorMarkers() {
    el.floorMarkers.innerHTML = "";
    const byRoom = {};
    state.devices.forEach((d) => {
      const key = d.room || "unassigned";
      byRoom[key] = byRoom[key] || [];
      byRoom[key].push(d);
    });

    Object.entries(byRoom).forEach(([roomId, list]) => {
      list.forEach((device, idx) => {
        const pos = markerPosition(device, idx);
        if (roomId === "unassigned") {
          pos.left = 6 + (idx % 5) * 8;
          pos.top = 94;
        }
        const node = document.createElement("div");
        node.className = `floor-marker ${device.person ? "has-person" : ""}`;
        node.style.left = `${pos.left}%`;
        node.style.top = `${pos.top}%`;
        const label = device.person || device.display_name || device.mac.slice(-8);
        node.innerHTML = `<div class="dot"></div><div class="tag">${escapeHtml(label)}</div>`;
        node.title = `${device.display_name}\n${device.ip}\n${device.mac}`;
        el.floorMarkers.appendChild(node);
      });
    });

    el.floorStats.textContent = `${state.devices.length} devices`;
  }

  function renderDeviceList() {
    const prevSelected = state.selectedMac;
    el.deviceList.innerHTML = "";
    el.formMac.innerHTML = "";

    if (!state.devices.length) {
      el.deviceList.innerHTML = '<p class="panel-sub">No devices found yet. Click scan.</p>';
    }

    state.devices.forEach((d) => {
      const card = document.createElement("div");
      card.className = `device-card${prevSelected === d.mac ? " selected" : ""}`;
      card.dataset.mac = d.mac;
      const badgeClass = d.room === "unassigned" ? "badge warn" : "badge";
      card.innerHTML = `
        <h4>${escapeHtml(d.display_name || d.hostname || "Unknown")}</h4>
        <div class="meta">
          ${escapeHtml(d.ip)} · ${escapeHtml(d.mac)}<br/>
          ${d.person ? escapeHtml(d.person) + " · " : ""}${escapeHtml(d.room_name || "Unassigned")}
          ${d.is_local ? " · THIS PC" : ""}
        </div>
        <span class="${badgeClass}">${escapeHtml(d.room_label || "UNASSIGNED")}</span>
      `;
      card.addEventListener("click", () => selectDevice(d.mac));
      el.deviceList.appendChild(card);

      const opt = document.createElement("option");
      opt.value = d.mac;
      opt.textContent = `${d.display_name || d.hostname || d.mac} (${d.ip})`;
      el.formMac.appendChild(opt);
    });

    if (prevSelected) {
      const still = state.devices.find((d) => d.mac === prevSelected);
      if (still) fillForm(still);
      else if (state.devices[0]) selectDevice(state.devices[0].mac);
    } else if (state.devices[0]) {
      selectDevice(state.devices[0].mac);
    }

    const unassigned = state.devices.filter((d) => d.room === "unassigned");
    el.unassignedList.innerHTML = unassigned.length
      ? unassigned.map((d) => `${escapeHtml(d.ip)} · ${escapeHtml(d.mac)}`).join("<br/>")
      : "All devices assigned.";
  }

  function selectDevice(mac) {
    state.selectedMac = mac;
    document.querySelectorAll(".device-card").forEach((c) => {
      c.classList.toggle("selected", c.dataset.mac === mac);
    });
    const device = state.devices.find((d) => d.mac === mac);
    if (device) fillForm(device);
  }

  function fillForm(device) {
    el.formMac.value = device.mac;
    el.formName.value = device.display_name && device.display_name !== device.hostname ? device.display_name : device.display_name || "";
    // Prefer mapping name if equal to hostname still ok
    el.formName.value = device.display_name || "";
    el.formPerson.value = device.person || "";
    el.formRoom.value = device.room || "unassigned";
  }

  function updateStatus() {
    el.scanStatus.textContent = state.scanning ? "SCANNING" : "LIVE";
    el.scanStatus.classList.toggle("scanning", state.scanning);
    el.scanStatus.classList.toggle("live", !state.scanning);
    const when = state.scannedAt ? new Date(state.scannedAt).toLocaleTimeString() : "—";
    el.scanMeta.textContent = `Last scan: ${when} · ${state.devices.length} online`;
    el.footerLocal.textContent = `Local IP: ${state.localIp || "—"}`;
    el.footerCount.textContent = `${state.devices.length} online`;
  }

  function applyPayload(payload) {
    state.devices = payload.devices || [];
    state.scannedAt = payload.scanned_at;
    state.scanning = !!payload.scanning;
    state.localIp = payload.local_ip;
    renderQuad();
    renderFloorMarkers();
    renderDeviceList();
    updateStatus();
  }

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function loadRooms() {
    const res = await fetch("/api/rooms");
    const data = await res.json();
    state.rooms = data.rooms || [];
    renderRoomsSelect();
    renderFloorRooms();
  }

  async function loadDevices() {
    const res = await fetch("/api/devices");
    const data = await res.json();
    applyPayload(data);
  }

  async function triggerScan() {
    el.btnScan.classList.add("spinning");
    state.scanning = true;
    updateStatus();
    try {
      const res = await fetch("/api/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ping_sweep: true }),
      });
      const data = await res.json();
      applyPayload(data);
    } catch (err) {
      console.error(err);
      el.scanMeta.textContent = "Scan failed — check server console";
    } finally {
      el.btnScan.classList.remove("spinning");
    }
  }

  el.btnGrid.addEventListener("click", () => setView("grid"));
  el.btnFloor.addEventListener("click", () => setView("floor"));
  el.btnScan.addEventListener("click", () => triggerScan());

  el.formMac.addEventListener("change", () => {
    selectDevice(el.formMac.value);
  });

  el.form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const mac = el.formMac.value;
    if (!mac) return;
    const body = {
      name: el.formName.value.trim(),
      person: el.formPerson.value.trim(),
      room: el.formRoom.value,
      icon: el.formPerson.value.trim() ? "phone" : "device",
    };
    const res = await fetch(`/api/devices/${encodeURIComponent(mac)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    applyPayload(data);
    state.selectedMac = mac;
    selectDevice(mac);
  });

  // Socket.IO live updates
  const socket = io({ transports: ["websocket", "polling"] });
  socket.on("devices_update", (payload) => applyPayload(payload));
  socket.on("connect", () => {
    el.scanStatus.textContent = "LIVE";
    el.scanStatus.classList.add("live");
  });

  tickClock();
  setInterval(tickClock, 1000);
  setView("grid");

  loadRooms()
    .then(loadDevices)
    .catch((err) => {
      console.error(err);
      el.scanMeta.textContent = "Failed to load data";
    });
})();
