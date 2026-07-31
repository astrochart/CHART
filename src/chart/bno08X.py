import time
from math import atan2, asin, sqrt, pi, radians

import requests

from board import SCL, SDA
from busio import I2C

from adafruit_bno08x import BNO_REPORT_ROTATION_VECTOR
from adafruit_bno08x.i2c import BNO08X_I2C


# ============================================================
# BNO085 INITIALIZATION
# ============================================================

i2c = I2C(SCL, SDA, frequency=800000)

bno = BNO08X_I2C(i2c)
bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)

time.sleep(1)


# ============================================================
# FUNCTIONS
# ============================================================

def normalize_quaternion(w, x, y, z):
    norm = sqrt(w*w + x*x + y*y + z*z)

    if norm < 1e-6:
        return None
    return (
        w / norm,
        x / norm,
        y / norm,
        z / norm
    )


def find_heading(w, x, y, z):
    yaw = atan2(
        2.0 * (w*z + x*y),
        1.0 - 2.0 * (y*y + z*z)
    ) * 180.0 / pi

    yaw -= 90.0
    yaw %= 360.0

    return yaw


def find_altitude(w, x, y, z):
    value = 2.0 * (w*y - z*x)
    value = max(-1.0, min(1.0, value))

    return asin(value) * 180.0 / pi


def move_stellarium(az_deg, alt_deg):

    az = radians(az_deg)
    alt = radians(alt_deg)

    try:
        response = requests.post(
            "http://localhost:8090/api/main/view",
            params={
                "az": az,
                "alt": alt
            },
            timeout=2
        )

        if response.status_code != 200:
            print("Stellarium error:", response.status_code, response.text)

    except requests.exceptions.RequestException as e:
        print("Stellarium connection error:", e)


def get_az_alt():
    quat = bno.quaternion

    qi, qj, qk, qr = quat

    quat = normalize_quaternion(qr, qi, qj, qk)

    w, x, y, z = quat

    az = find_heading(w, x, y, z)
    alt = find_altitude(w, x, y, z)

    return az, alt


def AzAlt():
    return get_az_alt()


def runStellarium(stop_event):


    # Wait for Stellarium's Remote Control API
    while True:
        try:
            response = requests.get(
                "http://localhost:8090/api/main/status",
                timeout=1
            )

            if response.status_code == 200:
                print("Connected to Stellarium.")
                break

        except requests.exceptions.RequestException:
            pass

        print("Waiting for Stellarium...")
        time.sleep(0.5)

    while not stop_event.is_set():
        try:
            az, alt = get_az_alt()
            move_stellarium(az, alt)

        except Exception as e:
            print("IMU thread error:", repr(e))

        time.sleep(0.01)

    print("Stellarium thread exiting")
