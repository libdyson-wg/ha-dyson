# Home Assistant Integration for Wi-Fi Connected Dyson Devices

This is a Home Assistant custom integration for Wi-Fi connected Dyson devices, and is being actively developed. It replaces the Dyson Local and Dyson Cloud integrations by shenxn, which are no longer maintained.

[![GitHub (Pre-)Release Date](https://img.shields.io/github/release-date-pre/libdyson-wg/ha-dyson)](https://github.com/libdyson-wg/ha-dyson/releases/)
[![Latest Release](https://badgen.net/github/release/libdyson-wg/ha-dyson)](https://github.com/libdyson-wg/ha-dyson/releases/)
[![validate](https://badgen.net/github/checks/libdyson-wg/ha-dyson/main/validate)](https://github.com/libdyson-wg/ha-dyson/actions/workflows/hassfest.yaml)
[![HACS Action](https://badgen.net/github/checks/libdyson-wg/ha-dyson/main/HACS%20Action)](https://github.com/libdyson-wg/ha-dyson/actions/workflows/hacs.yaml)
[![Latest Commit](https://badgen.net/github/last-commit/libdyson-wg/ha-dyson/main)](https://github.com/libdyson-wg/ha-dyson/commit/HEAD)

## Troubleshooting

### Fan connection failures

Please try power-cycling the fan device and try connecting again. 

Dyson fans run an MQTT Broker which this integration connects to as a client. The broker has a connection limit and some devices appear to have a firmware bug where they hold onto dead connections and fill up the connection pool, causing new connections to fail. This behavior has been observed on the following device models, but may also include others:

- TP07 Purifier Cool
- TP09 Purifier Cool Formaldehyde
- HP07 Purifier Hot+Cool
- HP09 Purifier Hot+Cool Formaldehyde

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=libdyson-wg&repository=ha-dyson&category=integration)

You can also install manually by copying the `custom_components` from this repository into your Home Assistant installation.

### Dyson Devices Supported

This integration uses MQTT-based protocol to communicate with Dyson devices. Only WiFi enabled models have this capability. Currently the following models are supported, and support for more models can be added on request.

- Dyson 360 Eye robot vacuum
- Dyson 360 Heurist robot vacuum
- Dyson Pure Cool
- Dyson Purifier Cool
- Dyson Purifier Cool Formaldehyde
- Dyson Pure Cool Desk
- Dyson Pure Cool Link
- Dyson Pure Cool Link Desk
- Dyson Pure Hot+Cool
- Dyson Pure Hot+Cool Link
- Dyson Purifier Hot+Cool
- Dyson Purifier Hot+Cool Formaldehyde
- Dyson Pure Humidity+Cool
- Dyson Purifier Humidity+Cool
- Dyson Purifier Humidity+Cool Formaldehyde
- Dyson Purifier Big+Quiet
- Dyson Purifier Big+Quiet Formaldehyde

### MyDyson Accounts

MyDyson mobile apps use an HTTP-based API, which is also used by the MyDyson part of this integration. Currently it supports automated setup of your devices by discovering and fetching credentials from the API. It also supports getting cleaning maps as `camera` entities for 360 Eye robot vacuum.

## Setup

Once you have installed the integration, navigate to `Settings > Devices` tab, press `Add integration` on the bottom right and search for `Dyson`.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=ha-dyson)


### Setup using device WiFi information

Note: Some new models released after 2020 do not ship with a Wi-Fi information sticker. They are still supported by this integration, but can only be configured via your MyDyson account. After setting up your devices, your account can be deleted from Home Assistant if you prefer to stay offline.

Find your device WiFi SSID and password on the sticker on your device body or user's manual. Don't fill in your home WiFi information. Note that this method only uses SSID and password to calculate serial, credential, and device type so you still need to setup your device on the official mobile app first.

### Setup using your MyDyson account

You can also set up a MyDyson account first so that you don't need to manually get device credentials. After successfully connecting your account, all devices under the account will be shown as discovered entities and you can easily set them up. After that, you can even remove MyDyson account entity if you don't need cleaning maps for the 360 Eye vacuum. All local devices that are already set up will remain untouched.

Note: When setting up your MyDyson account, please make sure you check your email/spam for the verification code from Dyson.

### Setup manually

If you want to manually set up a Dyson device, you need to get credentials first. Clone or download https://github.com/libdyson-wg/libdyson-neon, then use `python3 get_devices.py` to do that. You may need to install some dependencies using `pip3 install -r requirements.txt`.

## FAQ

### I got "not a valid add-on repository" when I try to add this repo

This is a **custom integration** not a **custom add-on**. You need to install [HACS](https://hacs.xyz/) and add this repo there.


### How do I migrate from [shenxn/ha-dyson](https://github.com/shenxn/ha-dyson)?

If you used Dyson Local from shenxn, you can migrate fairly easily:

#### Experimental no-reconfiguration migration

 This is less proven, but it is possible to switch over with zero impact to your current integration configuration, entities/devices, or dashboards. I don't know what side-effects it may have though (leftover old config data might start causing issues or something - no guarantees).

1. Remove the ha-dyson and ha-dyson-cloud custom repositories from HACS
    - _Without_ removing the integrations themselves
3. Install the new [ha-dyson](https://github.com/libdyson-wg/ha-dyson)
    - If you installed this as a Custom Repository, update the ha-dyson repository using the HACS updater

#### Proven some-reconfiguration migration

This is proven to work without any side effects. If you used the default IDs for the entities and devices, then you'll just need to re-configure the devices but your dashboards will not need updating.

1. Remove the Dyson Local and Dyson Cloud _integrations_ from your /config/integrations page.
1. Remove the Dyson Local and Dyson Cloud _integrations_ from your /hacs/integrations page.
2. Remove the dyson-ha and dyson-ha-cloud custom repositories from HACS
3. Add the new [dyson-ha](https://github.com/libdyson-wg/ha-dyson)
    - If you installed this as a Custom Repository, update the ha-dyson repository using the HACS updater
