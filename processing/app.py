"""
PROCESSING SERVICE - Forest Fire Data Aggregation and Statistics
=================================================================

PURPOSE:
This service calculates and maintains statistics about temperature and air quality readings
stored in the MySQL database. It does NOT directly access the database - instead, it queries
the Storage service via HTTP REST API.

DATA FLOW ARCHITECTURE:
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Receiver   │  POST   │   Storage   │  Query  │ Processing  │
│  (8080)     │ ------> │   (8090)    │ <------ │  (8100)     │
└─────────────┘         └─────────────┘         └─────────────┘
                              │                        │
                              ▼                        ▼
                        ┌──────────┐            ┌──────────┐
                        │  MySQL   │            │data.json │
                        │ (Docker) │            │  (local) │
                        └──────────┘            └──────────┘
                     RAW EVENT DATA          STATISTICS ONLY

HOW TO ACCESS THIS SERVICE:
- GET http://localhost:8100/stats - View current statistics
- Swagger UI: http://localhost:8100/ui

WHERE DATA COMES FROM:
1. This service does NOT directly access MySQL database
2. It makes HTTP GET requests to Storage service endpoints:
   - GET http://localhost:8090/temperature?start_timestamp=X&end_timestamp=Y
   - GET http://localhost:8090/airquality?start_timestamp=X&end_timestamp=Y
3. Storage service queries MySQL and returns the data
4. This service calculates statistics and saves to data.json

WHAT STATISTICS ARE TRACKED:
- num_temp_readings: Total count of temperature readings processed
- max_temperature_celsius: Highest temperature ever recorded
- num_airquality_readings: Total count of air quality readings processed  
- max_air_quality: Highest air quality value ever recorded
- last_updated: Timestamp of last processing run

HOW TO RUN:
cd processing
python app.py

The service runs on port 8100 and processes data every 5 seconds (configurable in app_conf.yml)
"""

import connexion
from apscheduler.schedulers.background import BackgroundScheduler
import yaml
import logging.config
import requests
import json
from datetime import datetime
import os

# ============== CONFIGURATION SETUP ==============
# Loads the configuration files that define:
# - Where to store statistics (data.json)
# - How often to run processing (every 5 seconds)
# - URLs of Storage service endpoints for querying data
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    
logging.config.dictConfig(log_config)
logger = logging.getLogger('basicLogger')


def get_stats():
    """
    GET /stats ENDPOINT - Returns current statistics
    
    This endpoint reads the statistics from the local data.json file and returns them.
    The statistics are updated periodically by the populate_stats() function.
    
    Example response:
    {
        "num_temp_readings": 150,
        "max_temperature_celsius": 45.3,
        "num_airquality_readings": 123,
        "max_air_quality": 250,
        "last_updated": "2025-10-09T16:05:00Z"
    }
    """
    logger.info("Started Request for Statistics")
    
    # Check if the statistics file exists
    if not os.path.exists(app_config['datastore']['filename']):
        logger.error("Statistics do not exist")
        return {"message": "Statistics do not exist"}, 404
    
    # Read the statistics from the file
    with open(app_config['datastore']['filename'], 'r') as f:
        stats = json.load(f)
    
    logger.debug(f"Statistics: {stats}")
    logger.info("Request for statistics has completed")
    
    return stats, 200


