import connexion
from connexion import NoContent
import httpx
import time
import yaml
import logging.config

# Load configuration
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

# Load logging configuration
with open("log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

STORAGE_URL = app_config['eventstore']['url']

def report_temperature_readings(body):
    readings = body.get("readings", [])

    try:
        for r in readings:
            #This autogenerates the traceid using the time in nanosecons so I don't have to add another 
            #value in the jmeter
            trace_id = time.time_ns()
            
            # Log when event is received
            logger.info(f"Received event temperature_reading with a trace id of {trace_id}")
            
            data = {
                "trace_id": trace_id,
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
            
            # Log the response of the storage service
            logger.info(f"Response for event temperature_reading (id: {trace_id}) has status {resp.status_code}")
            
            resp.raise_for_status()
            
    except Exception as e:
        return NoContent, 500

    return NoContent, 201


def report_airquality_reading(body):
    readings = body.get("readings", [])

    try:
        for r in readings:
            # Just added this and into the "data" sheet
            trace_id = time.time_ns()
            
            # Logs the event into the app.log
            logger.info(f"Received event airquality_reading with a trace id of {trace_id}")
            
            data = {
                "trace_id": trace_id,
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
            
            # Log the response of the storage service
            logger.info(f"Response for event airquality_reading (id: {trace_id}) has status {resp.status_code}")
            
            resp.raise_for_status()
            
    except Exception as e:
        return NoContent, 500

    return NoContent, 201


app = connexion.App(__name__, specification_dir=".")
app.add_api("lab1.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)
