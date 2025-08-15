import argparse 
import random 
import math 
import datetime 
import time 
import geopandas as gpd 
import rasterio 
import serial 

def dms_to_decimal(degrees, minutes, seconds):
    decimal_degrees = degrees + minutes / 60 + seconds / 3600 #преобразование координат в десятичные градусы
    return decimal_degrees 

def decimal_to_dms(decimal_degrees):
    #преобразование десятичные градусы в формат градусов, минут, секунд
    degrees = int(decimal_degrees)
    minute = (decimal_degrees - degrees) * 60
    seconds = round((minute - int(minute)) * 60, 6)
    minutes = minute + seconds
    return degrees, minutes, seconds 

def generate_random_point(lat1, lon1, distance_km, brng):
    R = 6371  #радиус Земли
    φ1 = math.radians(lat1)
    λ1 = math.radians(lon1)
    d = distance_km / R  #угловое расстояние
    #новые координаты
    φ2 = math.asin(math.sin(φ1) * math.cos(d) + math.cos(φ1) * math.sin(d) * math.cos(brng))
    λ2 = λ1 + math.atan2(math.sin(brng) * math.sin(d) * math.cos(φ1), math.cos(d) - math.sin(φ1) * math.sin(φ2))
    #преобразование обратно в десятичные градусы
    φ2 = math.degrees(φ2)
    λ2 = math.degrees(λ2)
    return φ2, λ2

def get_depth_from_raster(φ2, λ2, raster_path):
    with rasterio.open(raster_path) as src:
        point = gpd.GeoDataFrame(geometry=gpd.points_from_xy([λ2], [φ2]), crs="epsg:4326")
        point = point.to_crs(src.crs)
        point = point.geometry.iloc[0]
        x = point.x
        y = point.y
        for sample in src.sample([(x, y)]):
            depth = sample[0]
            break
        return depth
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Генерация случайных точек в круге.')
    parser.add_argument('latitude_degrees', type=int, help='Градусы широты')
    parser.add_argument('latitude_minutes', type=int, help='Минуты широты')
    parser.add_argument('latitude_seconds', type=float, help='Секунды широты')
    parser.add_argument('longitude_degrees', type=int, help='Градусы долготы')
    parser.add_argument('longitude_minutes', type=int, help='Минуты долготы')
    parser.add_argument('longitude_seconds', type=float, help='Секунды долготы')
    args = parser.parse_args()
    raster_path = r"C:\Users\79114\Downloads\_ags_Baltic_Sea_Bathymetry_Database_v091\Baltic_Sea_Bathymetry_Database_v091.tif"
    lat1 = dms_to_decimal(args.latitude_degrees, args.latitude_minutes, args.latitude_seconds)
    lon1 = dms_to_decimal(args.longitude_degrees, args.longitude_minutes, args.longitude_seconds)
    radius_km = 1
    #подключение к serial порту
    device = 'COM4'
    serial = serial.Serial(port=device, baudrate=19200, bytesize=8, parity="N", stopbits=1, rtscts=True, dsrdtr=True, xonxoff=0, timeout=10)
    while True:
        azimuth_deg = random.uniform(0, 360)
        distance_km = random.uniform(0, radius_km)
        brng = math.radians(azimuth_deg)
        #генерация новой точки
        φ2, λ2 = generate_random_point(lat1, lon1, distance_km, brng)
        #преобразование в формат градусов, минут, секунд
        lat2_deg, lat2_min, lat2_sec = decimal_to_dms(φ2)
        lon2_deg, lon2_min, lon2_sec = decimal_to_dms(λ2)
        lat_hemisphere = "N" if lat2_deg >= 0 else "S"
        lon_hemisphere = "E" if lon2_deg >= 0 else "W"
        now = datetime.datetime.now()
        time_str = now.strftime("%H%M%S")
        lat_str = f"{lat2_deg:02d}{lat2_min:04.4f}"
        lon_str = f"{lon2_deg:02d}{lon2_min:04.4f}"
        line = f"$GPGGA,{time_str},{lat_str},{lat_hemisphere},{lon_str},{lon_hemisphere},1,04,61.10,6,M,32.3,M,,*50\n"
        serial.write(line.encode("ascii"))
        print(line)
        depth = get_depth_from_raster(lat2_deg, lon2_deg, raster_path)
        depth_feet = depth * 3.28
        depth_fathoms = depth * 0.468691
        if depth:
            line1 = f"$SDBT,{depth_feet:.2f},f,{depth:.2f},M,{depth_fathoms:.2f},F,*64\n"
            serial.write(line1.encode("ascii"))
            print(line1)
        else:
            line2 = "Глубина не найдена\n"
            serial.write(line2.encode("ascii"))
            print(line2)
        time.sleep(1)
