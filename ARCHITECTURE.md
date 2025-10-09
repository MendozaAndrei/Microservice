# Microservice Architecture - Data Flow Explanation

## Overview

This document explains **where the Processing service gets its data** and **how data flows through the system**.

## The Answer: Processing Does NOT Query MySQL Directly!

**Your confusion is understandable!** When you read the Processing service code, you don't see any MySQL database queries because **the Processing service doesn't access MySQL directly**.

Instead, it follows a **microservices architecture** where each service has a specific responsibility:

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Receiver   │  POST   │   Storage   │  Query  │ Processing  │
│  (8080)     │ ------> │   (8090)    │ <------ │  (8100)     │
└─────────────┘         └─────────────┘         └─────────────┘
      │                       │                        │
      │                       ▼                        ▼
      │                 ┌──────────┐            ┌──────────┐
      │                 │  MySQL   │            │data.json │
      │                 │ (Docker) │            │  (local) │
      │                 └──────────┘            └──────────┘
      │                 RAW EVENT DATA          STATISTICS ONLY
      │
      └─────────────────> Accepts data from external sources
```

## Three Services, Three Responsibilities

### 1. Receiver Service (Port 8080)
**What it does:** Accepts temperature and air quality data from external sources

**File:** `receiver/app.py`

**Code snippet:**
```python
# Receiver forwards data to Storage via HTTP
resp = httpx.post(f"{STORAGE_URL}/temperature", json=data)
```

**How to access:** http://localhost:8080/ui (Swagger UI)

---

### 2. Storage Service (Port 8090) ⭐ **This is where MySQL queries happen!**
**What it does:** Directly manages the MySQL database - stores and retrieves data

**File:** `storage/app.py`

**Code snippet (THIS is where MySQL is queried):**
```python
def get_temperature_readings(start_timestamp, end_timestamp):
    # THIS IS THE ACTUAL MYSQL QUERY!
    statement = select(Temperature).where(
        Temperature.date_created >= start_datetime
    ).where(
        Temperature.date_created < end_datetime
    )
    
    # Execute query against MySQL
    results = session.execute(statement).scalars().all()
```

**Endpoints:**
- POST /temperature - Store temperature data in MySQL
- POST /airquality - Store air quality data in MySQL
- **GET /temperature?start_timestamp=X&end_timestamp=Y** - Query temperature data from MySQL
- **GET /airquality?start_timestamp=X&end_timestamp=Y** - Query air quality data from MySQL

**How to access:** http://localhost:8090/ui (Swagger UI)

---

### 3. Processing Service (Port 8100)
**What it does:** Calculates statistics by querying the Storage service (not MySQL directly!)

**File:** `processing/app.py`

**Code snippet:**
```python
# Processing makes HTTP GET request to Storage service
temp_response = requests.get(
    'http://localhost:8090/temperature',
    params={'start_timestamp': last_updated, 'end_timestamp': current_datetime}
)

# Storage service queries MySQL and returns JSON
temp_readings = temp_response.json()

# Processing calculates statistics
stats["num_temp_readings"] += len(temp_readings)
```

**Endpoints:**
- GET /stats - View current statistics

**How to access:** http://localhost:8100/stats or http://localhost:8100/ui

---

## Step-by-Step Data Flow

### Scenario: Processing Service Needs Data

Here's exactly what happens when the Processing service runs (every 5 seconds):

**Step 1:** Processing service runs `populate_stats()` function
```python
# processing/app.py line 159
temp_response = requests.get(
    'http://localhost:8090/temperature',
    params={'start_timestamp': '2000-01-01T00:00:00Z', 
            'end_timestamp': '2025-10-09T16:00:00Z'}
)
```

**Step 2:** HTTP GET request sent to Storage service
```
GET http://localhost:8090/temperature?start_timestamp=2000-01-01T00:00:00Z&end_timestamp=2025-10-09T16:00:00Z
```

**Step 3:** Storage service receives request and queries MySQL
```python
# storage/app.py - get_temperature_readings function
start_datetime = datetime.fromisoformat(start_timestamp.replace('Z', '+00:00'))
end_datetime = datetime.fromisoformat(end_timestamp.replace('Z', '+00:00'))

statement = select(Temperature).where(
    Temperature.date_created >= start_datetime
).where(
    Temperature.date_created < end_datetime
)

results = session.execute(statement).scalars().all()
```

**Step 4:** MySQL executes query
```sql
SELECT * FROM temperature 
WHERE date_created >= '2000-01-01 00:00:00' 
AND date_created < '2025-10-09 16:00:00'
-- Actual timestamps depend on the start_timestamp and end_timestamp parameters
```

**Step 5:** Storage service formats results as JSON and returns
```json
[
  {
    "trace_id": 123456789,
    "fire_id": "FIRE001",
    "temperature_celsius": 45.3,
    ...
  },
  {
    "trace_id": 123456790,
    "fire_id": "FIRE002", 
    "temperature_celsius": 38.7,
    ...
  }
]
```

**Step 6:** Processing service receives JSON response
```python
temp_readings = temp_response.json()
# temp_readings = [{"temperature_celsius": 45.3, ...}, {...}]
```

**Step 7:** Processing calculates statistics
```python
stats["num_temp_readings"] += len(temp_readings)  # Add count: 2
max_temp = max([r['temperature_celsius'] for r in temp_readings])  # Find max: 45.3
if max_temp > stats["max_temperature_celsius"]:
    stats["max_temperature_celsius"] = max_temp  # Update max: 45.3
