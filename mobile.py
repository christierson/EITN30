import json
import time
import random
from udp_interface import UDPInterface  # assuming this is your communication module


def load_config():
    with open("device_config.json", "r") as f:
        return json.load(f)


def get_dummy_sensor_data():
    # Replace with real DHT22 readings later
    return {
        "temperature": round(random.uniform(20, 30), 2),
        "humidity": round(random.uniform(30, 70), 2),
    }


def get_dummy_weather_data():
    # Replace with real web API call later
    return {
        "wind_speed": round(random.uniform(1, 10), 2),
        "precipitation": round(random.uniform(0, 5), 2),
    }


def main():
    comm = UDPInterface()

    print("Mobile unit started. Sending data every 10 seconds...")

    while True:
        sensor_data = get_dummy_sensor_data()
        weather_data = get_dummy_weather_data()
        payload = {**sensor_data, **weather_data}
        comm.send(payload)
        print(f"Sent data: {payload}")
        time.sleep(10)


if __name__ == "__main__":
    main()
