import connexion
from sqlalchemy import create_engine, Integer, String, Float, DateTime, func, BigInteger, text, select
from sqlalchemy.orm import DeclarativeBase, mapped_column, sessionmaker
from datetime import datetime
import pymysql
import yaml
import logging.config

#================= Lab 4 Code Added ==============================
#Opens the app_conf.yml configuration to load. 
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

#Opens the log_conf.yml for configuration
with open("log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

# MySQL connection Grabbed from app_conf.yml
# Storage.db will be completely useless and all. 
db_config = app_config['datastore']
try:
    #Uses "keys" to grab the value and to create the things needed to connect to the network. 
    connection_string = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['hostname']}:{db_config['port']}/{db_config['db']}"
    mysql = create_engine(connection_string, future=True)
    # Logs that the connection is successful and is connected
    logger.info("Connected to the database")
except Exception as e:
    logger.error(f"Error: {e}")
    mysql = create_engine("sqlite:///storage.db", future=True)

SessionLocal = sessionmaker(bind=mysql)

#Required for the MySQL Mapping. (Received a little help for this one.)
# Without the base declarative I receive the error of failure. 
class Base(DeclarativeBase):
    pass

# I don't know where you'd want this to be in so I just added in app.py storage
class Temperature(Base):
    __tablename__ = "temperature"
    id = mapped_column(Integer, primary_key=True)
    trace_id = mapped_column(BigInteger, nullable=False)
    fire_id = mapped_column(String(250), nullable=False)
    latitude = mapped_column(Float, nullable=False)
    longitude = mapped_column(Float, nullable=False)
    temperature_celsius = mapped_column(Float, nullable=False)
    humidity_level = mapped_column(Float, nullable=True)
    batch_timestamp = mapped_column(DateTime, nullable=False)
    reading_timestamp = mapped_column(DateTime, nullable=False)
    date_created = mapped_column(DateTime, nullable=False, default=func.now())

    def to_dict(self):
        """Convert Temperature object to dictionary matching the OpenAPI schema"""
        return {
            "trace_id": self.trace_id,
            "fire_id": self.fire_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "temperature_celsius": self.temperature_celsius,
            "humidity_level": self.humidity_level,
            "batch_timestamp": self.batch_timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "reading_timestamp": self.reading_timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        }


class AirQuality(Base):
    __tablename__ = "airquality"
    id = mapped_column(Integer, primary_key=True)
    trace_id = mapped_column(BigInteger, nullable=False)
    fire_id = mapped_column(String(250), nullable=False)
    location_name = mapped_column(String(250), nullable=False)
    particulate_level = mapped_column(Float, nullable=False)
    air_quality = mapped_column(Float, nullable=False)
    smoke_opacity = mapped_column(Float, nullable=False)
    batch_timestamp = mapped_column(DateTime, nullable=False)
    reading_timestamp = mapped_column(DateTime, nullable=False)
    date_created = mapped_column(DateTime, nullable=False, default=func.now())

    def to_dict(self):
        """Convert AirQuality object to dictionary matching the OpenAPI schema"""
        return {
            "trace_id": self.trace_id,
            "fire_id": self.fire_id,
            "location_name": self.location_name,
            "particulate_level": self.particulate_level,
            "air_quality": self.air_quality,
            "smoke_opacity": self.smoke_opacity,
            "batch_timestamp": self.batch_timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "reading_timestamp": self.reading_timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        }


def create_temperature_reading(body):
    session = SessionLocal()
    logger.debug(f"Storing {body['trace_id']} to the database")

    humidity = None
    if "humidity_level" in body and body["humidity_level"] is not None:
        humidity = float(body["humidity_level"])
    # Time stamps are formatted differently, so I added this to convert them into the datetime format to remove any conflicts
    batch_timestamp = datetime.fromisoformat(body["batch_timestamp"].replace('Z', '+00:00'))
    reading_timestamp = datetime.fromisoformat(body["reading_timestamp"].replace('Z', '+00:00'))
        
    event = Temperature(
        trace_id=int(body["trace_id"]),
        fire_id=body["fire_id"],
        latitude=float(body["latitude"]),
        longitude=float(body["longitude"]),
        temperature_celsius=float(body["temperature_celsius"]),
        humidity_level=humidity,
        batch_timestamp=batch_timestamp,
        reading_timestamp=reading_timestamp,
    )
    session.add(event)
    session.commit()
    session.close()
    # Log message when event is successfully stored
    logger.debug(f"Stored event temperature_reading with a trace id of {body['trace_id']}")
    return {"message": "stored"}, 201


def create_airquality_reading(body):
    session = SessionLocal()
    logger.debug(f"Storing {body['trace_id']} to the database")

    batch_timestamp = datetime.fromisoformat(body["batch_timestamp"].replace('Z', '+00:00'))
    reading_timestamp = datetime.fromisoformat(body["reading_timestamp"].replace('Z', '+00:00'))
    
    event = AirQuality(
        trace_id=int(body["trace_id"]),
        fire_id=body["fire_id"],
        location_name=body["location_name"],
        particulate_level=float(body["particulate_level"]),
        air_quality=float(body["air_quality"]),
        smoke_opacity=float(body["smoke_opacity"]),
        batch_timestamp=batch_timestamp,
        reading_timestamp=reading_timestamp,
    )
    session.add(event)
    session.commit()
    session.close()
    # Log message when event is successfully stored (after DB session is closed)
    logger.debug(f"Stored event airquality_reading with a trace id of {body['trace_id']}")
    return {"message": "stored"}, 201


def get_temperature_readings(start_timestamp, end_timestamp):
    """Gets temperature readings between the start and end timestamps"""
    session = SessionLocal()
    
    logger.info(f"Query for Temperature readings between {start_timestamp} and {end_timestamp}")
    
    # Convert ISO format timestamps to datetime objects
    start_datetime = datetime.fromisoformat(start_timestamp.replace('Z', '+00:00'))
    end_datetime = datetime.fromisoformat(end_timestamp.replace('Z', '+00:00'))
    
    # Query the database for readings within the timestamp range
    statement = select(Temperature).where(
        Temperature.date_created >= start_datetime
    ).where(
        Temperature.date_created < end_datetime
    )
    
    results = [
        result.to_dict()
        for result in session.execute(statement).scalars().all()
    ]
    
    session.close()
    
    logger.info(f"Query for Temperature readings returns {len(results)} results")
    
    return results, 200


def get_airquality_readings(start_timestamp, end_timestamp):
    """Gets air quality readings between the start and end timestamps"""
    session = SessionLocal()
    
    logger.info(f"Query for Air Quality readings between {start_timestamp} and {end_timestamp}")
    
    # Convert ISO format timestamps to datetime objects
    start_datetime = datetime.fromisoformat(start_timestamp.replace('Z', '+00:00'))
    end_datetime = datetime.fromisoformat(end_timestamp.replace('Z', '+00:00'))
    
    # Query the database for readings within the timestamp range
    statement = select(AirQuality).where(
        AirQuality.date_created >= start_datetime
    ).where(
        AirQuality.date_created < end_datetime
    )
    
    results = [
        result.to_dict()
        for result in session.execute(statement).scalars().all()
    ]
    
    session.close()
    
    logger.info(f"Query for Air Quality readings returns {len(results)} results")
    
    return results, 200


# I changed the name of the lab1.yaml from the receiver folder to openapi.yaml
app = connexion.App(__name__, specification_dir=".")
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8090)
