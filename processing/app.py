import connexion
from apscheduler.schedulers.background import BackgroundScheduler
import yaml
import logging.config
import requests
import json
from datetime import datetime
import os

# Contains: datastore filename, scheduler interval, and eventstore URLs
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

# Loads the logging configuration from log_conf.yml
with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    
logging.config.dictConfig(log_config)
logger = logging.getLogger('basicLogger')



def get_stats():
    """
    HTTP GET endpoint to retrieve current statistics
    
    URL: GET http://localhost:8100/stats
    
    Example Response:
    {
        "num_temp_readings": 150,
        "max_temperature_celsius": 145.8,
        "num_airquality_readings": 120,
        "max_air_quality": 250.5,
        "last_updated": "2025-10-09T08:45:30Z"
    }
    """
    logger.info("Started Request for Statistics")
    
    # Check if the statistics file exists (data.json)
    if not os.path.exists(app_config['datastore']['filename']):
        logger.error("Statistics do not exist")
        return {"message": "Statistics do not exist"}, 404
    
    # Read the statistics from the JSON     file
    with open(app_config['datastore']['filename'], 'r') as f:
        stats = json.load(f)
    
    logger.debug(f"Statistics: {stats}")
    logger.info("Request for statistics has completed")
    
    return stats, 200



# ============================================================================
# PERIODIC PROCESSING FUNCTION (Runs every 5 seconds)
# ============================================================================
def populate_stats():
    logger.info("Started Periodic Processing")
    
    if os.path.exists(app_config['datastore']['filename']):
        # Read existing statistics from data.json
        with open(app_config['datastore']['filename'], 'r') as f:
            stats = json.load(f)
    else:
        # First time running - initialize with default values
        stats = {
            "num_temp_readings": 0,
            "max_temperature_celsius": 0,
            "num_airquality_readings": 0,
            "max_air_quality": 0,
            "last_updated": "2000-01-01T00:00:00Z"
        }
    
    current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    last_updated = stats["last_updated"]
    
    logger.info(f"Querying events from {last_updated} to {current_datetime}")
    
    temp_response = requests.get(
        app_config['eventstores']['temperature']['url'],
        params={'start_timestamp': last_updated, 'end_timestamp': current_datetime}
    )
    
    if temp_response.status_code == 200:
        temp_readings = temp_response.json()
        logger.info(f"Received {len(temp_readings)} NEW temperature readings")
        
        stats["num_temp_readings"] += len(temp_readings)
        
        if len(temp_readings) > 0:
            max_temp = max([reading['temperature_celsius'] for reading in temp_readings])
            # Only update if this new max is higher than our current max
            if max_temp > stats["max_temperature_celsius"]:
                stats["max_temperature_celsius"] = max_temp
                logger.info(f"New max temperature: {max_temp}°C")
    else:
        logger.error(f"Failed to get temperature readings. Status code: {temp_response.status_code}")
    # Example URL: http://localhost:8090/airquality?start_timestamp=2025-10-09T08:00:00Z&end_timestamp=2025-10-09T08:05:00Z
    airquality_response = requests.get(
        app_config['eventstores']['airquality']['url'],
        params={'start_timestamp': last_updated, 'end_timestamp': current_datetime}
    )
    
    if airquality_response.status_code == 200:
        airquality_readings = airquality_response.json()
        logger.info(f"Received {len(airquality_readings)} NEW air quality readings")
        
        stats["num_airquality_readings"] += len(airquality_readings)
        
        if len(airquality_readings) > 0:
            max_aq = max([reading['air_quality'] for reading in airquality_readings])
            if max_aq > stats["max_air_quality"]:
                stats["max_air_quality"] = max_aq
                logger.info(f"New max air quality: {max_aq}")
    else:
        logger.error(f"Failed to get air quality readings. Status code: {airquality_response.status_code}")
    
    stats["last_updated"] = current_datetime
    
    # Write updated statistics back to data.json file
    with open(app_config['datastore']['filename'], 'w') as f:
        json.dump(stats, f, indent=4)
    
    logger.debug(f"Updated statistics: {stats}")
    logger.info("Periodic processing has ended")



def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(
        populate_stats,                                  # Function to run
        'interval',                                      # Run at regular intervals
        seconds=app_config['scheduler']['interval']      # Every 5 seconds (from config)
    )
    sched.start()
    logger.info(f"Scheduler started - will run every {app_config['scheduler']['interval']} seconds")
app = connexion.App(__name__, specification_dir=".")
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_scheduler()
    
    logger.info("Starting Processing Service on port 8100")
    app.run(port=8100)
