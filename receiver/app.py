import datetime
import json
import connexion
from connexion import NoContent
import httpx
import time
import yaml
import logging.config
from pykafka import KafkaClient
import datetime

# Loads External CConfiguration File. This is used specifically for KAFKA agent. 
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

# Loads External Configuration File. This is used specifically for LOGGING agent. 
with open("log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())


logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger('basicLogger')
#This essentially sets up the logging from log_conf.yml
#Creates a logging instance to write logs basically. REALLY important for logs.
#Don't forget this. 

# Since we are not using the STORAGE_URL from app_conf.yml, I commented it out. We will be sing kafka
# STORAGE_URL = app_config['eventstore']['url']

# name used to be eventstore, but now it is events. 
KAFKA_HOSTNAME = app_config['events']['hostname']
KAFKA_PORT = app_config['events']['port']
KAFKA_TOPIC = app_config['events']['topic']



def report_temperature_readings(body):
    readings = body.get("readings", [])
    """
    Contains the entire batch from YAML Schema
    the READINGS is an array of individual temperature measurements. 
This, essentially, what it receives: 
{
  "fire_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
  "reporting_timestamp": "2025-08-29T09:12:33.001Z",
  "latitude": 49.391065,
  "longitude": -123.047647,
  "readings": [
    {
      "temperature_celsius": 129.4,
      "humidity_level": 60.4,
      "recorded_timestamp": "2025-08-29T09:12:33.001Z"
    },
    {
      "temperature_celsius": 80.1,
      "humidity_level": 50.1,
      "recorded_timestamp": "2025-08-29T09:56:33.001Z"
    }
  ]
}
    """
    try:
        # We'd have to connect it all over again here, to connect it over to the thingy
        #This creates the connection to the KAFKA server that we have set up. 
        # It gets the TOPIC that it requires, the queue name. 
        # Creates a producer to send messages  
        client = KafkaClient(hosts=f'{KAFKA_HOSTNAME}:{KAFKA_PORT}')
        topic = client.topics[str.encode(KAFKA_TOPIC)]
        producer = topic.get_sync_producer()

        #This loops through the readings in the "readings" array
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
            # We don't need this anymore. getting rid of this 
            # resp = httpx.post(f"{STORAGE_URL}/temperature", json=data)
            # New code to send the data to Kafka
            
            msg = {
                "type": "temperature_reading",
                "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "payload": data #The actual fucking data that will be sent out
            }
            msg_str = json.dumps(msg) #Converts it to a JSON String
            producer.produce(msg_str.encode('utf-8')) #Sends it to KAFKA
            # This will log when the event is received and will have a response status for debugging
            logger.info(f"Response for event temperature_reading (id: {trace_id}) has status {resp.status_code}")
            resp.raise_for_status()

            
    except Exception as e:
        return NoContent, 500
    return NoContent, 201


def report_airquality_reading(body):
    readings = body.get("readings", [])

    try:

        client = KafkaClient(hosts=f'{KAFKA_HOSTNAME}:{KAFKA_PORT}')
        topic = client.topics[str.encode(KAFKA_TOPIC)]
        producer = topic.get_sync_producer()
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
            # resp = httpx.post(f"{STORAGE_URL}/airquality", json=data)
            msg = {
                "type": "airquality_reading",
                "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "payload": data
            }
            msg_str = json.dumps(msg)
            producer.produce(msg_str.encode('utf-8'))
            # Log the response of the storage service
            logger.info(f"Response for event airquality_reading (id: {trace_id}) has status {resp.status_code}")
            
            resp.raise_for_status()
            
    except Exception as e:
        return NoContent, 500

    return NoContent, 201

#This one is what connects the app.py to the openapi.yaml
#This exports any important information needed. 
app = connexion.App(__name__, specification_dir=".")
app.add_api("lab1.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)
