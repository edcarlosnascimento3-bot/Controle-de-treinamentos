from ..models import Categoria, Pagina, Treinamento
from ._base_crud import criar_router

router = criar_router(
    model=Categoria,
    prefix="/categorias",
    singular="Categoria",
    plural="Categorias",
    maxlen=50,
    contar_usos=lambda db, c: db.query(Treinamento).filter(Treinamento.categoria == c.nome).count(),
    pagina=Pagina.CATEGORIAS,
)
