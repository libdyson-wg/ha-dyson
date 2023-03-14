# HomeAssistant Custom Integration for Dyson

This custom integration is still under development.

This is a HA custom integration for dyson. There are several main differences between this custom integration and the official dyson integration:

- It does not rely on dyson account. Which means once configured, the integration will no longer login to the Dyson cloud service so fast and more reliable start up process.

- Config flow and discovery is supported, so easier configuration.

- Based on a new library that is better structured so the code in the integration itself is simplified.

My goal is to make this integration official. However, at the current stage, I don't want to do the changes in core since there could be a lot of breaking changes. Therefore, I'll do be merge when everything seems stable.

## Important note regarding connection via Dyson Link

If you use your Dyson Link account to connect to the integration, you may or may not encounter a `libdyson.exceptions.DysonInvalidAuth` error. In this case, try disconnecting from the mobile app first, it should clear the error. Sometimes, you just need to try multiple times. If you discover a workaround for this issue please open a pull request.

## Installation

The minimum supported Home Assistant version is 2021.12.0.

You can install using HACS. Adding https://github.com/libdyson-wg/ha-dyson as custom repository and then install Dyson Local. If you want cloud functionalities as well, add https://github.com/libdyson-wg/ha-dyson-cloud and install Dyson Cloud.

You can also install manually

## Local and Cloud

There are two integrations, Dyson Local and Dyson Cloud. Due to the limitation of HACS, they are split into two repositories. This repository hosts Dyson Local, and https://github.com/libdyson-wg/ha-dyson-cloud hosts Dyson Cloud.

### Dyson Local

Dyson Local uses MQTT-based protocol to communicate with local Dyson devices using credentials. Currently it supports

- Dyson 360 Eye robot vacuum
- Dyson 360 Heurist robot vacuum
- Dyson Pure Cool
- Dyson Pure Cool Desk
- Dyson Pure Cool Link
- Dyson Pure Cool Link Desk
- Dyson Pure Hot+Cool
- Dyson Pure Hot+Cool Link
- Dyson Pure Humidity+Cool

### Dyson Cloud

Dyson Cloud uses HTTP-based API to communicate with cloud service. Currently it supports getting device credentials and show all devices as discovered entities under the Integrations page. It also supports getting cleaning maps as `camera` entities for 360 Eye robot vacuum.

## Setup

### Setup using device WiFi information

Version 0.6.1 introduced a new way to set up. This is inspired by https://community.home-assistant.io/t/dyson-pure-cool-link-local-mqtt-control/217263. Set up through UI and select "Setup using WiFi information". Find your device WiFi SSID and password on the sticker on your device body or user's manual (See the figure below). Don't fill in your home WiFi information. Note that this method only uses SSID and password to calculate serial, credential, and device type so you still need to setup your device on the official mobile app first.

### Setup using Dyson cloud account

You can also set up Dyson Cloud first so that you don't need to manually get device credentials. To do so, go to **Configuration** -> **Integrations** and click the **+** button. Then find Dyson Cloud. After successful setup, all devices under the account will be shown as discovered entities and you can then set up Dyson Local with single click. Leave host blank to using zeroconf discovery. After that, you can even remove Dyson Cloud entity if you don't need cleaning maps. All local devices that are already set up will remain untouched.

### Setup manually

If you want to manually set up Dyson Local, you need to get credentials first. Clone or download https://github.com/libdyson-wg/libdyson-neon, then use `python3 get_devices.py` to do that. You may need to install some dependencies using `pip3 install -r requirements.txt`.

## Debug Log

To enable debug log, add the following lines to your `configuration.yaml` and restart your HomeAssistant.

```yaml
logger:
  default: info
  logs:
    libdyson: debug
    custom_components.dyson_local: debug
    custom_components.dyson_cloud: debug
```

## FAQ

### I got "not a valid add-on repository" when I try to add this repo

This is a **custom integration** not a **custom add-on**. You need to install [HACS](https://hacs.xyz/) and add this repo there.