```

**Step 8:** Processing saves statistics to data.json
```python
with open('data.json', 'w') as f:
    json.dump(stats, f)
```

**Step 9:** User requests statistics
```
GET http://localhost:8100/stats
```

**Step 10:** Processing reads and returns data.json
```json
{
    "num_temp_readings": 150,
    "max_temperature_celsius": 45.3,
    "num_airquality_readings": 123,
    "max_air_quality": 250,
    "last_updated": "2025-10-09T16:05:00Z"
}
```

---

## Why This Architecture?

### Benefits of Microservices Separation:

1. **Separation of Concerns**
   - Storage service: Database expert (handles MySQL)
   - Processing service: Statistics expert (calculates aggregates)
   - Receiver service: API gateway (accepts external data)

2. **Scalability**
   - Can run multiple Processing services
   - Storage service can be scaled independently
   - Each service can be deployed separately

3. **Maintainability**
   - Changes to database don't affect Processing code
   - Each service is smaller and easier to understand
   - Can test services independently

4. **Security**
   - Only Storage service has MySQL credentials
   - Processing doesn't need database access
   - Easier to control access to sensitive data

---

## Common Confusion Points - Answered!

### Q: "Where is it grabbing its data from?"
**A:** Processing grabs data from the **Storage service HTTP API** (port 8090), which then queries MySQL.

### Q: "How come when I read the code, I am seeing nothing that it is grabbing from the database itself?"
**A:** Because Processing doesn't query the database! Look for HTTP requests instead:
```python
# This is what you SHOULD look for in processing/app.py:
requests.get('http://localhost:8090/temperature', ...)
```

Not:
```python
# This is what you WON'T find in processing/app.py:
session.execute(select(Temperature).where(...))  # This is in storage/app.py!
```

### Q: "The datastore and filename - where does it read from?"
**A:** Two different data stores:
1. **MySQL database** (Docker) - Stores ALL raw events - Used by Storage service
2. **data.json file** (local) - Stores ONLY statistics - Used by Processing service

### Q: "Why is num_temp_readings showing 0?"
**A:** Possible reasons:
1. MySQL database is empty (no data has been POSTed)
2. The `last_updated` timestamp in data.json is too recent (after your data)
3. Storage service is not running
4. MySQL Docker container is not running

**Solution:** Delete data.json and restart Processing service to query from year 2000

---

## How to Test the Complete Flow

### 1. Start MySQL
```bash
docker-compose up -d
```

### 2. Start Storage Service
```bash
cd storage
python app.py
```

### 3. Verify Storage can access MySQL
```bash
# Should return JSON array (empty if no data)
curl "http://localhost:8090/temperature?start_timestamp=2000-01-01T00:00:00Z&end_timestamp=2025-12-31T23:59:59Z"
```

### 4. Start Processing Service
```bash
cd processing
python app.py
```

### 5. Check Statistics
```bash
curl http://localhost:8100/stats
```

### 6. Add Data (Optional)
```bash
cd receiver
python app.py
# Then POST data via http://localhost:8080/ui
```

### 7. Wait 5 Seconds and Check Again
```bash
curl http://localhost:8100/stats
```

Statistics should now reflect the data in MySQL!

---

## Key Files to Examine

### To understand MySQL queries:
**File:** `storage/app.py`
**Functions:** `get_temperature_readings()` and `get_airquality_readings()`
**Look for:** `select(Temperature).where(...)` and `session.execute(...)`

### To understand HTTP requests:
**File:** `processing/app.py`
**Function:** `populate_stats()` - Look in Steps 3 and 4
**Look for:** `requests.get(app_config['eventstores']['temperature']['url'], params={...})`

### To understand data flow:
**File:** `processing/app.py`
**Lines:** 106-215 (populate_stats function with detailed comments)

---

## Summary

**The key insight:** Processing service uses **HTTP REST API** to get data, not direct database access!

```
Processing Service --[HTTP GET]--> Storage Service --[SQL Query]--> MySQL Database
```

The Processing service code will have:
- ✅ `requests.get()` calls
- ❌ NO `select()` or `session.execute()` database calls

The Storage service code will have:
- ✅ `select()` and `session.execute()` database calls
- ✅ `@app.route()` or connexion endpoints that Processing calls

This is by design! It's a proper microservices architecture where services communicate via HTTP APIs.
