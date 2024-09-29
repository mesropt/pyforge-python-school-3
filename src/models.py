from pydantic import BaseModel


class Molecule(BaseModel):
    id: int
    name: str
    smiles: str
    weight: float
    formula: str


class MoleculeUpdate(BaseModel):
    name: str
    smiles: str
    weight: float
    formula: str
