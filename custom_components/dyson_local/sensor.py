"""Sensor platform for dyson."""

from typing import Callable, Union

from libdyson import (
    Dyson360Eye,
    Dyson360Heurist,
    DysonDevice,
    DysonPureCoolLink,
    DysonPurifierHumidifyCool,
)

from libdyson.const import MessageType
from libdyson.dyson_device import DysonFanDevice

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONF_NAME,
    PERCENTAGE,
    TEMP_CELSIUS,
    TIME_HOURS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import DysonEntity
from .const import DATA_COORDINATORS, DATA_DEVICES, DOMAIN
from .utils import environmental_property


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable
) -> None:
    """Set up Dyson sensor from a config entry."""
    device = hass.data[DOMAIN][DATA_DEVICES][config_entry.entry_id]
    name = config_entry.data[CONF_NAME]
    if isinstance(device, Dyson360Eye) or isinstance(device, Dyson360Heurist):
        entities = [DysonBatterySensor(device, name)]
    else:
        coordinator = hass.data[DOMAIN][DATA_COORDINATORS][config_entry.entry_id]
        entities = [
            DysonHumiditySensor(coordinator, device, name),
            DysonTemperatureSensor(coordinator, device, name),
            DysonVOCSensor(coordinator, device, name),
        ]

        if isinstance(device, DysonPureCoolLink):
            entities.extend(
                [
                    DysonFilterLifeSensor(device, name),
                    DysonParticulatesSensor(coordinator, device, name),
                ]
            )
        else:  # DysonPureCool or DysonPurifierHumidifyCool
            entities.extend(
                [
                    DysonPM25Sensor(coordinator, device, name),
                    DysonPM10Sensor(coordinator, device, name),
                    DysonNO2Sensor(coordinator, device, name),
                ]
            )
            if device.carbon_filter_life is None:
                entities.append(DysonCombinedFilterLifeSensor(device, name))
            else:
                entities.extend(
                    [
                        DysonCarbonFilterLifeSensor(device, name),
                        DysonHEPAFilterLifeSensor(device, name),
                    ]
                )
        if isinstance(device, DysonPurifierHumidifyCool):
            entities.append(DysonNextDeepCleanSensor(device, name))
        if hasattr(device, "formaldehyde") and device.formaldehyde is not None:
            entities.append(DysonHCHOSensor(coordinator, device, name))
    async_add_entities(entities)


class DysonSensor(SensorEntity, DysonEntity):
    """Base class for a Dyson sensor."""

    _MESSAGE_TYPE = MessageType.STATE
    _SENSOR_TYPE = None
    _SENSOR_NAME = None

    def __init__(self, device: DysonDevice, name: str):
        """Initialize the sensor."""
        super().__init__(device, name)

    @property
    def sub_name(self):
        """Return the name of the Dyson sensor."""
        return self._SENSOR_NAME

    @property
    def sub_unique_id(self):
        """Return the sensor's unique id."""
        return self._SENSOR_TYPE


class DysonSensorEnvironmental(CoordinatorEntity, DysonSensor):
    """Dyson environmental sensor."""

    _MESSAGE_TYPE = MessageType.ENVIRONMENTAL

    def __init__(
        self, coordinator: DataUpdateCoordinator, device: DysonDevice, name: str
    ):
        """Initialize the environmental sensor."""
        CoordinatorEntity.__init__(self, coordinator)
        DysonSensor.__init__(self, device, name)


class DysonBatterySensor(DysonSensor):
    """Dyson battery sensor."""

    _SENSOR_TYPE = "battery_level"
    _SENSOR_NAME = "Battery Level"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.battery_level


class DysonFilterLifeSensor(DysonSensor):
    """Dyson filter life sensor (in hours) for Pure Cool Link."""

    _SENSOR_TYPE = "filter_life"
    _SENSOR_NAME = "Filter Life"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = TIME_HOURS

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.filter_life


class DysonCarbonFilterLifeSensor(DysonSensor):
    """Dyson carbon filter life sensor (in percentage) for Pure Cool."""

    _SENSOR_TYPE = "carbon_filter_life"
    _SENSOR_NAME = "Carbon Filter Life"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.carbon_filter_life


