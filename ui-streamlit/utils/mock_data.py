"""Mock VehicleManager and Vehicle for testing without hitting the real API.

Activate via ?mock=1 URL parameter in the Streamlit app.

Simulates a Kia Sorento PHEV, Europe region, plugged in but not charging.
"""
from __future__ import annotations

import datetime
import time

from hyundai_kia_connect_api.Vehicle import (
    Vehicle,
    DailyDrivingStats,
    MonthTripInfo,
    DayTripCounts,
    DayTripInfo,
    TripInfo,
)
from hyundai_kia_connect_api.Token import Token
from hyundai_kia_connect_api.const import ORDER_STATUS, ENGINE_TYPES
from hyundai_kia_connect_api.exceptions import DuplicateRequestError


# ── Module-level mock action state ──────────────────────────────────────────

_mock_action_counter: int = 0
_mock_last_call: dict = {}          # key -> (command_name, timestamp)
_mock_action_status: dict = {}      # action_id -> call_count

_DUPLICATE_WINDOW_SECONDS = 5


def _next_action_id() -> str:
    global _mock_action_counter
    _mock_action_counter += 1
    return f"MOCK-ACTION-{_mock_action_counter:04d}"


def _checked_command(command_name: str, vehicle_id: str) -> str:
    """Return new action id or raise DuplicateRequestError within 5s."""
    key = f"{command_name}:{vehicle_id}"
    now = time.monotonic()
    last = _mock_last_call.get(key)
    if last and (now - last) < _DUPLICATE_WINDOW_SECONDS:
        raise DuplicateRequestError(
            f"Duplicate request: {command_name} was called within the last "
            f"{_DUPLICATE_WINDOW_SECONDS} seconds."
        )
    _mock_last_call[key] = now
    return _next_action_id()


def _simple_command(*_args, **_kwargs) -> str:
    """Return a new action ID without duplicate detection."""
    return _next_action_id()


# ── Build the mock vehicle ───────────────────────────────────────────────────

