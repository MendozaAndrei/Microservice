# Processing Service - Quick Start Guide

## TL;DR - Your Question Answered

**Q: Where is the Processing service grabbing data from?**

**A: It queries the Storage service via HTTP at `http://localhost:8090/temperature` and `http://localhost:8090/airquality`**

The Processing service **does NOT directly access MySQL**. It's a microservices architecture!

```
Processing --[HTTP GET]--> Storage --[SQL Query]--> MySQL
```

## Quick Architecture Overview

```
User POSTs data
    ↓
Receiver Service (8080)
    ↓ HTTP POST
Storage Service (8090)
    ↓ SQL INSERT
MySQL Database ✅ Data stored here
    ↑ SQL SELECT
Storage Service (8090)
    ↑ HTTP GET
Processing Service (8100)
    ↓ Calculate stats
data.json ✅ Statistics saved here
```

## Key Points

1. **Processing makes HTTP requests** (line 159 & 185 in app.py)
   ```python
   temp_response = requests.get('http://localhost:8090/temperature', params={...})
   ```

2. **Storage queries MySQL** (storage/app.py lines 161-165)
   ```python
   statement = select(Temperature).where(Temperature.date_created >= start_datetime)
   ```

3. **Two data stores:**
   - MySQL: All raw sensor readings (temperature, air quality)
   - data.json: Just 5 statistics (counts and max values)

## Where to Find What

| What You're Looking For | File to Read |
|------------------------|--------------|
| How Processing queries Storage | `processing/app.py` (lines 153-177, 179-203) |
| Actual MySQL queries | `storage/app.py` (lines 150-205) |
| Complete architecture | `../ARCHITECTURE.md` |
| How to run/troubleshoot | `README.md` (this folder) |
| Summary of all changes | `../CHANGES_SUMMARY.md` |

## Common Issues

### Statistics showing zeros?

1. Check MySQL has data:
   ```bash
   docker exec -it microservice-db-1 mysql -u skibidi -phelpme fire_data -e "SELECT COUNT(*) FROM temperature;"
   ```

2. Delete data.json and restart Processing:
   ```bash
   rm data.json
   python app.py
   ```

3. Check logs:
   ```bash
   tail -f app.log
   # Should see: "Received X NEW temperature readings from MySQL (via Storage service)"
   ```

## To View Statistics

```bash
curl http://localhost:8100/stats
```

Or open in browser: http://localhost:8100/stats

## Read Next

- **README.md** (this folder) - Complete guide with troubleshooting
- **../ARCHITECTURE.md** - Detailed explanation of data flow
- **../CHANGES_SUMMARY.md** - Summary of what was changed
