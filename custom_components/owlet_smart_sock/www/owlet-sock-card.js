/*
 * Owlet Smart Sock UI - custom Lovelace card
 * Part of https://github.com/AlexShubovich/ha-owlet-integration
 *
 * Shows a single sock's status, heart rate, oxygen, movement and battery in
 * one compact, theme-aware card. It is registered automatically by the
 * integration, so you only need:
 *
 *   type: custom:owlet-sock-card
 *   entity: sensor.<your_device>_status
 */

const VITAL_SUFFIXES = {
  heart_rate: "_heart_rate",
  oxygen: "_oxygen_saturation",
  movement: "_movement",
  battery: "_battery",
};

const STATUS_META = {
  monitoring: { label: "Monitoring", color: "var(--success-color, #43a047)", icon: "mdi:baby-face-outline" },
  charging: { label: "Charging", color: "var(--info-color, #039be5)", icon: "mdi:battery-charging" },
  charged: { label: "Charged", color: "var(--info-color, #039be5)", icon: "mdi:battery" },
  no_signal: { label: "No signal", color: "var(--warning-color, #ffa600)", icon: "mdi:signal-off" },
  disconnected: { label: "Disconnected", color: "var(--disabled-color, #9e9e9e)", icon: "mdi:lan-disconnect" },
  error: { label: "Error", color: "var(--error-color, #db4437)", icon: "mdi:alert-circle" },
  unknown: { label: "Unknown", color: "var(--disabled-color, #9e9e9e)", icon: "mdi:help-circle" },
};

class OwletSockCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("You must set 'entity' to one of the sock's sensors (ideally the Status sensor, e.g. sensor.owlet_..._status).");
    }
    this._config = config;
    this._refined = false;
    this._resolve();
    this._build();
  }

  _resolve() {
    // Initial guess from the entity id prefix; refined from the device
    // registry once hass is available (see _refineFromDevice).
    const c = this._config;
    const prefix = c.entity.replace(/_status$/, "");
    this._entities = {
      status: c.entity,
      heart_rate: c.heart_rate || prefix + VITAL_SUFFIXES.heart_rate,
      oxygen: c.oxygen || prefix + VITAL_SUFFIXES.oxygen,
      movement: c.movement || prefix + VITAL_SUFFIXES.movement,
      battery: c.battery || prefix + VITAL_SUFFIXES.battery,
    };
  }

  _refineFromDevice() {
    // Resolve siblings via the device registry, so the user only has to pick
    // one entity and any ``_2`` style renames are handled correctly.
    if (!this._hass || !this._hass.entities) return;
    const reg = this._hass.entities[this._config.entity];
    const deviceId = reg && reg.device_id;
    if (!deviceId) return;

    const found = {};
    for (const eid of Object.keys(this._hass.entities)) {
      if (this._hass.entities[eid].device_id !== deviceId) continue;
      for (const [key, suf] of Object.entries(VITAL_SUFFIXES)) {
        if (eid.endsWith(suf)) found[key] = eid;
      }
      if (eid.endsWith("_status")) found.status = eid;
    }

    const c = this._config;
    if (!c.entity.endsWith("_status") && found.status) {
      this._entities.status = found.status;
    }
    this._entities.heart_rate = c.heart_rate || found.heart_rate || this._entities.heart_rate;
    this._entities.oxygen = c.oxygen || found.oxygen || this._entities.oxygen;
    this._entities.movement = c.movement || found.movement || this._entities.movement;
    this._entities.battery = c.battery || found.battery || this._entities.battery;
    this._refined = true;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._refined) this._refineFromDevice();
    this._update();
  }

  _st(entityId) {
    const s = this._hass && this._hass.states[entityId];
    return s ? s.state : undefined;
  }

  _num(entityId) {
    const v = this._st(entityId);
    if (v === undefined || v === "unknown" || v === "unavailable" || v === "" || v === null) {
      return null;
    }
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  _build() {
    if (this._card) return;
    this._card = document.createElement("ha-card");
    this._content = document.createElement("div");
    this._content.className = "owlet-content";
    this._card.appendChild(this._content);

    const style = document.createElement("style");
    style.textContent = `
      ha-card { padding: 16px; }
      .owlet-header { display:flex; align-items:center; gap:10px; margin-bottom:14px; }
      .owlet-header ha-icon { --mdc-icon-size: 26px; }
      .owlet-title { font-size: 1.1rem; font-weight: 500; flex: 1; }
      .owlet-badge { font-size: .8rem; font-weight: 600; padding: 3px 10px; border-radius: 12px;
                     color: #fff; white-space: nowrap; }
      .owlet-grid { display:grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
      .owlet-tile { display:flex; align-items:center; gap:10px; padding:12px;
                    border-radius: 12px; background: var(--secondary-background-color); }
      .owlet-tile ha-icon { --mdc-icon-size: 28px; color: var(--state-icon-color); }
      .owlet-tile.hr ha-icon { color: var(--error-color, #db4437); }
      .owlet-tile.ox ha-icon { color: var(--info-color, #039be5); }
      .owlet-vals { display:flex; flex-direction:column; line-height:1.15; }
      .owlet-value { font-size: 1.5rem; font-weight: 600; }
      .owlet-value small { font-size: .8rem; font-weight: 400; color: var(--secondary-text-color); }
      .owlet-label { font-size: .75rem; color: var(--secondary-text-color); }
      .owlet-alerts { margin-top: 12px; display:flex; flex-wrap:wrap; gap:6px; }
      .owlet-alert { font-size:.72rem; font-weight:600; padding:3px 8px; border-radius:10px;
                     background: var(--error-color, #db4437); color:#fff; }
      .owlet-pulse { animation: owletpulse 1.1s ease-in-out infinite; }
      @keyframes owletpulse { 0%,100% { transform: scale(1);} 50% { transform: scale(1.18);} }
    `;
    this._card.appendChild(style);
    this.innerHTML = "";
    this.appendChild(this._card);
  }

  _tile(cls, icon, value, unit, label, pulse) {
    const v = value === null || value === undefined ? "—" : value;
    const u = unit && v !== "—" ? ` <small>${unit}</small>` : "";
    const pc = pulse && v !== "—" ? " owlet-pulse" : "";
    return `
      <div class="owlet-tile ${cls}">
        <ha-icon class="${pc}" icon="${icon}"></ha-icon>
        <div class="owlet-vals">
          <span class="owlet-value">${v}${u}</span>
          <span class="owlet-label">${label}</span>
        </div>
      </div>`;
  }

  _update() {
    if (!this._hass || !this._content) return;

    const statusState = this._st(this._entities.status);
    const meta = STATUS_META[statusState] || STATUS_META.unknown;
    const title = this._config.name
      || (this._hass.states[this._entities.status]
          && this._hass.states[this._entities.status].attributes.friendly_name)
      || "Owlet Smart Sock";

    const monitoring = statusState === "monitoring";
    const hr = this._num(this._entities.heart_rate);
    const ox = this._num(this._entities.oxygen);
    const mv = this._num(this._entities.movement);
    const bat = this._num(this._entities.battery);

    // Active alerts, read from the Status sensor's attributes.
    const statusObj = this._hass.states[this._entities.status];
    const active = (statusObj && statusObj.attributes && statusObj.attributes.active_alerts) || [];
    const alertHtml = active.length
      ? `<div class="owlet-alerts">${active
          .map((a) => `<span class="owlet-alert">${String(a).replace(/_/g, " ")}</span>`)
          .join("")}</div>`
      : "";

    this._content.innerHTML = `
      <div class="owlet-header">
        <ha-icon icon="${meta.icon}" style="color:${meta.color}"></ha-icon>
        <span class="owlet-title">${title}</span>
        <span class="owlet-badge" style="background:${meta.color}">${meta.label}</span>
      </div>
      <div class="owlet-grid">
        ${this._tile("hr", "mdi:heart-pulse", hr, "bpm", "Heart rate", monitoring)}
        ${this._tile("ox", "mdi:lungs", ox, "%", "Oxygen", false)}
        ${this._tile("mv", "mdi:run", mv, "%", "Movement", false)}
        ${this._tile("bat", "mdi:battery", bat, "%", "Battery", false)}
      </div>
      ${alertHtml}
    `;

    // Make the header clickable -> opens the Status entity's more-info dialog.
    const header = this._content.querySelector(".owlet-header");
    header.style.cursor = "pointer";
    header.onclick = () => {
      const ev = new Event("hass-more-info", { bubbles: true, composed: true });
      ev.detail = { entityId: this._entities.status };
      this.dispatchEvent(ev);
    };
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig(hass) {
    const status = Object.keys(hass.states).find((e) => e.endsWith("_status") && e.startsWith("sensor."));
    return { type: "custom:owlet-sock-card", entity: status || "sensor.owlet_smart_sock_status" };
  }

  static getConfigElement() {
    return document.createElement("owlet-sock-card-editor");
  }
}

/* Visual editor: a simple ha-form with an entity picker so the sock can be
 * chosen from a dropdown instead of being typed. */
const EDITOR_SCHEMA = [
  {
    name: "entity",
    required: true,
    selector: { entity: { integration: "owlet_smart_sock", domain: "sensor" } },
  },
  { name: "name", selector: { text: {} } },
];
const EDITOR_LABELS = {
  entity: "Sock Status sensor",
  name: "Card name (optional)",
};

class OwletSockCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: ev.detail.value },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = EDITOR_SCHEMA;
    this._form.data = this._config;
    this._form.computeLabel = (s) => EDITOR_LABELS[s.name] || s.name;
  }
}

if (!customElements.get("owlet-sock-card-editor")) {
  customElements.define("owlet-sock-card-editor", OwletSockCardEditor);
}

// Guard against being loaded twice (e.g. both auto-registered and added as a
// manual dashboard resource) - a second define() would throw.
if (!customElements.get("owlet-sock-card")) {
  customElements.define("owlet-sock-card", OwletSockCard);
}

// Make the card appear in the dashboard "Add card" picker.
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "owlet-sock-card")) {
  window.customCards.push({
    type: "owlet-sock-card",
    name: "Owlet Smart Sock",
    description: "Heart rate, oxygen, movement, battery and status for an Owlet sock.",
    preview: true,
    documentationURL: "https://github.com/AlexShubovich/ha-owlet-integration",
  });
}

console.info("%c OWLET-SOCK-CARD %c loaded ", "background:#039be5;color:#fff;border-radius:3px 0 0 3px;padding:2px 4px", "background:#333;color:#fff;border-radius:0 3px 3px 0;padding:2px 4px");
