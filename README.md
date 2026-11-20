# Destinos da Banda — Plataforma Turística Angolana

## Fase 1 — Fundação

---

## Instalação Rápida

### Pré-requisitos
- Python 3.11 ou superior
- PostgreSQL instalado e a correr
- Git

---

## Passo a passo

### 1. Criar e activar o ambiente virtual

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

---

### 2. Instalar dependências

**Método recomendado (funciona em todos os sistemas):**
```bash
pip install -r requirements/dev.txt --only-binary=:all:
```

> A flag `--only-binary=:all:` força o pip a usar wheels pré-compilados,
> evitando erros de compilação no Windows (como o erro `pg_config not found`).

**Se o erro persistir com psycopg2, instalar separadamente:**
```bash
pip install psycopg2-binary --only-binary=:all:
pip install -r requirements/dev.txt --ignore-installed psycopg2-binary
```

---

### 3. Configurar variáveis de ambiente

```bash
# Copiar o ficheiro de exemplo
copy .env.example .env        # Windows
cp .env.example .env          # macOS/Linux

# Editar o .env com os teus dados
```

Conteúdo do `.env`:
```
ENVIRONMENT=development
SECRET_KEY=gerar-uma-chave-unica-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=destinos_banda_db
DB_USER=postgres
DB_PASSWORD=a-tua-password
DB_HOST=localhost
DB_PORT=5432
```

**Gerar uma SECRET_KEY segura:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

### 4. Criar a base de dados PostgreSQL

```sql
-- Abrir o psql ou pgAdmin e executar:
CREATE DATABASE destinos_banda_db;
CREATE USER destinos_user WITH PASSWORD 'a-tua-password';
GRANT ALL PRIVILEGES ON DATABASE destinos_banda_db TO destinos_user;
```

---

### 5. Executar migrações e arrancar

```bash
python manage.py migrate
python manage.py runserver
```

Abrir no browser: **http://localhost:8000**

---

## Resolução de Problemas Comuns

### Erro: `pg_config executable not found`
O psycopg2 está a tentar compilar do código fonte. Solução:
```bash
pip install psycopg2-binary --only-binary=:all:
```

### Erro: `ModuleNotFoundError: No module named 'decouple'`
O ambiente virtual não está activado ou as dependências não foram instaladas:
```bash
venv\Scripts\activate   # Windows
pip install -r requirements/dev.txt --only-binary=:all:
```

### Erro: `FATAL: password authentication failed`
As credenciais no `.env` não correspondem ao utilizador PostgreSQL.
Verificar com: `psql -U postgres -d destinos_banda_db`

---

## Estrutura do Projecto

```
destinos_banda/
├── config/                 # Configuração Django
│   ├── settings/
│   │   ├── base.py         # Configurações comuns
│   │   ├── development.py  # Desenvolvimento local
│   │   └── production.py   # Produção (servidor)
│   ├── urls.py
│   └── wsgi.py
├── apps/                   # Apps Django
│   └── core/               # App principal (Fase 1)
├── templates/              # Templates HTML
│   ├── base.html           # Template base
│   ├── components/         # Navbar, Footer
│   ├── core/               # Templates da app core
│   └── errors/             # Páginas de erro
├── static/                 # CSS, JS, imagens
├── media/                  # Uploads dos utilizadores
├── requirements/           # Dependências por ambiente
├── .env.example            # Exemplo de variáveis de ambiente
└── manage.py
```