class DysonHEPAFilterLifeSensor(DysonSensor):
    """Dyson HEPA filter life sensor (in percentage) for Pure Cool."""

    _SENSOR_TYPE = "hepa_filter_life"
    _SENSOR_NAME = "HEPA Filter Life"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.hepa_filter_life


class DysonCombinedFilterLifeSensor(DysonSensor):
    """Dyson combined filter life sensor (in percentage) for Pure Cool."""

    _SENSOR_TYPE = "combined_filter_life"
    _SENSOR_NAME = "Filter Life"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.hepa_filter_life


class DysonNextDeepCleanSensor(DysonSensor):
    """Sensor of time until next deep clean (in hours) for Dyson Pure Humidify+Cool."""

    _SENSOR_TYPE = "next_deep_clean"
    _SENSOR_NAME = "Next Deep Clean"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = TIME_HOURS

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.time_until_next_clean


class DysonHumiditySensor(DysonSensorEnvironmental):
    """Dyson humidity sensor."""

    _SENSOR_TYPE = "humidity"
    _SENSOR_NAME = "Humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @environmental_property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.humidity


class DysonTemperatureSensor(DysonSensorEnvironmental):
    """Dyson temperature sensor."""

    _SENSOR_TYPE = "temperature"
    _SENSOR_NAME = "Temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = TEMP_CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    @environmental_property
    def temperature_kelvin(self) -> int:
        """Return the temperature in kelvin."""
        return self._device.temperature

    @property
    def native_value(self) -> Union[str, float]:
        """Return the "native" value for this sensor.

        Note that as of 2021-10-28, Home Assistant does not support converting
        from Kelvin native unit to Celsius/Fahrenheit. So we return the Celsius
        value as it's the easiest to calculate.
        """
        temperature_kelvin = self.temperature_kelvin
        if isinstance(temperature_kelvin, str):
            return temperature_kelvin

        return temperature_kelvin - 273.15


class DysonPM25Sensor(DysonSensorEnvironmental):
    """Dyson sensor for PM 2.5 fine particulate matters."""

    _SENSOR_TYPE = "pm25"
    _SENSOR_NAME = "PM 2.5"
    _attr_device_class = SensorDeviceClass.PM25
    _attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    _attr_state_class = SensorStateClass.MEASUREMENT

    @environmental_property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.particulate_matter_2_5


class DysonPM10Sensor(DysonSensorEnvironmental):
    """Dyson sensor for PM 10 particulate matters."""

    _SENSOR_TYPE = "pm10"
    _SENSOR_NAME = "PM 10"
    _attr_device_class = SensorDeviceClass.PM10
    _attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    _attr_state_class = SensorStateClass.MEASUREMENT

    @environmental_property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.particulate_matter_10


class DysonParticulatesSensor(DysonSensorEnvironmental):
    """Dyson sensor for particulate matters for "Link" devices."""
    _SENSOR_TYPE = "aqi"
    _SENSOR_NAME = "Air Quality Index"
    _attr_device_class = SensorDeviceClass.AQI
    _attr_state_class = SensorStateClass.MEASUREMENT

    @environmental_property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.particulates


class DysonVOCSensor(DysonSensorEnvironmental):
    """Dyson sensor for volatile organic compounds."""

    _SENSOR_TYPE = "voc-index"
    _SENSOR_NAME = "Volatile Organic Compounds Index"
    _attr_device_class = SensorDeviceClass.AQI
    _attr_state_class = SensorStateClass.MEASUREMENT

    @environmental_property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        return self._device.volatile_organic_compounds


class DysonNO2Sensor(DysonSensorEnvironmental):
    """Dyson sensor for Nitrogen Dioxide."""

    _SENSOR_TYPE = "no2-index"
    _SENSOR_NAME = "Nitrogen Dioxide Index"
    _attr_device_class = SensorDeviceClass.AQI
    _attr_state_class = SensorStateClass.MEASUREMENT

    @environmental_property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.nitrogen_dioxide


class DysonHCHOSensor(DysonSensorEnvironmental):
    """Dyson sensor for Formaldehyde."""

    _SENSOR_TYPE = "hcho"
    _SENSOR_NAME = "Formaldehyde"

    _attr_device_class = SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS
    _attr_state_class = SensorStateClass.MEASUREMENT

    @environmental_property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        return self._device.nitrogen_dioxide
