# Container de desenvolvimento

O container de desenvolvimento se chama **`logistica-dev`** e contém Node.js e o código do projeto, incluindo o repositório local do Spec Kit. Os serviços da aplicação (FastAPI e PostgreSQL) serão adicionados no Compose principal.

## Criar e iniciar

```powershell
docker compose -f compose.dev.yml up -d --build
```

## Abrir um terminal dentro do container

```powershell
docker exec -it logistica-dev bash
```

## Comandos úteis dentro do container

```bash
node --version
```

## Parar o container

```powershell
docker compose -f compose.dev.yml down
```

O código local é montado em `/workspace`; qualquer alteração feita no container aparece no projeto local e vice-versa.
