from ..models import Funcionario, Pagina, Setor
from ._base_crud import criar_router

router = criar_router(
    model=Setor,
    prefix="/setores",
    singular="Setor",
    plural="Setores",
    maxlen=150,
    contar_usos=lambda db, s: db.query(Funcionario).filter(Funcionario.setor_id == s.id).count(),
    pagina=Pagina.SETORES,
)