def populate_stats():
    """
    CORE PROCESSING FUNCTION - Calculates statistics from MySQL data
    
    This function runs periodically (every 5 seconds by default) and:
    1. Loads existing statistics from data.json (or creates default if first run)
    2. Queries NEW data from Storage service (which queries MySQL)
    3. Updates statistics with the new data
    4. Saves updated statistics back to data.json
    
    IMPORTANT: This function does NOT directly access MySQL database!
    Instead, it makes HTTP GET requests to the Storage service at port 8090.
    The Storage service is the one that actually queries the MySQL database.
    
    DATA RETRIEVAL FLOW:
    Processing Service (this code)
        ↓ HTTP GET Request
    Storage Service (port 8090)
        ↓ SQL Query
    MySQL Database (Docker container)
    """
    logger.info("Started Periodic Processing")
    
    # ============== STEP 1: Load or Initialize Statistics ==============
    # Check if we have previous statistics saved in data.json
    if os.path.exists(app_config['datastore']['filename']):
        with open(app_config['datastore']['filename'], 'r') as f:
            stats = json.load(f)
    else:
        # First time running - create default statistics
        # Set last_updated to year 2000 to ensure we get ALL historical data from MySQL
        stats = {
            "num_temp_readings": 0,
            "max_temperature_celsius": 0,
            "num_airquality_readings": 0,
            "max_air_quality": 0,
            "last_updated": "2000-01-01T00:00:00Z"  # Start from year 2000 to catch all data
        }
    
    # ============== STEP 2: Prepare Time Window for Queries ==============
    # Get current time and the last time we processed data
    # We only query for NEW data between last_updated and now
    current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    last_updated = stats["last_updated"]
    
    logger.info(f"Querying data from {last_updated} to {current_datetime}")
    
    # ============== STEP 3: Query Temperature Readings from Storage Service ==============
    # Makes a GET request to: http://localhost:8090/temperature
    # Parameters: start_timestamp and end_timestamp
    # The Storage service will query MySQL for temperature records where:
    #   date_created >= start_timestamp AND date_created < end_timestamp
    # Example URL: http://localhost:8090/temperature?start_timestamp=2000-01-01T00:00:00Z&end_timestamp=2025-10-09T16:00:00Z
    temp_response = requests.get(
        app_config['eventstores']['temperature']['url'],
        params={'start_timestamp': last_updated, 'end_timestamp': current_datetime}
    )
    
    if temp_response.status_code == 200:
        temp_readings = temp_response.json()
        logger.info(f"Received {len(temp_readings)} NEW temperature readings from MySQL (via Storage service)")
        
        # Update cumulative count (total readings processed so far)
        stats["num_temp_readings"] += len(temp_readings)
        
        # Calculate max temperature (highest value ever seen across ALL data)
        if len(temp_readings) > 0:
            max_temp = max([reading['temperature_celsius'] for reading in temp_readings])
            if max_temp > stats["max_temperature_celsius"]:
                stats["max_temperature_celsius"] = max_temp
    else:
        logger.error(f"Failed to get temperature readings. Status code: {temp_response.status_code}")
    
    # ============== STEP 4: Query Air Quality Readings from Storage Service ==============
    # Makes a GET request to: http://localhost:8090/airquality
    # Parameters: start_timestamp and end_timestamp
    # The Storage service will query MySQL for air quality records where:
    #   date_created >= start_timestamp AND date_created < end_timestamp
    # Example URL: http://localhost:8090/airquality?start_timestamp=2000-01-01T00:00:00Z&end_timestamp=2025-10-09T16:00:00Z
    airquality_response = requests.get(
        app_config['eventstores']['airquality']['url'],
        params={'start_timestamp': last_updated, 'end_timestamp': current_datetime}
    )
    
    if airquality_response.status_code == 200:
        airquality_readings = airquality_response.json()
        logger.info(f"Received {len(airquality_readings)} NEW air quality readings from MySQL (via Storage service)")
        
        # Update cumulative count (total readings processed so far)
        stats["num_airquality_readings"] += len(airquality_readings)
        
        # Calculate max air quality (highest value ever seen across ALL data)
        if len(airquality_readings) > 0:
            max_aq = max([reading['air_quality'] for reading in airquality_readings])
            if max_aq > stats["max_air_quality"]:
                stats["max_air_quality"] = max_aq
    else:
        logger.error(f"Failed to get air quality readings. Status code: {airquality_response.status_code}")
    
    # ============== STEP 5: Save Updated Statistics ==============
    # Update last_updated to current time so next run only processes new data
    stats["last_updated"] = current_datetime
    
    # Write updated statistics to JSON file (data.json)
    # This is NOT the MySQL database - it's a local file storing just the summary statistics
    with open(app_config['datastore']['filename'], 'w') as f:
        json.dump(stats, f, indent=4)
    
    logger.debug(f"Updated statistics: {stats}")
    logger.info("Periodic processing has ended")


def init_scheduler():
    """
    Initialize the background scheduler
    
    Uses APScheduler to run populate_stats() periodically in the background.
    The interval is configured in app_conf.yml (default: every 5 seconds).
    
    This allows the service to continuously process new data from MySQL
    without needing manual triggers.
    """
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, 'interval', seconds=app_config['scheduler']['interval'])
    sched.start()


# ============== APPLICATION STARTUP ==============
# Create Connexion app with OpenAPI specification
# This provides:
# - GET /stats endpoint (see get_stats function above)
# - Swagger UI at http://localhost:8100/ui for testing
app = connexion.App(__name__, specification_dir=".")
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    # Start the background scheduler that processes data every 5 seconds
    init_scheduler()
    # Run the Flask/Connexion app on port 8100
    app.run(port=8100)