def _build_mock_vehicle() -> Vehicle:
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    vehicle = Vehicle(
        id="MOCK-VEHICLE-001",
        name="My Sorento PHEV",
        model="Sorento 1.6T PHEV",
        year=2023,
        VIN="KNAGU81C8P5000001",
        registration_date="20230320",
        engine_type=ENGINE_TYPES.PHEV,
        enabled=True,
        generation=None,
        ccu_ccs2_protocol_support=1,
        key="mock-key-001",
        data={},
    )

    # Property-setter fields (value, unit) tuples
    vehicle.total_driving_range = (612.0, "km")
    vehicle.odometer = (18472.3, "km")
    vehicle.outside_temperature = (18.5, "°C")
    vehicle.air_temperature = (22.0, "°C")
    vehicle.ev_driving_range = (52.0, "km")
    vehicle.fuel_driving_range = (560.0, "km")
    vehicle.next_service_distance = (7528.0, "km")
    vehicle.last_service_distance = (12000.0, "km")
    vehicle.ev_battery_water_temperature = (24, "°C")
    vehicle.ev_battery_temperature_min = (22, "°C")
    vehicle.ev_battery_temperature_max = (26, "°C")
    vehicle.ev_target_range_charge_AC = (72.0, "km")
    vehicle.ev_target_range_charge_DC = (None, "km")
    vehicle.ev_first_departure_climate_temperature = (21.0, "°C")
    vehicle.ev_second_departure_climate_temperature = (22.0, "°C")
    vehicle.ev_estimated_current_charge_duration = (180, "min")
    vehicle.ev_estimated_fast_charge_duration = (None, "min")
    vehicle.ev_estimated_portable_charge_duration = (None, "min")
    vehicle.ev_estimated_station_charge_duration = (110, "min")

    # Timestamps
    vehicle._last_updated_at = now_utc - datetime.timedelta(minutes=47)
    vehicle._location_last_set_time = now_utc - datetime.timedelta(hours=1)

    # Location
    vehicle._location_latitude = 52.5200
    vehicle._location_longitude = 13.4050
    vehicle._geocode_name = "Mitte, Berlin"
    vehicle._geocode_address = "Unter den Linden 1, 10117 Berlin, Germany"

    # General state
    vehicle.car_battery_percentage = 88
    vehicle.engine_is_running = False
    vehicle.dtc_count = 0
    vehicle.dtc_descriptions = {}
    vehicle.smart_key_battery_warning_is_on = False
    vehicle.washer_fluid_warning_is_on = False
    vehicle.brake_fluid_warning_is_on = False

    # Climate
    vehicle.air_control_is_on = False
    vehicle.defrost_is_on = False
    vehicle.steering_wheel_heater_is_on = False
    vehicle.back_window_heater_is_on = False
    vehicle.side_mirror_heater_is_on = False
    vehicle.front_left_seat_status = 0
    vehicle.front_right_seat_status = 0
    vehicle.rear_left_seat_status = 0
    vehicle.rear_right_seat_status = 0

    # Doors
    vehicle.is_locked = True
    vehicle.front_left_door_is_locked = True
    vehicle.front_right_door_is_locked = True
    vehicle.back_left_door_is_locked = True
    vehicle.back_right_door_is_locked = True
    vehicle.front_left_door_is_open = False
    vehicle.front_right_door_is_open = False
    vehicle.back_left_door_is_open = False
    vehicle.back_right_door_is_open = False
    vehicle.trunk_is_open = False
    vehicle.hood_is_open = False

    # Windows
    vehicle.front_left_window_is_open = False
    vehicle.front_right_window_is_open = False
    vehicle.back_left_window_is_open = False
    vehicle.back_right_window_is_open = False
    vehicle.sunroof_is_open = False
    vehicle.supports_window_control = True

    # Tyres
    vehicle.tire_pressure_all_warning_is_on = False
    vehicle.tire_pressure_front_left_warning_is_on = False
    vehicle.tire_pressure_front_right_warning_is_on = False
    vehicle.tire_pressure_rear_left_warning_is_on = False
    vehicle.tire_pressure_rear_right_warning_is_on = False

    # EV battery
    vehicle.ev_battery_percentage = 72
    vehicle.ev_battery_pack_voltage = 321
    vehicle.ev_battery_chiller_rpm = 0
    vehicle.ev_battery_heating_state = False
    vehicle.ev_battery_winter_mode = False
    vehicle.ev_battery_soh_percentage = 96
    vehicle.ev_battery_remain = 10
    vehicle.ev_battery_capacity = 14
    vehicle.ev_battery_is_charging = False
    vehicle.ev_battery_is_plugged_in = True
    vehicle.ev_charging_power = 0.0
    vehicle.ev_charge_limits_ac = 100
    vehicle.ev_charge_limits_dc = 80
    vehicle.ev_charging_current = 1
    vehicle.ev_charge_port_door_is_open = False
    vehicle.ev_battery_precondition_enabled = False
    vehicle.ev_v2l_status = None
    vehicle.ev_v2x_status = None
    vehicle.ev_v2l_discharge_limit = None

    # Energy totals
    vehicle.total_power_consumed = 847500
    vehicle.total_power_regenerated = 124300
    vehicle.power_consumption_30d = 89200
    vehicle.ev_power_consumption_battery_cooling = 1200
    vehicle.ev_power_consumption_battery_heater = 800
    vehicle.ev_power_consumption_air_conditioning = 4500

    # Fuel
    vehicle.fuel_level = 78.0
    vehicle.fuel_level_is_low = False

    # Scheduled departure
    vehicle.ev_first_departure_enabled = True
    vehicle.ev_second_departure_enabled = False
    vehicle.ev_first_departure_days = [1, 2, 3, 4, 5]
    vehicle.ev_second_departure_days = []
    vehicle.ev_first_departure_time = datetime.time(7, 30)
    vehicle.ev_second_departure_time = datetime.time(9, 0)
    vehicle.ev_first_departure_climate_enabled = True
    vehicle.ev_second_departure_climate_enabled = False
    vehicle.ev_first_departure_climate_defrost = False
    vehicle.ev_second_departure_climate_defrost = False
    vehicle.ev_off_peak_start_time = datetime.time(23, 0)
    vehicle.ev_off_peak_end_time = datetime.time(7, 0)
    vehicle.ev_off_peak_charge_only_enabled = True
    vehicle.ev_schedule_charge_enabled = True

    # Misc status
    vehicle.accessory_on = False
    vehicle.ign3 = False
    vehicle.remote_ignition = False
    vehicle.transmission_condition = "P"
    vehicle.sleep_mode_check = False
    vehicle.headlamp_status = "Off"
    vehicle.headlamp_left_low = False
    vehicle.headlamp_right_low = False
    vehicle.stop_lamp_left = False
    vehicle.stop_lamp_right = False
    vehicle.turn_signal_left_front = False
    vehicle.turn_signal_right_front = False
    vehicle.turn_signal_left_rear = False
    vehicle.turn_signal_right_rear = False

    # Daily driving stats (7 entries covering July 2026)
    vehicle.daily_stats = [
        DailyDrivingStats(
            date=datetime.datetime(2026, 7, 4),
            total_consumed=19200,
            engine_consumption=12500,
            climate_consumption=2800,
            onboard_electronics_consumption=1900,
            battery_care_consumption=500,
            regenerated_energy=3400,
            distance=55.2,
        ),
        DailyDrivingStats(
            date=datetime.datetime(2026, 7, 3),
            total_consumed=22400,
            engine_consumption=15100,
            climate_consumption=3100,
            onboard_electronics_consumption=2000,
            battery_care_consumption=400,
            regenerated_energy=4200,
            distance=64.8,
        ),
        DailyDrivingStats(
            date=datetime.datetime(2026, 7, 2),
            total_consumed=14800,
            engine_consumption=9800,
            climate_consumption=2200,
            onboard_electronics_consumption=1700,
            battery_care_consumption=300,
            regenerated_energy=2600,
            distance=42.1,
        ),
        DailyDrivingStats(
            date=datetime.datetime(2026, 7, 1),
            total_consumed=27600,
            engine_consumption=18500,
            climate_consumption=4100,
            onboard_electronics_consumption=2400,
            battery_care_consumption=600,
            regenerated_energy=5200,
            distance=79.4,
        ),
        DailyDrivingStats(
            date=datetime.datetime(2026, 6, 30),
            total_consumed=11200,
            engine_consumption=7400,
            climate_consumption=1800,
            onboard_electronics_consumption=1500,
            battery_care_consumption=250,
            regenerated_energy=1900,
            distance=31.7,
        ),
        DailyDrivingStats(
            date=datetime.datetime(2026, 6, 27),
            total_consumed=18900,
            engine_consumption=12800,
            climate_consumption=2700,
            onboard_electronics_consumption=1900,
            battery_care_consumption=450,
            regenerated_energy=3100,
            distance=53.9,
        ),
        DailyDrivingStats(
            date=datetime.datetime(2026, 6, 26),
            total_consumed=16300,
            engine_consumption=10900,
            climate_consumption=2400,
            onboard_electronics_consumption=1800,
            battery_care_consumption=350,
            regenerated_energy=2800,
            distance=46.5,
        ),
    ]

    # Month trip info (202607)
    vehicle.month_trip_info = MonthTripInfo(
        yyyymm="202607",
        summary=TripInfo(
            drive_time=287,
            idle_time=42,
            distance=273.2,
            avg_speed=54.8,
            max_speed=130,
        ),
        day_list=[
            DayTripCounts(yyyymmdd="20260701", trip_count=3),
            DayTripCounts(yyyymmdd="20260702", trip_count=2),
            DayTripCounts(yyyymmdd="20260703", trip_count=4),
            DayTripCounts(yyyymmdd="20260704", trip_count=2),
        ],
    )

    # Day trip info (20260704)
    vehicle.day_trip_info = DayTripInfo(
        yyyymmdd="20260704",
        summary=TripInfo(
            drive_time=82,
            idle_time=14,
            distance=55.2,
            avg_speed=38.7,
            max_speed=120,
        ),
        trip_list=[
            TripInfo(
                hhmmss="080510",
                drive_time=47,
                idle_time=9,
                distance=33.4,
                avg_speed=41.2,
                max_speed=120,
            ),
            TripInfo(
                hhmmss="174255",
                drive_time=35,
                idle_time=5,
                distance=21.8,
                avg_speed=35.8,
                max_speed=90,
            ),
        ],
    )

    return vehicle


