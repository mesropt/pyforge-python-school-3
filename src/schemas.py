from pydantic import BaseModel


class MoleculeBase(BaseModel):
    name: str
    smiles: str
    weight: float
    formula: str


class Molecule(MoleculeBase):
    id: int

    class ConfigDict:
        from_attributes = True


class MoleculeCreate(MoleculeBase):
    pass


class MoleculeUpdate(MoleculeBase):
    pass


class MoleculeUpdateMessage(MoleculeBase):
    message: str


class MoleculeInDB(MoleculeBase):
    id: int

    class ConfigDict:
        from_attributes = True


class MoleculeResponse(BaseModel):
    molecule: Molecule
    message: str
