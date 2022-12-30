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

    def get_lat_and_lon(self, postcode):
        country = pgeocode.Nominatim("de")
        lat = country.query_postal_code(postcode)["latitude"]
        lon = country.query_postal_code(postcode)["longitude"]
        return lat, lon

    def check_distance(self, user_postcode, termin_postcode):
        country = pgeocode.GeoDistance("de")
        distance = country.query_postal_code(user_postcode, termin_postcode)
        return distance
