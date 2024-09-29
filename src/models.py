from pydantic import BaseModel

class Molecule(BaseModel):
    id: int
    name: str
    smiles: str
    weight: float
    formula: str


"""
Проблема с тестами в FastAPI при обновлении объекта
В тесте test_update_molecule_by_id я постоянно получал статус 422, что свидетельствовало о проблеме валидации.
Как оказалось, тесты, связанные с обновлением объекта в FastAPI, не работают из-за конфликта 
между параметром id, передаваемым в URL (в качестве параметра пути), и тем же id, 
который передается в теле запроса при обновлении объекта. Этот конфликт возникает из-за того, 
что FastAPI использует Pydantic для валидации данных, и наличие id в обоих местах вызывает 
несоответствия и ошибки валидации.

Причина: Когда в запросе обновления используется параметр пути id, одновременно 
передавая этот же идентификатор в теле запроса, возникает избыточность. 
В результате, если значения id не совпадают или если одно из них не нужно, 
это может привести к ошибкам. Такая практика противоречит RESTful принципам, 
где идентификатор объекта обычно передается только в URL, а тело запроса должно содержать 
лишь данные, которые необходимо обновить.

Решение: Для решения проблемы необходимо изменить архитектуру моделей: разделить модели 
для создания и обновления объекта. Модель для обновления не должна содержать поле id, 
чтобы избежать конфликта с параметром пути. 

Поэтому я ввёл модель MoleculeUpdate.
"""
class MoleculeUpdate(BaseModel):
    name: str
    smiles: str
    weight: float
    formula: str