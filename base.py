import json
from udp_interface import UDPInterface


def is_weather_good(data: dict) -> bool:
    # Define your rules here
    temp_ok = 18 <= data.get("temperature", 0) <= 30
    humidity_ok = 30 <= data.get("humidity", 100)
    wind_ok = data.get("wind_speed", 100) < 8
    rain_ok = data.get("precipitation", 100) < 2
    return temp_ok and humidity_ok and wind_ok and rain_ok


def on_data(data: dict, addr, comm: UDPInterface):
    try:
        # message = json.loads(data.decode())
        print(f"Received from {addr}: {data}")

        if is_weather_good(data):
            response = "Weather is good"
        else:
            response = "Weather is bad"

        comm.send({"message": response})
        print(f"Replied to {addr} with: {response}")
    except Exception as e:
        print(f"Error handling message from {addr}: {e}")


def main():
    comm = UDPInterface()

    comm.start_listening(lambda data, addr: on_data(data, addr, comm))

    print("Base station listening for weather data...")
    try:
        while True:
            pass  # Just keeping the main thread alive
    except KeyboardInterrupt:
        comm.stop()
        print("\nStopped base station.")


if __name__ == "__main__":
    main()
