import connexion
from connexion import NoContent
import httpx
# using different port
STORAGE_URL = "http://localhost:8090"

def report_temperature_readings(body):
    readings = body.get("readings", [])

    try:
        for r in readings:
            data = {
                "fire_id": body["fire_id"],
                "latitude": body["latitude"],
                "longitude": body["longitude"],
                "temperature_celsius": r["temperature_celsius"],
                "humidity_level": r.get("humidity_level"),
                "batch_timestamp": body["reporting_timestamp"],
                "reading_timestamp": r["recorded_timestamp"],
            }
            


            # The HTTPX post that sends it over to storage app.py API
            resp = httpx.post(f"{STORAGE_URL}/temperature", json=data)
            
    except Exception as e:
        return NoContent, 500

    return NoContent, 201


def report_airquality_reading(body):
    readings = body.get("readings", [])

    try:
        for r in readings:
            data = {
                "fire_id": body["fire_id"],
                "location_name": body["location_name"],
                "particulate_level": body["particulate_level"],
                "air_quality": r["air_quality"],
                "smoke_opacity": r["smoke_opacity"],
                "batch_timestamp": body["reporting_timestamp"],
                "reading_timestamp": r["recorded_timestamp"],
            }

            # The HTTPX post that sends it over to storage app.py API 
            resp = httpx.post(f"{STORAGE_URL}/airquality", json=data)
            resp.raise_for_status()
            
    except Exception as e:
        return NoContent, 500

    return NoContent, 201


app = connexion.App(__name__, specification_dir=".")
app.add_api("lab1.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)
