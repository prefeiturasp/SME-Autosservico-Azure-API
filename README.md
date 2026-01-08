# SME-Autosservico-Azure-API

API FastAPI para extração de backlog do Azure DevOps.

## Requisitos
- Docker e Docker Compose v2 instalados.

## Configuração de ambiente
1. Copie o arquivo `.env.example` para `.env`.
2. Preencha pelo menos `AZURE_DEVOPS_PAT` e, se desejar, `AZURE_DEVOPS_ORGANIZATION`, `AZURE_DEVOPS_PROJECT` e `API_PORT`.
3. O container já força `API_HOST=0.0.0.0` para exposição externa.

## Executando com Docker

### Desenvolvimento (Dockerfile padrão + Compose)
Build e run direto:
```bash
docker build -t azure-backlog-api .
docker run --env-file .env -p 8000:8000 azure-backlog-api
```
Altere o mapeamento de porta (`host:container`) se definir um `API_PORT` diferente.

Usando Docker Compose:
```bash
docker compose up --build -d
```
O Compose lê o arquivo `.env` para carregar as variáveis e usa `API_PORT` (padrão 8000) para mapear a porta do host.

### Produção (Gunicorn + workers Uvicorn)
Build da imagem otimizada:
```bash
docker build -f Dockerfile.prod -t azure-backlog-api:prod .
docker run --env-file .env -e WORKERS=4 -p 8000:8000 azure-backlog-api:prod
```
Recomendações:
- Ajuste `WORKERS` conforme CPU disponível (ex.: 2–4 em instâncias pequenas).
- Defina `API_PORT` se precisar expor porta diferente no container.
- Em produção configure `CORS_ORIGINS` explicitamente (evite `*`).

Usando Docker Compose (produção):
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```
O arquivo `docker-compose.prod.yml` aponta para o `Dockerfile.prod` (Gunicorn).

## URLs úteis
- API: `http://localhost:8000/`
- Documentação Swagger: `http://localhost:8000/docs`
