# Processing Service (Statistics & Data Aggregation)

## 🎯 Purpose
The Processing service is a **data aggregation microservice** that periodically collects events from the Storage service and calculates cumulative statistics.

## 📊 What It Does

### Main Functions:
1. **Periodic Data Collection**: Every 5 seconds, queries the Storage service for NEW events
2. **Statistics Calculation**: 
   - Counts total temperature readings
   - Counts total air quality readings
   - Tracks maximum temperature recorded
   - Tracks maximum air quality value
3. **Data Persistence**: Stores statistics in `data.json`
4. **API Endpoint**: Provides HTTP endpoint to retrieve current statistics

## 🏗️ Microservice Architecture Position

```
External Client
    |
    v
Receiver Service (Port 8080) - Receives batch events
    |
    v
Storage Service (Port 8090) - Stores events in MySQL database
    |
    v
Processing Service (Port 8100) - Calculates statistics from events
    |
    v
data.json (Statistics file)
```

## 🚀 How to Run

### Prerequisites:
1. Storage service must be running on port 8090
2. MySQL database must be running (via Docker)

### Start the Service:
```powershell
cd processing
python app.py
```

The service will:
- Start on port 8100
- Begin processing statistics every 5 seconds
- Log activity to `app.log`

## 🌐 How to Access

### REST API Endpoint:
```
GET http://localhost:8100/stats
```

### Swagger UI (Interactive API Docs):
```
http://localhost:8100/ui
```

### Test with curl:
```powershell
curl http://localhost:8100/stats
```

### Test with browser:
Simply open: `http://localhost:8100/stats`

## 📄 Example Response

```json
{
    "num_temp_readings": 150,
    "max_temperature_celsius": 145.8,
    "num_airquality_readings": 120,
    "max_air_quality": 250.5,
    "last_updated": "2025-10-09T08:45:30Z"
}
```

## ⚙️ Configuration Files

### app_conf.yml
```yaml
datastore:
  filename: data.json          # Where statistics are stored
scheduler:
  interval: 5                  # How often to process (seconds)
eventstores:
  temperature:
    url: http://localhost:8090/temperature    # Storage service endpoint
  airquality:
    url: http://localhost:8090/airquality     # Storage service endpoint
```

### log_conf.yml
Contains logging configuration (INFO level by default)

## 🔄 How the Periodic Processing Works

### Timeline Example:
```
Time 0s (First Run):
- Last Updated: 2000-01-01T00:00:00Z (default)
- Current Time: 2025-10-09T08:00:00Z
- Queries ALL historical events
- Updates statistics
- Saves last_updated = 2025-10-09T08:00:00Z

Time 5s (Second Run):
- Last Updated: 2025-10-09T08:00:00Z
- Current Time: 2025-10-09T08:00:05Z
- Queries ONLY events from last 5 seconds
- Adds to cumulative statistics
- Saves last_updated = 2025-10-09T08:00:05Z

Time 10s (Third Run):
- Last Updated: 2025-10-09T08:00:05Z
- Current Time: 2025-10-09T08:00:10Z
- Queries ONLY events from last 5 seconds
- And so on...
```

**Key Point**: Each run only processes NEW events since the last run, preventing duplicate counting!

## 📁 Files

- `app.py` - Main application with scheduler and API endpoint
- `openapi.yaml` - API specification (Swagger)
- `app_conf.yml` - Application configuration
- `log_conf.yml` - Logging configuration
- `data.json` - Statistics storage (created automatically)
- `app.log` - Application logs (created automatically)

## 🔍 Monitoring

### Check if it's working:
1. **Check the logs**: `app.log` should show periodic processing every 5 seconds
2. **Check the stats file**: `data.json` should update every 5 seconds
3. **Query the API**: `curl http://localhost:8100/stats`
4. **Watch the counts increase**: As you POST new events via Receiver, the counts should grow

## 🐛 Troubleshooting

### Problem: "Statistics do not exist" error
**Solution**: The service hasn't run its first processing cycle yet. Wait 5 seconds.

### Problem: Statistics not updating
**Solution**: 
1. Check if Storage service is running: `curl http://localhost:8090/temperature?start_timestamp=2000-01-01T00:00:00Z&end_timestamp=2025-10-09T23:59:59Z`
2. Check `app.log` for errors
3. Verify the scheduler is running (should see log entries every 5 seconds)

### Problem: Statistics counts are wrong
**Solution**: Delete `data.json` and restart the service to recalculate from scratch

## 💡 Testing the Service

### Full Test Flow:
```powershell
# 1. Start all services
cd storage
python app.py
# (In new terminal)
cd receiver  
python app.py
# (In new terminal)
cd processing
python app.py

# 2. Send test data via Receiver
# Use Swagger UI: http://localhost:8080/ui
# POST temperature or air quality readings

# 3. Wait 5-10 seconds for processing

# 4. Check statistics
curl http://localhost:8100/stats

# 5. Send more data and watch stats grow
```

## 📈 Statistics Explained

| Statistic | Description | Example |
|-----------|-------------|---------|
| `num_temp_readings` | Total count of all temperature readings ever received | 500 |
| `max_temperature_celsius` | Highest temperature value recorded across all readings | 145.8 |
| `num_airquality_readings` | Total count of all air quality readings ever received | 450 |
| `max_air_quality` | Highest air quality index recorded across all readings | 250.5 |
| `last_updated` | Timestamp of when statistics were last calculated | 2025-10-09T08:45:30Z |

## 🎓 Learning Points

This service demonstrates:
- **Background job scheduling** with APScheduler
- **Periodic data processing**
- **RESTful API consumption** (calling Storage service)
- **Cumulative statistics calculation**
- **Time-windowed queries** (only fetching new data)
- **JSON file-based persistence**
- **Microservice communication patterns**
