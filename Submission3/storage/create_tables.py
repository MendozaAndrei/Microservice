from app import Base, mysql

Base.metadata.create_all(mysql)
print("Tables created")
