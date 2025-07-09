# Projeto Estacionamento - Backend

Este repositório contém o código da API em FastAPI para o sistema de gerenciamento de estacionamentos do projeto de TPPE. A API é responsável por toda a lógica de negócio, comunicação com o banco de dados e exposição dos endpoints para o frontend.

## Stack de Tecnologias

- **Linguagem:** Python 3.11+
- **Framework:** FastAPI
- **Banco de Dados:** PostgreSQL
- **ORM:** SQLAlchemy
- **Validação de Dados:** Pydantic
- **Servidor ASGI:** Uvicorn
- **Containerização:** Docker

## 🚀 Como Executar (Ambiente Completo com Docker)

A maneira recomendada de executar este serviço é através do repositório orquestrador, que utiliza `docker-compose` para iniciar o backend, frontend e o banco de dados de forma integrada.

Por favor, consulte as instruções no `README.md` do repositório geral para um setup completo com um único comando.

Caso queira rodar o deploy use o link

[TPPE Backend](https://tppe-estacionamento.up.railway.app)

## 🔧 Desenvolvimento Local (Isolado)

Se você precisa rodar e testar o backend de forma isolada, siga os passos abaixo.

### Pré-requisitos

- Python 3.11+
- Uma instância do PostgreSQL rodando e acessível

### 1. Clone o Repositório

```bash
git clone <URL_DO_SEU_REPO_BACKEND>
cd TPPE_Estacionamento
```

### 2. Crie e Ative um Ambiente Virtual

É uma boa prática isolar as dependências do projeto.

```bash
# Crie o ambiente virtual
python -m venv .venv

# Ative o ambiente (Linux/macOS)
source .venv/bin/activate

# Ative o ambiente (Windows)
# .venv\Scripts\activate
```

### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto e adicione a URL de conexão do seu banco de dados local.

**.env**

```env
DATABASE_URL=postgresql://seu_usuario:sua_senha@localhost:5432/seu_banco
```

### 5. Inicie o Servidor

```bash
uvicorn src.main:app --reload
```

A API estará disponível em `http://localhost:8000`.

## ✅ Testes

Para executar a suíte de testes automatizados, certifique-se de que seu ambiente virtual esteja ativo e rode o seguinte comando:

```bash
pytest
```

## 📄 Documentação da API

Com o servidor rodando, a documentação interativa da API (gerada automaticamente pelo FastAPI) está disponível em:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
