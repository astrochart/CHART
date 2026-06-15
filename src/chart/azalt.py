from datetime import datetime, timedelta
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import astropy.units as u
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError

# Converting Latitude and Longitude into a timezone so we can use UTC instead of local time
# Thus allowing us to use the program without having to account for time zones manually
def timezone_of(latitude, longitude):
    tzname = TimezoneFinder().timezone_at(lat=latitude, lng=longitude)
    if tzname is None:
        raise ValueError(f"No Timezone found for {latitude},{longitude}")
    return ZoneInfo(tzname)


def pointing(latitude, longitude, year, month, day, hour, minute, delay, num_points, lat_increment, long_increment, delta_time, gal_long_start, gal_lat_start):
    year, month, day = int(year), int(month), int(day)
    hour, minute, delay = int(hour), int(minute), int(delay)
    num_points, long_increment, lat_increment = abs(int(num_points)), int(long_increment), int(lat_increment)
    latitude, longitude = float(latitude), float(longitude)
    delta_time = abs(int(delta_time))
    gal_long_start, gal_lat_start = int(gal_long_start), int(gal_lat_start)


    long_span = abs(long_increment) * num_points
    lat_span = abs(lat_increment) * num_points
    
    if long_span > 360:
        raise ValueError(f"Longitude spans {long_span}° which is greater than 360°. \nPlease change the number of points or the Longitude spacing\n")
    if lat_span >180:  
        raise ValueError(f"Latitude spans {lat_span}° which is greater than 180°. \nPlease change the number of points or the Latitude spacing\n")
    
    
    h = 1
    if 0 < abs(long_increment) < h:
        raise ValueError(f"Galactic Longitude Spacing is too small, please stay above {h}\n")
    if 0 < abs(lat_increment) < h:
        raise ValueError(f"Galactic Latitude Spacing is too small, please stay above {h}\n")
    
    tz = timezone_of(latitude, longitude)
    location = EarthLocation(lat = latitude * u.deg , lon = longitude * u.deg)
    sgr_a_gal = SkyCoord(ra = 266.41684 * u.deg, dec = -29.00781 * u.deg, frame='icrs').galactic

    b0 = sgr_a_gal.b.deg
    b_start = b0 + gal_lat_start 
    b_final = b_start+ lat_increment * (num_points - 1)
    if not -90 <= b_final <= 90:
        # largest i >= 0 keeping b0 + lat_increment*i within +/-90 deg
        if lat_increment > 0:
            max_points = int((90 - b_start) // lat_increment) + 1
        elif lat_increment < 0:
            max_points = int((-90 - b_start) // lat_increment) + 1
        else:
            max_points = num_points
        raise ValueError(
            f"Galactic latitude reaches {b_final:.1f}° at point {num_points}, "
            f"outside the valid ±90° range. With a latitude increment of "
            f"{lat_increment}°, request at most {max_points} point(s).\n"
        )

    
    start = datetime(year, month, day, hour, minute, tzinfo = tz)
    results = []
                     
    for i in range(num_points):
        obs_time = start + timedelta(minutes = delay + delta_time * i)
        
        l = sgr_a_gal.l + long_increment * i * u.deg + gal_long_start * u.deg
        b = sgr_a_gal.b + lat_increment * i * u.deg + gal_lat_start * u.deg
        offset = SkyCoord(l = l, b = b, frame = 'galactic')
        altaz = offset.transform_to(AltAz(obstime=Time(obs_time), location=location))

        results.append({
            "Observation #": i+1,
            "l": l, "b": b,
            "Galactic longitudinal offset": long_increment * i + gal_long_start,
            "Galactic latitudinal offset": lat_increment * i + gal_lat_start,
            "Altitude": altaz.alt.deg,
            "Azimuth": altaz.az.deg,
            "Local time": obs_time,
            "Galactic Longitudinal Increment": long_increment,
            "Galactic Latitudinal Increment": lat_increment,
        })
    return results


def azalt(results):
    lines = []
    lines.append("Here is a plan for your observation today. \nIt is okay if you need to change the plan for your specific conditions. \nThese are recommendations not requirements.\nMost importantly: Have FUN!")
    for i in results:
        lines.append(f"Observation # {i['Observation #']}:")
        lines.append(f"Local time {i['Local time'].strftime('%I:%M %p')}")
        if 0 < abs(i['Galactic Longitudinal Increment']) < 5:
            lines.append("WARNING Galactic Longitudinal Increment is below 5 which is very small")
        if 0 < abs(i['Galactic Latitudinal Increment']) < 5:
            lines.append("WARNING Galactic Latitudinal Increment is below 5 which is very small")
        lines.append(f"    Galactic longitudinal offset {i['Galactic longitudinal offset']}°")
        lines.append(f"    Galactic latitudinal offset {i['Galactic latitudinal offset']}°")
        if i['Altitude'] < 0:
            lines.append(f"WARNING ALTITUDE IS BELOW HORIZON (not observable)\n    Altitude {i['Altitude']:.1f}°")
        else:
            lines.append(f"    Altitude {i['Altitude']:.1f}°")
        lines.append(f"    Azimuth {i['Azimuth']:.1f}°")
        lines.append("")
    return "\n".join(lines)

def gps(location):
    geolocator = Nominatim(user_agent="CHART-telescope") 
    try:
        lat_long = geolocator.geocode(location)
    except GeocoderServiceError:
        raise ValueError("Need Internet connection for this feature :/\nPlease enter Latitude and Longitude Manually")
    if lat_long is None:
        raise ValueError(f"Could not find location: {location!r}. Try again.\n")
    latitude = lat_long.latitude
    longitude = lat_long.longitude
    return latitude, longitude


def gimme_time(latitude, longitude, gal_lat, gal_long, point_height, year, month, day):
    result = []
    
    tz = timezone_of(latitude, longitude)
    location = EarthLocation(lat = latitude * u.deg , lon = longitude * u.deg)
    sgr_a_gal = SkyCoord(ra = 266.41684 * u.deg, dec = -29.00781 * u.deg, frame='icrs').galactic


    l = sgr_a_gal.l + gal_long * u.deg
    b = sgr_a_gal.b + gal_lat * u.deg

    offset = SkyCoord(l = l, b = b, frame = 'galactic')
    

    start = datetime(year, month, day, hour = 0, minute = 0, tzinfo = tz)
    end = datetime(year, month, day, hour = 23, minute = 59, tzinfo = tz)
    time_interval = timedelta(minutes = 5)

    time_array = []
    current_time = start
    while current_time <= end:
        time_array.append(current_time)
        current_time += time_interval

    Time_Array = Time(time_array)
    altaz = offset.transform_to(AltAz(obstime=Time_Array, location=location))

    pos_in_sky = altaz.alt.deg.argmax()
    time_max_alt = time_array[pos_in_sky]
    result.append(f"Your point will reach its max altitude at {time_max_alt.strftime('%I:%M %p %Z')}")
    
    alt = altaz.alt.deg
    rise_time = None
    for i in range(1, len(time_array)):
        if alt[i-1]<0 and alt[i]>=0:
            rise_time = time_array[i]
            result.append(f"Your point will cross the horizon at {rise_time.strftime('%I:%M %p %Z')}")
            break
    if alt.max() < 0:
        result.append(f"Altitude of your set point today ({start.strftime('%I:%M %p %Z')}) never goes above the horizon.\nTry another day:/")
    elif alt.min() > 0:
        result.append(f"Altitude of your set point today({start.strftime('%I:%M %p %Z')}) never goes below the horizon")

    #this allows us to get the time of a height above the horizon of the point in degrees
    point_height_time = None
    for i in range(1, len(time_array)):
        if alt[i-1]< point_height and alt[i] >= point_height:
            point_height_time = time_array[i]
            result.append(f"Your point will reach {point_height}° altitude at {point_height_time.strftime('%I:%M %p %Z')}")
            break
    if point_height_time is None:
        result.append(f"Your point never reaches {point_height}° today")

    return "\n".join(result)






















    