# Controle de Treinamentos

Sistema web interno para controlar treinamentos de funcionários: NRs e treinamentos
corporativos, certificados em PDF, validade automática, alertas de vencimento e
relatórios exportáveis para Excel.

A **mesma aplicação roda local e online** — a migração é trocar a `DATABASE_URL`
e subir o servidor em um host acessível.

## Funcionalidades

- **Funcionários**: cadastro com setor, cargo, matrícula, CPF e datas de admissão/demissão.
- **Treinamentos**: NRs e corporativos, com norma, carga horária e validade (meses).
- **Registros (matrículas)**: vínculo funcionário × treinamento com data de realização,
  instrutor, aprovação, observações e **certificado em PDF** (upload/download/remover).
- **Validade automática**: cada registro calcula a data de vencimento a partir da validade
  do treinamento. Situações: **Válido**, **A vencer** (default: 60 dias antes), **Vencido**.
- **Dashboard**: contadores, listas de "A vencer" e "Vencidos".
- **Relatórios**: por funcionário, por treinamento e filtros de vencimento, com
  **exportação CSV** (compatível com Excel).
- **Perfis de acesso**: `admin`, `rh`, `gestor` e `colaborador`.

| Perfil        | Painel | Cadastros | Relatórios | Usuários |
|---------------|--------|-----------|------------|----------|
| `admin`       | Sim    | Sim       | Sim        | Sim      |
| `rh`          | Sim    | Sim       | Sim        | Não      |
| `gestor`      | Sim    | Visualização | Sim     | Não      |
| `colaborador` | Só o próprio | Não   | Não        | Não      |

## Estrutura

```
backend/
  alembic/                # migrações (produção / PostgreSQL)
  app/
    main.py               # app FastAPI + bootstrap (admin inicial)
    config.py             # configuração via .env
    database.py           # SQLAlchemy engine
    models/               # ORM
    routers/              # auth, dashboard, funcionarios, treinamentos, matriculas, relatorios, usuarios
    services.py           # cálculo de validade, situações, certificados
    static/               # CSS
    templates/            # Jinja2
  run.py                  # inicializador
  alembic.ini
  requirements.txt
data/                     # SQLite local + uploads (não versionar)
.env.example              # modelo de configuração
```

## Requisitos

- Python 3.11+ (testado com 3.13)

## Execução local (desenvolvimento)

```bash
# 1) ambiente virtual
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 2) dependências
pip install -r backend/requirements.txt

# 3) configuração
copy .env.example .env          # Windows
cp .env.example .env            # Linux/macOS

# 4) subir
python backend/run.py           # http://127.0.0.1:8000
```

Na primeira execução o banco SQLite é criado em `data/app.db` e o usuário
administrador inicial é gerado (padrão: `admin` / `admin123` — **troque a senha
no `.env` antes de publicar**).

Login padrão: `admin` / `admin123` (configure em `.env`).

## Acessar da rede local (LAN)

```bash
python backend/run.py --host 0.0.0.0 --port 8000
```

Acesse de outra máquina da rede via `http://IP_DESTA_MAQUINA:8000`. Use `--reload`
apenas em desenvolvimento (recarrega a cada alteração de código).

## Publicar online (PostgreSQL)

A mudança é configurar o banco e rodar as migrações. O código não muda.

1. **Crie o banco** PostgreSQL (ex.: na nuvem — Neon, Supabase, Render, Fly.io, Railway...).
2. **Configure o `.env`** com a URL do banco:

   ```
   DATABASE_URL=postgresql+psycopg://usuario:senha@host:5432/nome_do_banco
   SECRET_KEY=<gere um valor longo e aleatório>
   ADMIN_PASSWORD=<senha forte do admin>
   ```

   Gere a chave com: `python -c "import secrets; print(secrets.token_hex(32))"`

3. **Rode as migrações** (a partir de `backend/`):

   ```bash
   python -m alembic upgrade head
   ```

   > Em um banco já criado pelo modo local (SQLite → existe `alembic_version`), não
   > é preciso fazer nada. Para um banco que já tenha as tabelas criadas manualmente,
   > use `python -m alembic stamp head` para marcar a versão sem recriar.

4. **Suba o app** em um host com acesso público (Fly.io, Render, Railway, um VPS com
   Nginx + uvicorn, etc.):

   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

   O admin inicial será criado na primeira execução (se não existir).

## Migrações (Alembic)

As migrações são geradas a partir dos models:

```bash
# após alterar um model
python -m alembic revision --autogenerate -m "descricao"
python -m alembic upgrade head
```

Sempre teste `upgrade` e `downgrade` em um banco de desenvolvimento antes de aplicar
em produção.

## Backup

- **Local**: copie a pasta `data/` (contém o banco `app.db` e os certificados em `data/uploads/`).
- **Online**: exporte o PostgreSQL (`pg_dump`) e preserve o bucket/volume de uploads.

Para restauração em outra máquina, basta copiar `data/` de volta (e ajustar o `.env`).

## Segurança

- Senhas armazenadas com **bcrypt**.
- Login via **JWT** em cookie `HttpOnly` (SameSite=Lax).
- `.env` nunca é versionado (veja `.gitignore`).
- Troque `SECRET_KEY` e a senha `ADMIN_PASSWORD` antes de publicar.
- Para ambientes muitos expostos, coloque o app atrás de HTTPS (Caddy/Nginx/Cloudflare).

## Customização

- **Alerta de vencimento**: `ALERTA_DIAS` no `.env` (dias antes de entrar em "A vencer").
- **Validade de login**: `ACCESS_TOKEN_EXPIRE_HOURS`.
- **Aparência**: edite `backend/app/static/css/app.css` e os templates em `backend/app/templates/`.
