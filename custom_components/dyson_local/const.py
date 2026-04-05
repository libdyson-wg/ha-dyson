"""Constants for Dyson Local."""

DOMAIN = "dyson_local"

CONF_SERIAL = "serial"
CONF_CREDENTIAL = "credential"
CONF_DEVICE_TYPE = "device_type"

DATA_DEVICES = "devices"
DATA_DISCOVERY = "discovery"
DATA_COORDINATORS = "coordinators"

# Device types not yet supported by libdyson-neon.
# These are handled locally until upstream adds support.
DEVICE_TYPE_HUSHJET = "897"