# ── Mock Token ───────────────────────────────────────────────────────────────

class _MockToken:
    """Token-like object that satisfies the UI's attribute access."""
    username = "demo@example.com"
    password = ""
    pin = ""
    valid_until = None
    access_token = "mock-token"
    refresh_token = "mock-refresh"
    device_id = None
    stamp = None


# ── MockVehicleManager ───────────────────────────────────────────────────────

class MockVehicleManager:
    """Drop-in replacement for VehicleManager used in mock mode (?mock=1)."""

    def __init__(self) -> None:
        vehicle = _build_mock_vehicle()
        self.vehicles: dict[str, Vehicle] = {vehicle.id: vehicle}
        self.token = _MockToken()
        self.region = 1       # REGION_EUROPE
        self.brand = 1        # BRAND_KIA
        self.geocode_api_enable = False
        self.geocode_provider = 1
        self.geocode_api_key = None

    # ── Auth / lifecycle ─────────────────────────────────────────────────────

    def login(self) -> bool:
        return True

    def check_and_refresh_token(self) -> bool:
        return False  # token still valid

    def initialize_vehicles(self) -> None:
        pass  # vehicles already initialised in __init__

    # ── State update ─────────────────────────────────────────────────────────

    def update_vehicle_with_cached_state(self, vehicle_id: str) -> None:
        vehicle = self.vehicles.get(vehicle_id)
        if vehicle is not None:
            vehicle._last_updated_at = (
                datetime.datetime.now(datetime.timezone.utc)
                - datetime.timedelta(minutes=10)
            )

    def force_refresh_vehicle_state(self, vehicle_id: str) -> None:
        vehicle = self.vehicles.get(vehicle_id)
        if vehicle is not None:
            vehicle._last_updated_at = (
                datetime.datetime.now(datetime.timezone.utc)
                - datetime.timedelta(seconds=30)
            )

    def update_all_vehicles_with_cached_state(self) -> None:
        for vid in self.vehicles:
            self.update_vehicle_with_cached_state(vid)

    # ── Trip info ─────────────────────────────────────────────────────────────

    def update_month_trip_info(self, vehicle_id: str, yyyymm: str) -> None:
        vehicle = self.vehicles.get(vehicle_id)
        if vehicle is None:
            return
        if yyyymm == "202607":
            vehicle.month_trip_info = MonthTripInfo(
                yyyymm="202607",
                summary=TripInfo(
                    drive_time=287,
                    idle_time=42,
                    distance=273.2,
                    avg_speed=54.8,
                    max_speed=130,
                ),
                day_list=[
                    DayTripCounts(yyyymmdd="20260701", trip_count=3),
                    DayTripCounts(yyyymmdd="20260702", trip_count=2),
                    DayTripCounts(yyyymmdd="20260703", trip_count=4),
                    DayTripCounts(yyyymmdd="20260704", trip_count=2),
                ],
            )
        else:
            vehicle.month_trip_info = None

    def update_day_trip_info(self, vehicle_id: str, yyyymmdd: str) -> None:
        vehicle = self.vehicles.get(vehicle_id)
        if vehicle is None:
            return
        if yyyymmdd == "20260704":
            vehicle.day_trip_info = DayTripInfo(
                yyyymmdd="20260704",
                summary=TripInfo(
                    drive_time=82,
                    idle_time=14,
                    distance=55.2,
                    avg_speed=38.7,
                    max_speed=120,
                ),
                trip_list=[
                    TripInfo(
                        hhmmss="080510",
                        drive_time=47,
                        idle_time=9,
                        distance=33.4,
                        avg_speed=41.2,
                        max_speed=120,
                    ),
                    TripInfo(
                        hhmmss="174255",
                        drive_time=35,
                        idle_time=5,
                        distance=21.8,
                        avg_speed=35.8,
                        max_speed=90,
                    ),
                ],
            )
        else:
            vehicle.day_trip_info = None

    # ── OTP (no-op in mock) ───────────────────────────────────────────────────

    def send_otp(self, notify_type) -> None:
        return None

    def verify_otp_and_complete_login(self, otp_code: str) -> None:
        return None

    # ── Vehicle enable/disable ────────────────────────────────────────────────

    def enable_vehicle(self, vehicle_id: str) -> None:
        vehicle = self.vehicles.get(vehicle_id)
        if vehicle is not None:
            vehicle.enabled = True

    def disable_vehicle(self, vehicle_id: str) -> None:
        vehicle = self.vehicles.get(vehicle_id)
        if vehicle is not None:
            vehicle.enabled = False

    # ── Commands with duplicate detection ─────────────────────────────────────

    def lock(self, vehicle_id: str) -> str:
        return _checked_command("lock", vehicle_id)

    def unlock(self, vehicle_id: str) -> str:
        return _checked_command("unlock", vehicle_id)

    def start_climate(self, vehicle_id: str, *args, **kwargs) -> str:
        return _checked_command("start_climate", vehicle_id)

    def stop_climate(self, vehicle_id: str) -> str:
        return _checked_command("stop_climate", vehicle_id)

    def start_charge(self, vehicle_id: str) -> str:
        return _checked_command("start_charge", vehicle_id)

    def stop_charge(self, vehicle_id: str) -> str:
        return _checked_command("stop_charge", vehicle_id)

    def start_hazard_lights(self, vehicle_id: str) -> str:
        return _checked_command("start_hazard_lights", vehicle_id)

    def start_hazard_lights_and_horn(self, vehicle_id: str) -> str:
        return _checked_command("start_hazard_lights_and_horn", vehicle_id)

    # ── Commands without duplicate detection ──────────────────────────────────

    def set_charge_limits(self, vehicle_id: str, *args, **kwargs) -> str:
        return _simple_command()

    def set_charging_current(self, vehicle_id: str, *args, **kwargs) -> str:
        return _simple_command()

    def set_windows_state(self, vehicle_id: str, *args, **kwargs) -> str:
        return _simple_command()

    def open_charge_port(self, vehicle_id: str) -> str:
        return _simple_command()

    def close_charge_port(self, vehicle_id: str) -> str:
        return _simple_command()

    def schedule_charging_and_climate(self, vehicle_id: str, *args, **kwargs) -> str:
        return _simple_command()

    def start_valet_mode(self, vehicle_id: str) -> str:
        return _simple_command()

    def stop_valet_mode(self, vehicle_id: str) -> str:
        return _simple_command()

    def set_vehicle_to_load_discharge_limit(self, vehicle_id: str, *args, **kwargs) -> str:
        return _simple_command()

    def set_navigation(self, vehicle_id: str, *args, **kwargs) -> str:
        return _simple_command()

    # ── Action status ─────────────────────────────────────────────────────────

    def check_action_status(
        self, vehicle_id: str, action_id: str, synchronous: bool = False, timeout: int = 120
    ):
        if synchronous:
            time.sleep(1)
            return ORDER_STATUS.SUCCESS

        count = _mock_action_status.get(action_id, 0) + 1
        _mock_action_status[action_id] = count
        if count == 1:
            return ORDER_STATUS.PENDING
        return ORDER_STATUS.SUCCESS


# ── Factory function ─────────────────────────────────────────────────────────

def create_mock_vm() -> MockVehicleManager:
    """Create and return a new MockVehicleManager instance."""
    return MockVehicleManager()
