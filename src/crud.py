from sqlalchemy.orm import Session
from . import models, schemas


def add_molecule(db: Session, molecule: schemas.MoleculeCreate):
    db_molecule = models.Molecule(**molecule.dict())
    db.add(db_molecule)
    db.commit()
    db.refresh(db_molecule)
    return db_molecule


def get_molecule_by_id(db: Session, molecule_id: int):
    return db.query(models.Molecule).filter(models.Molecule.id == molecule_id).first()


def get_molecule_by_name(db: Session, name: str):
    return db.query(models.Molecule).filter(models.Molecule.name == name).first()


def get_all_molecules(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Molecule).offset(skip).limit(limit).all()


def update_molecule(
        db: Session,
        molecule_id: int,
        molecule_data: schemas.MoleculeUpdate,
):
    db_molecule = get_molecule_by_id(db, molecule_id)
    if db_molecule:
        for key, value in molecule_data.dict().items():
            setattr(db_molecule, key, value)
        db.commit()
        db.refresh(db_molecule)
    return db_molecule


def delete_molecule(db: Session, molecule_id: int):
    db_molecule = get_molecule_by_id(db, molecule_id)
    if db_molecule:
        db.delete(db_molecule)
        db.commit()
