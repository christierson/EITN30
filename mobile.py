import json
import time
import random
from udp_interface import UDPInterface
import requests


def load_config():
    with open("device_config.json", "r") as f:
        return json.load(f)


def get_dummy_sensor_data():
    return {
        "temperature": round(random.uniform(20, 30), 2),
        "humidity": round(random.uniform(30, 70), 2),
    }


def get_dummy_weather_data():
    return {
        "wind_speed": round(random.uniform(1, 10), 2),
        "precipitation": round(random.uniform(0, 5), 2),
    }


def get_weather(latitude=52.52, longitude=13.405):  # Default: Berlin
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        f"&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
    )

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        weather = {
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "wind_speed": current.get("wind_speed_10m"),
        }

        return weather

    except Exception as e:
        print("Failed to get weather:", e)
        return None


def main():
    comm = UDPInterface()

    print("Mobile unit started. Sending data every 10 seconds...")

    while True:
        # sensor_data = get_dummy_sensor_data()
        # weather_data = get_dummy_weather_data()
        # payload = {**sensor_data, **weather_data}
        payload = get_weather()
        comm.send(payload)
        print(f"Sent data: {payload}")
        time.sleep(10)


if __name__ == "__main__":
    main()
