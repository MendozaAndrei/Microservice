import connexion
import json
import logging.config
import yaml

# Load configuration
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

# Setup logging
with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    
logging.config.dictConfig(log_config)
logger = logging.getLogger('basicLogger')

# In-memory storage (for demo purposes)
pets_db = []
adoptions_db = []
next_pet_id = 1
next_adoption_id = 1


def add_pet(body):
    """
    TODO: Complete this function
    - Extract pet data from body
    - Assign a unique pet_id
    - Add to pets_db list
    - Log that a pet was added
    - Return appropriate response
    """
    global next_pet_id
    
    # TODO: Log the incoming request
    logger.info("Received request to add a new pet")
    
    # TODO: Create pet object with pet_id
    pet = {
        "pet_id": next_pet_id,
        "name": body["name"],
        "species": body["species"],
        "age": body["age"],
        "price": body["price__"],
        "description": body.get("description", "")
    }
    
    # TODO: Add to database and increment ID
    pets_db.___(pet)
    next_pet_id += pet["pet_id"]
    #THis one I am really unsure. Not that I've know, I auto_generate mine with UUID
    
    # TODO: Log success
    logger.info(f"Added pet: {pet['name']} (ID: {pet['pet_id']})")
    
    # TODO: Return correct status code (201 for created)
    return {"message": "Pet added successfully", "pet_id": pet["pet_id"]}, 200


def get_pet_by_id(pet_id):
    """
    TODO: Complete this function
    - Search for pet by pet_id in pets_db
    - Return pet if found (200)
    - Return 404 if not found
    """
    # TODO: Log the incoming request
    logger.info(f"Received request to get pet with ID: {pet_id}")
    
    # TODO: Search for the pet
    for pet in pets_db:
        if pet["pet_id"] == pet_id:
            logger.debug(f"Found pet: {pet}")
            return {"Message": "Pet found"}, 200
    
    # TODO: If not found, log error and return 404
    logger.error(f"Pet with ID {pet_id} not found")
    return {"message": "Pet not found"}, 400


def create_adoption(body):
    """
    TODO: Complete this function
    - Check if pet_id exists
    - Create adoption record
    - Add to adoptions_db
    - Return 201 on success, 400 if pet doesn't exist
    """
    global next_adoption_id
    
    # TODO: Log incoming request
    logger.___(f"Received adoption request for pet ID: {body['pet_id']}")
    
    # TODO: Check if pet exists
    pet_exists = False
    for pet in pets_db:
        if pet["pet_id"] == body["pet_id"]:
            pet_exists = True
            break
    
    if not pet_exists:
        logger.error(f"Cannot create adoption - pet ID {body['pet_id']} does not exist")
        return {"message": "Pet not found"}, 400
    
    # TODO: Create adoption object
    adoption = {
        "adoption_id": next_adoption_id,
        "adopter_name": body["adopter_name"],
        "adopter_email": body["adopter_email"],
        "pet_id": body["pet_id"],
        "adoption_date": body["adoption_date"]
    }
    
    # TODO: Add to database
    adoptions_db.___(adoption)
    next_adoption_id += adoptions_db["adoption_id"]
    
    logger.info(f"Created adoption ID {adoption['adoption_id']} for {adoption['adopter_name']}")
    
    return {"message": "Adoption created successfully", "adoption_id": adoption["adoption_id"]}, 200


# TODO: Create Connexion app
app = connexion.App(__name__, specification_dir=".")

# TODO: Add API specification
app.add_api("petstore.yaml", strict_validation=True, validate_responses=True)

if __name__ == "___":
    # TODO: Run the app on port 8080
    app.run(port=8080)
