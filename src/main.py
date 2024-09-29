from fastapi import FastAPI, File, UploadFile, HTTPException
from rdkit import Chem
import os

from src.models import Molecule, MoleculeUpdate

app = FastAPI()

molecules = {
    1: {
        "name": "Ethanol",
        "smiles": "CCO",
        "weight": 46.06844,
        "formula": "C2H6O"
    },
    2: {
        "name": "water",
        "smiles": "[H]O[H]",
        "weight": 18.01530,
        "formula": "H2O"
    },
    3: {
        "name": "Methane",
        "smiles": "[H]C([H])([H])[H]",
        "weight": 16.04246,
        "formula": "CH4"
    },
    4: {
        "name": "Carbon Dioxide",
        "smiles": "O=C=O",
        "weight": 44.010,
        "formula": "CO2"
    },
    5: {
        "name": "Ammonia",
        "smiles": "c1ccccc1[H]N([H])[H]",
        "weight": 17.03056,
        "formula": "H3N"
    },
    6: {
        "name": "Glucose",
        "smiles": "C(C1C(C(C(C(O1)O)O)O)O)O",
        "weight": 180.15588,
        "formula": "C6H12O6"
    },
    7: {
        "name": "Sulfuric acid",
        "smiles": "[H]OS(=O)(=O)O[H]c1ccccc1",
        "weight": 98.07948,
        "formula": "H2O4S"
    },
    8: {
        "name": "Benzene",
        "smiles": "c1ccccc1",
        "weight": 78.11184,
        "formula": "C6H6"
    },
    9: {
        "name": "Aspirin",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "weight": 180.157,
        "formula": "C9H8O4"
    },
    10: {
        "name": "Sodium chloride",
        "smiles": "[Na+].[Cl-]",
        "weight": 58.44247,
        "formula": "ClNa"
    },
}

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# 1. Add molecule (smiles) and its identifier
@app.post("/add")
def add_molecule(molecule: Molecule):
    molecules[molecule.id] = {
        "name": molecule.name,
        "smiles": molecule.smiles,
        "weight": molecule.weight,
        "formula": molecule.formula
    }
    return {"message": "Molecule added successfully."}


# 2. Get molecule by identifier
@app.get("/molecule/{molecule_id}")
def get_molecule_by_id(molecule_id: int):
    if molecule_id in molecules:
        return molecules[molecule_id]
    else:
        raise HTTPException(status_code=404, detail='Molecule not found.')


# 3. Updating a molecule by identifier
@app.put("/update/molecule/{molecule_id}")
def update_molecule(molecule_id: int, molecule: MoleculeUpdate):
    if molecule_id in molecules:
        molecules[molecule_id] = {
            "name": molecule.name,
            "smiles": molecule.smiles,
            "weight": molecule.weight,
            "formula": molecule.formula
        }
        return {"message": "Molecule updated successfully."}
    else:
        raise HTTPException(status_code=404, detail="Molecule not found.")


# 4. Delete a molecule by identifier
@app.delete("/delete/molecule/{molecule_id}")
def delete_molecule(molecule_id: int):
    if molecule_id in molecules:
        del molecules[molecule_id]
        return {"message": "Molecule deleted successfully."}
    else:
        raise HTTPException(status_code=404, detail="Molecule not found.")


# 5. List all molecules
@app.get("/list")
def list_molecules():
    return {"molecules": molecules}


# 6. Substructure search for all added molecules
@app.get("/search")
def substructure_search(substructure: str):
    """
    SMILES (Simplified Molecular Input Line Entry System) is a textual representation
    of the structure of a molecule, convenient for storing and transmitting information.
    """
    try:
        desired_substructure = Chem.MolFromSmiles(substructure)

        # Validate substructure
        if not desired_substructure:
            raise HTTPException(status_code=400, detail="Invalid substructure SMILES")

        result = []

        # Iterate over the stored molecules
        for molecule_id, molecule_data in molecules.items():
            try:
                smile = molecule_data['smiles']
                molecule = Chem.MolFromSmiles(smile)

                if molecule and molecule.HasSubstructMatch(desired_substructure):
                    result.append({
                        "id": molecule_id,
                        "smiles": smile,
                        "name": molecule_data["name"],
                        "weight": molecule_data["weight"],
                        "formula": molecule_data["formula"]
                    })
            except Exception as e:
                print(f"Error: {molecule_id}: {e}")

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

# Start the server using: uvicorn main:app --reload --port 8010


@app.get("/")
def get_server():
    return {"server_id": os.getenv("SERVER_ID", "1")}
