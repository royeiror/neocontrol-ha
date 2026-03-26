[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories)
# Neocontrol & Somfy Inteo Gateway for Home Assistant

A **Custom Component** for Home Assistant that enables control of Somfy/Neocontrol RTS shutters managed by the Neocontrol Cloud gateway. 

This integration bypasses the mobile app and natively communicates with the `iot.neocontrolglobal.com` AWS MQTT broker using the proprietary binary protocol we reverse-engineered.

## ⚠️ Prerequisites
1. **Initial Setup**: Your Inteo Station V2 gateway **must** be fully set up and working in the official **inteO** app on your phone before adding it to Home Assistant.
2. **Account Access**: You do not need to share your personal email/password for this integration; it uses global master credentials extracted from the app.

## 📍 Finding your Box MAC Address
You will need your Gateway's MAC address for the configuration. 
*   **Physically**: Look for a sticker on the bottom or back of the Inteo Station V2. The MAC is a 12-character hex string (e.g., `44D5F2C11CBC`).
*   **Sniffing**: If the sticker is missing, use the **MQTT X** sniffing method below. The MAC address will appear as part of the MQTT topic name (`neo/conn/[MAC]/app`).

## Features
- Direct cloud control of Somfy/Neocontrol Shutters (Open, Close, Stop).
- No middleman local bridge servers required. Uses Home Assistant natively.
- Compatible with HACS for easy installation and updates.

## Installation

### Method 1: HACS (Recommended)
1. **Easy Install**: Click the button below to add this repository to HACS:
   
   [![Open your Home Assistant instance and open a repository maintainer's GitHub repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=royeiror&repository=neocontrol-ha&category=integration)

2. **Manual HACS Add**: 
   * Open Home Assistant and navigate to **HACS**.
   * Click the three dots in the top right corner and select **Custom repositories**.
   * Paste the URL of this repository (`https://github.com/royeiror/neocontrol-ha`) and select **Integration** as the category.
   * Click **Add** and then download the `Neocontrol` integration.
3. Restart Home Assistant.

### Method 2: Manual
1. Download this repository.
2. Copy the `custom_components/neocontrol` folder into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.

---

## Configuration

Since Neocontrol uses a proprietary binary protocol heavily tied to your specific Gateway's MAC Address and a dynamic sequence number, you must "sniff" the hex payloads that your physical phone sends to the broker in order to configure this integration. 

Don't worry, using modern tools like **MQTT X** makes this process very easy!

### Step 1: Find your Hex Payloads
The easiest way to find your shutter codes is using **[MQTT X](https://mqttx.app/)**, a modern and free MQTT client that handles binary data perfectly.

1. Download and open [MQTT X](https://mqttx.app/).
2. Create a **New Connection** with these exact details:
   - **Name:** `Neocontrol`
   - **Host:** `mqtts://iot.neocontrolglobal.com`
   - **Port:** `9420`
   - **Username:** `NM8Y6tUQ9SZcp6bx`
   - **Password:** `LFuBH4hsVnbBC98n`
   - **SSL/TLS:** `true` (Uncheck "SSL Secure" if you get certificate errors)
3. Click **Connect**.
4. Click **New Subscription** and enter the topic: `neo/conn/+/app`.
5. **Important**: In the message window, change the display format from **Plaintext** to **Hex**.
6. Open your physical Neocontrol App on your phone and press **Open**, **Stop**, and **Close** for your shutter.
7. Copy the **Hex** strings that appear!
*(For example, your payload will look like: `001c0000000000000044d5f2c11cbc02c8000000000c0100020001fb`)*

### Step 2: Update `configuration.yaml`
Add the following block to your `configuration.yaml` file in Home Assistant.

```yaml
neocontrol:
  box_mac: "YOUR_BOX_MAC_ADDRESS" # Example: 44D5F2C11CBC
  shutters:
    - name: "Living Room Window"
      payload_open: "YOUR_SNIFFED_OPEN_HEX_STRING_HERE"
      payload_close: "YOUR_SNIFFED_CLOSE_HEX_STRING_HERE"
      payload_stop: "YOUR_SNIFFED_STOP_HEX_STRING_HERE"
```

**Important**: 
- If your sniffed code contains a rolling sequence number, the integration automatically injects the rolling sequence number at byte 16 so the server doesn't reject your commands!
- You can optionally replace your MAC Address and Sequence number in the hex string with `{mac}` and `{seq}` respectively if you want to clean it up, but pasting the raw sniffed hex string works automatically.

### Step 3: Enjoy!
Restart Home Assistant. You should now see a new Cover entity for your shutter in your dashboard.

## 🛠️ Troubleshooting

If your shutters are not responding:
1. **MQTT Explorer**: Ensure you can see your phone's commands in MQTT Explorer using the credentials provided in Step 1.
2. **Logs**: Check your Home Assistant logs (**Settings -> System -> Logs**). 
3. **Debug Logging**: Add the following to your `configuration.yaml` to see exactly what the integration is sending and receiving:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.neocontrol: debug
   ```
4. **Sequence Numbers**: If you are trying to send the *exact same* hex string twice without the `{seq}` placeholder, the server might reject it as a replay. The integration tries to fix this automatically, but using the `{seq}` placeholder in your config is more robust.

---
*Disclaimer: This integration is not officially affiliated with Somfy or Neocontrol. Use at your own risk.*
