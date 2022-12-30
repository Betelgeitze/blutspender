import pgeocode
from math import radians, cos


class PostcodeRanges:

    def calculate_ranges(self, max_distance, lat1, lon1):
        lat = radians(lat1)

        lat_diff = (max_distance / 111.2)
        lon_diff = (max_distance / (111.2 * cos(lat)))

        min_lat = float(lat1 - lat_diff)
        max_lat = float(lat1 + lat_diff)
        min_lon = float(lon1 - lon_diff)
        max_lon = float(lon1 + lon_diff)

        return min_lat, max_lat, min_lon, max_lon

    def get_lat_and_lon(self, postal_code):
        country = pgeocode.Nominatim("de")
        lat = country.query_postal_code(postal_code)["latitude"]
        lon = country.query_postal_code(postal_code)["longitude"]
        return lat, lon

    def check_distance(self, user_postal_code, termin_postal_code):
        country = pgeocode.GeoDistance("de")
        distance = country.query_postal_code(user_postal_code, termin_postal_code)
        return distance
