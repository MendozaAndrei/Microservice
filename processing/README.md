# Processing Service - Forest Fire Data Aggregation

## Overview

The **Processing Service** is responsible for calculating and maintaining statistics about temperature and air quality readings stored in the MySQL database. It runs periodically to aggregate data and provide summary statistics.

## Purpose

This service:
- **Aggregates data** from the MySQL database (via Storage service)
- **Calculates statistics** like total counts and maximum values
- **Provides an API** to retrieve current statistics
- **Updates continuously** by processing new data every 5 seconds

## Architecture - How Data Flows

```
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
```

### Important: Processing Does NOT Directly Access MySQL!

**The Processing service makes HTTP requests to the Storage service**, which then queries MySQL and returns the data. This follows a microservices architecture where each service has a specific responsibility:

1. **Receiver Service (8080)**: Receives data from external sources
2. **Storage Service (8090)**: Manages MySQL database operations
3. **Processing Service (8100)**: Calculates statistics from stored data

## How to Run

### Prerequisites
- Python 3.x installed
- MySQL Docker container running (via `docker-compose up`)
- Storage service running on port 8090
- Dependencies installed: `pip install -r requirements.txt` (if exists)

### Start the Service

```bash
cd processing
python app.py
```

The service will:
1. Start on **port 8100**
2. Begin processing data every **5 seconds** (configurable)
3. Log activity to `app.log`
4. Save statistics to `data.json`

## How to Access

### 1. View Statistics (Browser)
Open in your browser:
```
http://localhost:8100/stats
```

### 2. Swagger UI (Interactive API Documentation)
```
http://localhost:8100/ui
```

### 3. Using curl (Command Line)
```bash
curl http://localhost:8100/stats
```

### 4. Using PowerShell
```powershell
Invoke-RestMethod -Uri "http://localhost:8100/stats" -Method Get
```

## API Endpoints

### GET /stats
Returns current statistics about temperature and air quality data.

**Response Example:**
```json
{
    "num_temp_readings": 150,
    "max_temperature_celsius": 45.3,
    "num_airquality_readings": 123,
    "max_air_quality": 250,
    "last_updated": "2025-10-09T16:05:00Z"
}
```

**Fields Explained:**
- `num_temp_readings`: Total count of temperature readings processed from MySQL
- `max_temperature_celsius`: Highest temperature value ever recorded
- `num_airquality_readings`: Total count of air quality readings processed from MySQL
- `max_air_quality`: Highest air quality value ever recorded
- `last_updated`: Timestamp when statistics were last updated

## Where Data Comes From

### Data Retrieval Process

```
Processing Service
    ↓
HTTP GET http://localhost:8090/temperature?start_timestamp=X&end_timestamp=Y
    ↓
Storage Service
    ↓
SQL Query: SELECT * FROM temperature WHERE date_created >= X AND date_created < Y
    ↓
MySQL Database (Docker)
    ↓
Returns temperature records
    ↓
Storage Service formats as JSON
    ↓
Returns to Processing Service
    ↓
Processing calculates statistics
    ↓
Saves to data.json
```

### Key Points:
1. **Processing queries Storage service via HTTP** (not MySQL directly)
2. Storage service queries MySQL database and returns JSON
3. Processing calculates statistics and saves to `data.json`
4. The `data.json` file contains **only summary statistics**, not raw data

## Configuration

### app_conf.yml
```yaml
datastore:
  filename: data.json          # Where to save statistics
scheduler:
  interval: 5                  # How often to process (seconds)
eventstores:
  temperature:
    url: http://localhost:8090/temperature   # Storage service endpoint
  airquality:
    url: http://localhost:8090/airquality    # Storage service endpoint
```

## How Periodic Processing Works

```
Time: 00:00 - Service starts
    ↓
00:00 - First run: Queries ALL data (from 2000-01-01 to now)
    ↓
00:05 - Second run: Queries NEW data (from 00:00 to 00:05)
    ↓
00:10 - Third run: Queries NEW data (from 00:05 to 00:10)
    ↓
... continues every 5 seconds ...
```

**Why this matters:**
- On **first run**, if data.json doesn't exist, it queries from year 2000 to get ALL historical data
- On **subsequent runs**, it only queries for NEW data since the last update
- Statistics are **cumulative** - they keep growing as more data is processed

## Files in This Directory

- **app.py**: Main application code with processing logic
- **app_conf.yml**: Configuration file (URLs, intervals, filenames)
- **log_conf.yml**: Logging configuration
- **openapi.yaml**: API specification (for Swagger UI)
- **data.json**: Statistics file (created automatically on first run)
- **app.log**: Application log file

## Troubleshooting

### Statistics Showing Zeros

**Problem:** `num_temp_readings` and `num_airquality_readings` are 0

**Possible Causes:**

1. **No data in MySQL database**
   - Solution: POST data through Receiver service at http://localhost:8080/ui

2. **Timestamp issue** - `last_updated` is set to a date AFTER your data
   - Solution: Delete `data.json` and restart the service. It will recreate with timestamp "2000-01-01T00:00:00Z"
   ```bash
   rm data.json
   python app.py
   ```

3. **Storage service not running**
   - Solution: Start Storage service first
   ```bash
   cd ../storage
   python app.py
   ```

4. **MySQL Docker not running**
   - Solution: Start Docker container
   ```bash
   docker-compose up -d
   ```

### Connection Errors

**Problem:** Error connecting to Storage service

**Check:**
1. Is Storage service running on port 8090?
2. Check logs: `tail -f app.log`
3. Test Storage service directly: `curl http://localhost:8090/temperature?start_timestamp=2000-01-01T00:00:00Z&end_timestamp=2025-12-31T23:59:59Z`

## Testing the Complete Flow

### 1. Start All Services
```bash
# Terminal 1 - MySQL
docker-compose up

# Terminal 2 - Storage
cd storage
python app.py

# Terminal 3 - Processing
cd processing
python app.py

# Terminal 4 - Receiver (optional, for posting new data)
cd receiver
python app.py
```

### 2. Check Initial Statistics
```bash
curl http://localhost:8100/stats
```

Should show counts of existing MySQL data (or zeros if database is empty)

### 3. Add New Data (Optional)
Go to http://localhost:8080/ui and POST temperature/air quality data

### 4. Wait 5 Seconds

The Processing service will automatically process the new data

### 5. Check Updated Statistics
```bash
curl http://localhost:8100/stats
```

Counts should have increased!

## Logs

### Viewing Logs
```bash
# Real-time logs
tail -f app.log

# View all logs
cat app.log
```

### What to Look For
```
INFO - Started Periodic Processing
INFO - Querying data from 2000-01-01T00:00:00Z to 2025-10-09T16:00:00Z
INFO - Received 150 NEW temperature readings from MySQL (via Storage service)
INFO - Received 123 NEW air quality readings from MySQL (via Storage service)
INFO - Periodic processing has ended
```

If you see `Received 0 NEW temperature readings`, it means:
- Either there's no data in MySQL
- Or the timestamp window doesn't include your data

## Summary

**Key Takeaways:**
1. Processing service **does NOT directly access MySQL**
2. It queries **Storage service via HTTP REST API**
3. Storage service queries MySQL and returns JSON
4. Processing calculates **summary statistics** and saves to data.json
5. Runs **automatically every 5 seconds** to process new data
6. Statistics are **cumulative** across all historical data
