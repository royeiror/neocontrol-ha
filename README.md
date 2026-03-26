[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories)
# Neocontrol & Somfy Inteo Gateway for Home Assistant

A **Custom Component** for Home Assistant that enables control of Somfy/Neocontrol RTS shutters managed by the Neocontrol Inteo Station V2 gateway. 

This integration supports both **Local LAN control** and **Cloud MQTT control** with **Real-Time State Feedback**.

## 🚀 Features
- **UI-Based Configuration**: Full Config Flow support. No YAML editing required!
- **Dual-Transport (Hybrid Mode)**: Automatically uses both Local UDP (LAN) and Cloud MQTT for maximum reliability and speed.
- **Real-Time Status**: Listens for feedback from the gateway to update shutter icons in Home Assistant the moment they move.
- **Custom Branding**: Includes official-style Somfy icons and logos for a premium dashboard look.
- **Async Powered**: Built with modern Home Assistant best practices for high performance.

## ⚠️ Prerequisites
1. **Initial Setup**: Your Inteo Station V2 gateway **must** be fully set up and working in the official **inteO** app on your phone.
2. **Sniffed Payloads**: You will need to sniff the hex payloads for your shutters once. The integration provides a built-in guide for this.

## 📦 Installation

### Method 1: HACS (Recommended)
1. Open Home Assistant and navigate to **HACS**.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Paste: `https://github.com/royeiror/neocontrol-ha`
4. Select **Integration** as the category and click **Add**.
5. Restart Home Assistant.

### Method 2: Manual
1. Download this repository.
2. Copy the `custom_components/neocontrol` folder into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.

## ⚙️ Setup
1. Go to **Settings -> Devices & Services**.
2. Click **Add Integration** and search for **Neocontrol**.
3. Enter your Gateway's MAC Address (found on the bottom of the device).
4. Enter the **Name** and **Hex Payloads** (Open/Close/Stop) for your shutters.
   - *Tip: Use [MQTT X](https://mqttx.app/) to sniff these codes from your phone app.*

## 🛠️ Advanced: Sniffing Hex Payloads
To find your shutter codes:
1. Connect **MQTT X** to `iot.neocontrolglobal.com:9420`.
2. Use credentials: `NM8Y6tUQ9SZcp6bx` / `LFuBH4hsVnbBC98n` (SSL enabled).
3. Subscribe to `neo/conn/+/app`.
4. Press a button in the **inteO** app and copy the **Hex** message.
   - Example: `001c0000000000000044d5f2c11cbc02c8000000000c0100020001fb`

---
*Disclaimer: This integration is not officially affiliated with Somfy or Neocontrol. Use at your own risk.*
