import enum


class CategoriaTreinamento(str, enum.Enum):
    NR = "NR"
    CORPORATIVO = "CORPORATIVO"


class Role(str, enum.Enum):
    ADMIN = "admin"
    RH = "rh"
    GESTOR = "gestor"
    COLABORADOR = "colaborador"
    VISUALIZADOR = "visualizador"


ROLE_LABELS = {
    Role.ADMIN: "Administrador",
    Role.RH: "Recursos Humanos",
    Role.GESTOR: "Gestor",
    Role.COLABORADOR: "Colaborador",
    Role.VISUALIZADOR: "Visualizador",
}


class Pagina(str, enum.Enum):
    """Páginas do menu lateral que podem ser liberadas por usuário."""

    PAINEL = "painel"
    FUNCIONARIOS = "funcionarios"
    TREINAMENTOS = "treinamentos"
    MATRICULAS = "matriculas"
    RELATORIOS = "relatorios"
    SETORES = "setores"
    CARGOS = "cargos"
    GESTORES = "gestores"
    CATEGORIAS = "categorias"
    KPIS = "kpis"
    USUARIOS = "usuarios"
    INATIVOS = "inativos"


PAGINA_LABELS = {
    Pagina.PAINEL: "Painel",
    Pagina.FUNCIONARIOS: "Funcionários",
    Pagina.TREINAMENTOS: "Treinamentos",
    Pagina.MATRICULAS: "Registros",
    Pagina.RELATORIOS: "Relatórios",
    Pagina.SETORES: "Setor",
    Pagina.CARGOS: "Cargo",
    Pagina.GESTORES: "Gestor",
    Pagina.CATEGORIAS: "Categoria",
    Pagina.KPIS: "KPIs",
    Pagina.USUARIOS: "Usuários",
    Pagina.INATIVOS: "Inativos",
}

# Somente administradores podem acessar a gestão de usuários,
# independentemente das permissões por página.
PAGINA_SOMENTE_ADMIN = {Pagina.USUARIOS}

MENU_LATERAL: list[dict] = [
    {"pagina": Pagina.PAINEL, "url": "/", "prefixo": "/", "exato": True},
    {
        "pagina": Pagina.FUNCIONARIOS,
        "url": "/funcionarios",
        "prefixo": "/funcionarios",
        "excecao": "/funcionarios/inativos",
    },
    {"pagina": Pagina.TREINAMENTOS, "url": "/treinamentos", "prefixo": "/treinamentos"},
    {"pagina": Pagina.MATRICULAS, "url": "/matriculas", "prefixo": "/matriculas"},
    {"pagina": Pagina.RELATORIOS, "url": "/relatorios", "prefixo": "/relatorios"},
    {"pagina": Pagina.SETORES, "url": "/setores", "prefixo": "/setores"},
    {"pagina": Pagina.CARGOS, "url": "/cargos", "prefixo": "/cargos"},
    {"pagina": Pagina.GESTORES, "url": "/gestores", "prefixo": "/gestores"},
    {"pagina": Pagina.CATEGORIAS, "url": "/categorias", "prefixo": "/categorias"},
    {"pagina": Pagina.KPIS, "url": "/kpis", "prefixo": "/kpis"},
    {"pagina": Pagina.USUARIOS, "url": "/usuarios", "prefixo": "/usuarios"},
    {
        "pagina": Pagina.INATIVOS,
        "url": "/funcionarios/inativos",
        "prefixo": "/funcionarios/inativos",
    },
]

# Permissões iniciais ao cadastrar um usuário (e migração de usuários antigos),
# espelhando a visibilidade atual de cada perfil no menu.
PERMISSOES_PADRAO: dict[Role, list[Pagina]] = {
    Role.ADMIN: list(PAGINA_LABELS),
    Role.RH: [
        Pagina.PAINEL,
        Pagina.FUNCIONARIOS,
        Pagina.TREINAMENTOS,
        Pagina.MATRICULAS,
        Pagina.RELATORIOS,
        Pagina.SETORES,
        Pagina.CARGOS,
        Pagina.GESTORES,
        Pagina.CATEGORIAS,
        Pagina.KPIS,
        Pagina.INATIVOS,
    ],
    Role.GESTOR: [
        Pagina.PAINEL,
        Pagina.RELATORIOS,
        Pagina.SETORES,
        Pagina.CARGOS,
        Pagina.GESTORES,
        Pagina.CATEGORIAS,
        Pagina.KPIS,
    ],
    Role.COLABORADOR: [Pagina.PAINEL],
    Role.VISUALIZADOR: [Pagina.MATRICULAS],
}
