import json
import os
import logging
import time

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from rdkit import Chem
import redis

from src import crud, models, schemas
from src.database import engine, get_db

from src.tasks import async_substructure_search_task
from celery.result import AsyncResult
from src.celery_worker import celery


FORMAT = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
logging.basicConfig(
    level=logging.INFO, # INFO and above (INFO, WARNING, ERROR, CRITICAL).
    format=FORMAT,
    handlers=[
        logging.FileHandler('app.log'), # logging to the file.
        logging.StreamHandler(), # logging to the console.
    ]
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Redis Start
redis_client = redis.Redis(host='redis', port=6379, db=0)

def get_cached_result(key: str):
    result = redis_client.get(key)
    if result:
        return json.loads(result)
    return None

def set_cache(key: str, value: dict, expiration: int = 3600): # 3600 = 1 hour
    redis_client.setex(key, expiration, json.dumps(value))
# Redis End

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

    return {"molecule": db_molecule, "message": "Molecule added successfully. Edited."}


@app.get("/molecule/{molecule_id}", response_model=schemas.Molecule)
def get_molecule_by_id(molecule_id: int, db: Session = Depends(get_db)):
    cache_key = f'molecule:{molecule_id}'

    # 1. If the search result is found in the cache, return it immediately:
    try:
        cached_result = get_cached_result(cache_key)
        if cached_result:
            logging.info(f'Molecule with {molecule_id} found in cache.')
            return cached_result
    except redis.RedisError as e:
        logging.warning(f'Redis is unavaliable: {e}')

    # 2.1. If the search result is not cached, perform the search, cache the result, and then return it:
    db_molecule = crud.get_molecule_by_id(db, molecule_id=molecule_id)
    if db_molecule is None:
        logging.info(f'Molecule with ID {molecule_id} not found.')
        raise HTTPException(status_code=404, detail="Molecule not found.")

    molecule_data = {
        'id': db_molecule.id,
        'name': db_molecule.name,
        'smiles': db_molecule.smiles,
        'weight': db_molecule.weight,
        'formula': db_molecule.formula,
    }

    # 2.2. Cache the result and then return it:
    try:
        set_cache(cache_key, molecule_data, expiration=60)
        logging.info(f'Molecule {db_molecule.name} with {db_molecule.id} added to cache.')
    except redis.RedisError as e:
        logging.warning(f'Could not cache data for molecule ID {molecule_id}: {e}')

    return db_molecule


@app.get("/molecules_list", response_model=list[schemas.Molecule])
def get_all_molecules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    cache_key = f'molecules_list:skip={skip}:limit={limit}'

    # 1. If the search result is found in the cache, return it immediately:
    try:
        cached_result = get_cached_result(cache_key)
        if cached_result:
            logging.info(f'Molecule list with skip={skip} and limit={limit} found in cache.')
            return cached_result
    except redis.RedisError as e:
        logging.warning(f'Redis is unavaliable: {e}')

    # 2.1. If the search result is not cached, perform the search, cache the result, and then return it:
    db_molecules = crud.get_all_molecules(db, skip=skip, limit=limit)
    if not db_molecules:
        logging.warning('No molecules found.')
        raise HTTPException(status_code=404, detail="Molecules not found.")

    molecules_data = [
        {
            'id': molecule.id,
            'name': molecule.name,
            'smiles': molecule.smiles,
            'weight': molecule.weight,
            'formula': molecule.formula
        } for molecule in db_molecules
    ]

    # 2.2. Cache the result and then return it:
    try:
        set_cache(cache_key, molecules_data, expiration=60)
        logging.info(f'List of molecules successfully added to cache with skip={skip} and limit={limit}.')
    except redis.RedisError as e:
        logging.warning(f'Could not cache molecule list for skip={skip} and limit={limit}: {e}')

    return db_molecules

@app.get("/molecule_no_cache/{molecule_id}", response_model=schemas.Molecule)
def get_molecule_by_id_no_cache(molecule_id: int, db: Session = Depends(get_db)):
    logging.info('Getting molecule with ID: molecule_id.')
    db_molecule = crud.get_molecule_by_id(db, molecule_id=molecule_id)
    if db_molecule is None:
        logging.info(f'Molecule with ID {molecule_id} not found.')
        raise HTTPException(status_code=404, detail="Molecule not found.")
    logging.info(f'Molecule retrieved successfully: {db_molecule.name}')
    return db_molecule


@app.get("/molecules_list_no_cache", response_model=list[schemas.Molecule])
def get_all_molecules_no_cache(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
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
    logging.info(f'Deleting molecule with ID: {molecule_id}')
    db_molecule = crud.get_molecule_by_id(db, molecule_id=molecule_id)
    if db_molecule is None:
        logging.warning(f'Molecule with ID {molecule_id} not found.')
        raise HTTPException(status_code=404, detail="Molecule not found.")
    db.delete(db_molecule)
    db.commit()
    logging.info(f'Molecule with ID {molecule_id} deleted successfully: {db_molecule.name}')

    return {"detail": f"Molecule with id {molecule_id} deleted successfully."}


@app.get("/sync_substructure_search")
def sync_substructure_search(substructure: str, db: Session = Depends(get_db)):
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

@app.post("/tasks/async_substructure_search")
async def create_async_substructure_search_task(substructure: str):
    """
    We send a request to start the substructure search task and then
    in get_async_substructure_search_task_result we can send request
    to get results if it is ready as shown in the example.
    """
    task = async_substructure_search_task.delay(substructure)
    return {"task_id": task.id, "status": task.status}

@app.get("/tasks/{task_id}")
async def get_async_substructure_search_task_result(task_id: str):
    task_result = AsyncResult(task_id, app=celery)
    if task_result.state == 'PENDING':
        return {"task_id": task_id, "status": "Task is still processing"}
    elif task_result.state == 'SUCCESS':
        return {"task_id": task_id, "status": "Task completed", "result": task_result.result}
    else:
        return {"task_id": task_id, "status": task_result.state}