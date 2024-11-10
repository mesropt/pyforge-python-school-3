import json
import os
import logging

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from rdkit import Chem
import redis

from src import crud, models, schemas
from src.database import engine, get_db


FORMAT = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
logging.basicConfig(
    level=logging.INFO, # INFO и выше (INFO, WARNING, ERROR, CRITICAL)
    format=FORMAT,
    handlers=[
        logging.FileHandler('app.log'), # логируем в файл
        logging.StreamHandler(), # логируем в консоль
    ]
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# TODO:
####### Connect to Redis
redis_client = redis.Redis(host='redis', port=6379, db=0)

def get_cached_result(key: str):
    result = redis_client.get(key)
    if result:
        return json.loads(result)
    return None

def set_cache(key: str, value: dict, expiration: int = 60):
    redis_client.setex(key, expiration, json.dumps(value))

@app.get("/search/")
async def search(query: str):
    cache_key = f"search:{query}"
    cached_result = get_cached_result(cache_key)

    if cached_result:
        return {"source": "cache", "data": cached_result}

    # Simulate a search operation (e.g., querying a database)
    search_result = {"query": query, "result": "Some data"}  # Replace with actual search logic

    set_cache(cache_key, search_result)

    return {"source": "database", "data": search_result}
#######

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/add/molecule", response_model=schemas.MoleculeResponse)
def add_molecule(molecule: schemas.MoleculeCreate, db: Session = Depends(get_db)):
    logging.info(f'Adding molecule: {molecule.name}')
    db_molecule = crud.get_molecule_by_name(db, name=molecule.name)
    if db_molecule:
        logging.warning(f'Molecule already exists: {molecule.name}')
        raise HTTPException(status_code=400, detail="Molecule already exists.")

    db_molecule = crud.add_molecule(db=db, molecule=molecule)
    logging.info(f'Molecule added successfully: {molecule.name}')

    return {"molecule": db_molecule, "message": "Molecule added successfully."}


@app.get("/molecule/{molecule_id}", response_model=schemas.Molecule)
def get_molecule_by_id(molecule_id: int, db: Session = Depends(get_db)):
    logging.info('Getting molecule with ID: molecule_id.')
    db_molecule = crud.get_molecule_by_id(db, molecule_id=molecule_id)
    if db_molecule is None:
        logging.info(f'Molecule with ID {molecule_id} not found.')
        raise HTTPException(status_code=404, detail="Molecule not found.")
    logging.info(f'Molecule retrieved successfully: {db_molecule.name}')
    return db_molecule


@app.get("/molecules_list", response_model=list[schemas.Molecule])
def get_all_molecules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logging.info(f'Getting molecules with skip={skip} and limit={limit}.')
    db_molecules = crud.get_all_molecules(db, skip=skip, limit=limit)
    if db_molecules is None:
        logging.warning('No molecules found.')
        raise HTTPException(status_code=404, detail="Molecules not found.")
    logging.info(f'Got {len(db_molecules)} molecules.')
    return db_molecules


@app.put("/update/molecule/{molecule_id}", response_model=schemas.MoleculeResponse)
def update_molecule(molecule_id: int, molecule: schemas.MoleculeUpdate,
                    db: Session = Depends(get_db)):
    logging.info(f'Updating {molecule.name} molecule with ID: {molecule_id}')
    db_molecule = crud.get_molecule_by_id(db, molecule_id=molecule_id)
    if not db_molecule:
        logging.warning(f'Molecule with ID {molecule_id} not found.')
        raise HTTPException(status_code=404, detail="Molecule not found.")

    db_molecule.name = molecule.name
    db_molecule.smiles = molecule.smiles
    db_molecule.weight = molecule.weight
    db_molecule.formula = molecule.formula

    db.commit()
    db.refresh(db_molecule)
    logging.info(f'Molecule with ID {molecule_id} updated successfully: {db_molecule.name}')

    return {"molecule": db_molecule, "message": "Molecule updated successfully."}


@app.delete("/delete/molecule/{molecule_id}")
def delete_molecule(molecule_id: int, db: Session = Depends(get_db)):
    logging.ingo(f'Deleting molecule with ID: {molecule_id}')
    db_molecule = crud.get_molecule_by_id(db, molecule_id=molecule_id)
    if db_molecule is None:
        logging.warning(f'Molecule with ID {molecule_id} not found.')
        raise HTTPException(status_code=404, detail="Molecule not found.")
    db.delete(db_molecule)
    db.commit()
    logging.info(f'Molecule with ID {molecule_id} deleted successfully: {db_molecule.name}')

    return {"detail": f"Molecule with id {molecule_id} deleted successfully."}


@app.get("/substructure_search")
def substructure_search(substructure: str, db: Session = Depends(get_db)):
    """
    SMILES (Simplified Molecular Input Line Entry System) is a textual representation
    of the structure of a molecule, convenient for storing and transmitting information.
    """
    logging.info(f'Starting substructure search for {substructure}')
    try:
        desired_substructure = Chem.MolFromSmiles(substructure)

        # Validate substructure
        if not desired_substructure:
            logging.warning(f'Substructure {substructure} is not valid.')
            raise HTTPException(status_code=400, detail="Invalid substructure SMILES")

        molecules = crud.get_all_molecules(db)

        result = []

        # Iterate over the stored molecules
        for molecule in molecules:
            try:
                smile = molecule.smiles
                rdkit_molecule = Chem.MolFromSmiles(smile)

                if (rdkit_molecule and
                        rdkit_molecule.HasSubstructMatch(desired_substructure)):
                    result.append({
                        "id": molecule.id,
                        "smiles": smile,
                        "name": molecule.name,
                        "weight": molecule.weight,
                        "formula": molecule.formula
                    })
            except Exception as e:
                logging.error(f'Error processing molecule with ID {molecule.id}: {e}')

        logging.info(f'Finished substructure search for {substructure} with {len(result)} molecules.')
        return result

    except Exception as e:
        logging.error(f'Error in substructure search for {substructure}: {e}')
        raise HTTPException(status_code=500, detail=f"Error: {e}")


# 7. [Optional] Upload file with molecules (the choice of format is yours).
@app.post("/upload_image")
def upload_image(file: UploadFile = File(...)):
    logging.info(f'Uploading image: {file.filename}')
    if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
        logging.warning(f'Image type is not supported: {file.content_type}.')
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Use png or jpeg."
        )

    try:
        file_location = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_location, "wb") as f:
            f.write(file.file.read())
        logging.info(f'Image uploaded successfully: {file_location}.')

        return {
            "message": "Image uploaded successfully.",
            "file_path": file_location
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error: {str(e)}')


@app.get("/")
def get_server():
    server_id = os.getenv("SERVER_ID", "1")
    logging.info(f'Accessed server with {server_id} ID.')
    return {"server_id": server_id}


# Start the server using: uvicorn src.main:app --reload --port 8015
