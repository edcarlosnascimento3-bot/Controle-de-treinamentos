from ..models import Cargo, Funcionario, Pagina
from ._base_crud import criar_router

router = criar_router(
    model=Cargo,
    prefix="/cargos",
    singular="Cargo",
    plural="Cargos",
    maxlen=150,
    contar_usos=lambda db, c: db.query(Funcionario).filter(Funcionario.cargo_id == c.id).count(),
    pagina=Pagina.CARGOS,
)
