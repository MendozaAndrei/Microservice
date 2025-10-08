import connexion
from sqlalchemy import create_engine, Integer, String, Float, DateTime, func
from sqlalchemy.orm import DeclarativeBase, mapped_column, sessionmaker
from datetime import datetime

mysql = create_engine("sqlite:///storage.db", future=True)
SessionLocal = sessionmaker(bind=mysql)


class Base(DeclarativeBase):
    pass

# I don't know where you'd want this to be in so I just added in app.py storage
class Temperature(Base):
    __tablename__ = "temperature"
    id = mapped_column(Integer, primary_key=True)
    fire_id = mapped_column(String(250), nullable=False)
    latitude = mapped_column(Float, nullable=False)
    longitude = mapped_column(Float, nullable=False)
    temperature_celsius = mapped_column(Float, nullable=False)
    humidity_level = mapped_column(Float, nullable=True)
    batch_timestamp = mapped_column(DateTime, nullable=False)
    reading_timestamp = mapped_column(DateTime, nullable=False)
    date_created = mapped_column(DateTime, nullable=False, default=func.now())


class AirQuality(Base):
    __tablename__ = "airquality"
    id = mapped_column(Integer, primary_key=True)
    fire_id = mapped_column(String(250), nullable=False)
    location_name = mapped_column(String(250), nullable=False)
    particulate_level = mapped_column(Float, nullable=False)
    air_quality = mapped_column(Float, nullable=False)
    smoke_opacity = mapped_column(Float, nullable=False)
    batch_timestamp = mapped_column(DateTime, nullable=False)
    reading_timestamp = mapped_column(DateTime, nullable=False)
    date_created = mapped_column(DateTime, nullable=False, default=func.now())


def create_temperature_reading(body):
    session = SessionLocal()
    # try:
    humidity = None
    if "humidity_level" in body and body["humidity_level"] is not None:
        humidity = float(body["humidity_level"])
    # Time stamps are formatted differently, so I added this to convert them into the datetime format to remove any conflicts
    batch_timestamp = datetime.fromisoformat(body["batch_timestamp"].replace('Z', '+00:00'))
    reading_timestamp = datetime.fromisoformat(body["reading_timestamp"].replace('Z', '+00:00'))
        
    event = Temperature(
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
    return {"message": "stored"}, 201
    # except Exception as e:
    #     # session.rollback()
    #     # print(f"Error storing temperature reading: {e}")
    #     return {"error": str(e)}, 500
    # finally:


def create_airquality_reading(body):
    session = SessionLocal()
    # try:
    batch_timestamp = datetime.fromisoformat(body["batch_timestamp"].replace('Z', '+00:00'))
    reading_timestamp = datetime.fromisoformat(body["reading_timestamp"].replace('Z', '+00:00'))
    
    event = AirQuality(
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
    return {"message": "stored"}, 201
    # except Exception as e:
    #     # session.rollback()
    #     # print(f"Error storing air quality reading: {e}")
    #     return {"error": str(e)}, 500
    # finally:

# I changed the name of the lab1.yaml from the receiver folder to openapi.yaml
app = connexion.App(__name__, specification_dir=".")
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8090)
