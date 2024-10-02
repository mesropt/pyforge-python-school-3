import os

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from rdkit import Chem

from src import crud, models, schemas
from src.database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/add/molecule", response_model=schemas.MoleculeResponse)
def add_molecule(molecule: schemas.MoleculeCreate, db: Session = Depends(get_db)):
    db_molecule = crud.get_molecule_by_name(db, name=molecule.name)
    if db_molecule:
        raise HTTPException(status_code=400, detail="Molecule already exists.")

    db_molecule = crud.add_molecule(db=db, molecule=molecule)

    return {"molecule": db_molecule, "message": "Molecule added successfully."}


@app.get("/molecule/{molecule_id}", response_model=schemas.Molecule)
def get_molecule_by_id(molecule_id: int, db: Session = Depends(get_db)):
    db_molecule = crud.get_molecule_by_id(db, molecule_id=molecule_id)
    if db_molecule is None:
        raise HTTPException(status_code=404, detail="Molecule not found.")
    return db_molecule


@app.get("/molecules_list", response_model=list[schemas.Molecule])
def get_all_molecules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    db_molecules = crud.get_all_molecules(db, skip=skip, limit=limit)
    if db_molecules is None:
        raise HTTPException(status_code=404, detail="Molecules not found.")
    return db_molecules


@app.put("/update/molecule/{molecule_id}", response_model=schemas.MoleculeResponse)
def update_molecule(molecule_id: int, molecule: schemas.MoleculeUpdate,
                    db: Session = Depends(get_db)):
    db_molecule = crud.get_molecule_by_id(db, molecule_id=molecule_id)
    if not db_molecule:
        raise HTTPException(status_code=404, detail="Molecule not found.")

    db_molecule.name = molecule.name
    db_molecule.smiles = molecule.smiles
    db_molecule.weight = molecule.weight
    db_molecule.formula = molecule.formula

    db.commit()
    db.refresh(db_molecule)

    return {"molecule": db_molecule, "message": "Molecule updated successfully."}


@app.delete("/delete/molecule/{molecule_id}")
def delete_molecule(molecule_id: int, db: Session = Depends(get_db)):
    db_molecule = crud.get_molecule_by_id(db, molecule_id=molecule_id)
    if db_molecule is None:
        raise HTTPException(status_code=404, detail="Molecule not found.")
    db.delete(db_molecule)
    db.commit()
    return {"detail": f"Molecule with id {molecule_id} deleted successfully."}


@app.get("/substructure_search")
def substructure_search(substructure: str, db: Session = Depends(get_db)):
    """
    SMILES (Simplified Molecular Input Line Entry System) is a textual representation
    of the structure of a molecule, convenient for storing and transmitting information.
    """
    try:
        desired_substructure = Chem.MolFromSmiles(substructure)

        # Validate substructure
        if not desired_substructure:
            raise HTTPException(status_code=400, detail="Invalid substructure SMILES")

        molecules = crud.get_all_molecules(db)

        result = []

        # Iterate over the stored molecules
        for molecule in molecules:
            try:
                smile = molecule.smiles
                rdkit_molecule = Chem.MolFromSmiles(smile)

                if (rdkit_molecule and rdkit_molecule.
                        HasSubstructMatch(desired_substructure)
                ):
                    result.append({
                        "id": molecule.id,
                        "smiles": smile,
                        "name": molecule.name,
                        "weight": molecule.weight,
                        "formula": molecule.formula
                    })
            except Exception as e:
                print(f"Error processing molecule with ID {molecule.id}: {e}")

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


# 7. [Optional] Upload file with molecules (the choice of format is yours).
@app.post("/upload_image")
def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Use png or jpeg."
        )

    try:
        file_location = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_location, "wb") as f:
            f.write(file.file.read())

        return {
            "message": "Image uploaded successfully.",
            "file_path": file_location
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error: {str(e)}')

# Start the server using: uvicorn src.main:app --reload --port 8010


@app.get("/")
def get_server():
    return {"server_id": os.getenv("SERVER_ID", "1")}
