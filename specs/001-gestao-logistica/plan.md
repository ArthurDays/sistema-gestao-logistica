# Plano Técnico e de Implantação: Gestão Logística

**Feature**: `001-gestao-logistica`  
**Especificação**: [spec.md](./spec.md)  
**Status**: Em implementação

## Resumo da solução

O produto será um monólito modular: um frontend web em Next.js/React comunica-se com uma API FastAPI. A API é a única responsável pelas regras de negócio e grava dados no PostgreSQL. O n8n consome eventos por webhook e usa endpoints autenticados da API para importações. Metabase acessa somente views de leitura no PostgreSQL.

## Stack

| Área | Decisão |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript; Tailwind CSS e shadcn/ui entram quando a biblioteca de componentes for necessária |
| Formulários e dados | React Hook Form, Zod, TanStack Query |
| Gráficos | Recharts |
| API | Python 3.12, FastAPI, Pydantic v2 |
| Persistência | PostgreSQL 18, SQLAlchemy 2.x, Alembic |
| Automação | n8n por API e webhooks |
| BI | Metabase conectado a views read-only |
| Infra | Docker Compose e Traefik |
| Qualidade | pytest, httpx, Ruff, mypy |
| Evolução de escala | Redis + ARQ para fila, cache e retentativas |
| Harness de engenharia | Spec Kit, workflow local, gates humanos e instruções em `AGENTS.md` |

## Decisões arquiteturais

1. **PostgreSQL é a fonte de verdade**: DBeaver é usado somente para inspeção e administração; migrations Alembic alteram o schema.
2. **Sem acesso direto do n8n às tabelas de domínio**: integrações entram pela API com credencial de serviço e chave de idempotência.
3. **Outbox transacional**: toda alteração que deve gerar notificação cria um `outbox_event` na mesma transação; um worker entrega os webhooks com retentativa.
4. **Cálculo determinístico**: valores financeiros usam `NUMERIC` no banco e `Decimal` na aplicação. Cálculos são serviços de domínio testados.
5. **Particionamento somente por necessidade comprovada**: tabelas de operação e eventos poderão ser particionadas por mês quando volume e consultas justificarem.

## Estrutura de repositório

```text
frontend/
  app/
  components/
  features/
  lib/
backend/
  app/
    api/
    core/
    domain/
    integrations/
    models/
    repositories/
    schemas/
    services/
    workers/
  alembic/
  tests/
n8n/workflows/
infra/traefik/
specs/001-gestao-logistica/
docker-compose.yml
.env.example
```

## Contratos principais da API

```text
POST   /api/v1/auth/token
GET    /api/v1/vehicles
POST   /api/v1/vehicles
POST   /api/v1/vehicles/{id}/operations
GET    /api/v1/vehicles/{id}/profitability?from=&to=
POST   /api/v1/expenses
POST   /api/v1/revenues
POST   /api/v1/maintenance-rules
POST   /api/v1/maintenance-executions
GET    /api/v1/maintenance-alerts
POST   /api/v1/integrations/vehicle-data
POST   /api/v1/integrations/fuel-prices
```

As rotas de integração exigem `Idempotency-Key`, registram a origem e retornam o identificador do recurso gravado. Os endpoints de saída do n8n recebem assinatura HMAC.

## Implantação com Docker Compose

### Serviços iniciais

```text
traefik       Proxy reverso, TLS e roteamento
frontend      Next.js
api           FastAPI/Uvicorn
postgres      Banco de dados persistente
n8n           Workflows e webhooks
metabase      BI administrativo
```

### Redes

- `public`: somente Traefik, frontend e serviços com rotas externas.
- `internal`: API, PostgreSQL, n8n e Metabase.
- PostgreSQL não expõe porta publicamente em produção.

### Persistência e backup

- Volumes nomeados para PostgreSQL, n8n e Metabase.
- Backup diário lógico do PostgreSQL com `pg_dump`, criptografado e enviado a armazenamento externo.
- Teste mensal de restauração em ambiente isolado.
- Variáveis sensíveis fora do Git, providas por `.env` no ambiente ou gerenciador de segredos.

### Ambientes

| Ambiente | Finalidade | Regra |
|---|---|---|
| Local | desenvolvimento | Docker Compose, dados fictícios |
| Homologação | validação | imagem igual à produção e banco separado |
| Produção | operação | HTTPS, backups e logs centralizados |

## Ordem de entrega

1. Base Docker Compose, PostgreSQL, FastAPI, Next.js e health checks.
2. Alembic, autenticação, organizações e controle de acesso.
3. Veículos, registros operacionais, receitas e despesas.
4. Serviço de cálculo de rentabilidade e testes de domínio.
5. Regras, execução e alertas de manutenção.
6. Outbox, webhooks e workflows n8n.
7. Dashboard React e views read-only para Metabase.
8. Redis/ARQ, Sentry, métricas e otimização baseada em uso real.
9. Instalar e executar o workflow local do Spec Kit para padronizar novas funcionalidades e correções.

## Progresso

- **2026-08-17 — Incremento 1 concluído**: PostgreSQL 18, migration inicial, FastAPI, Next.js, cadastro de veículo e fechamento diário com idempotência, validação de hodômetro e interface responsiva.
- **Validações do incremento 1**: pytest, Ruff, mypy, build do Next.js, auditoria npm sem vulnerabilidades e smoke test real contra PostgreSQL.
- **2026-08-17 — Incremento 2 concluído**: despesas categorizadas, migration financeira, endpoint de rentabilidade por período e resumo financeiro na interface.
- **Validações do incremento 2**: três testes aprovados, Ruff e mypy aprovados, build Next.js aprovado e smoke test com resultado líquido de R$ 230,00 sobre a operação demonstrativa.
- **2026-08-17 — Interface e documentação reorganizadas**: dashboard executivo e páginas independentes de catálogo, financeiro e frota; documentação arquitetural, modelo de dados, fluxos Mermaid, guia de contribuição e CI adicionados para publicação inicial.

## Critérios de aceite de implantação

- `docker compose up -d` inicia todos os serviços e health checks ficam saudáveis.
- A API aplica migrations antes de aceitar tráfego.
- Frontend acessa a API somente pelo endereço configurado.
- n8n recebe um webhook de alerta de teste sem acesso direto ao banco de domínio.
- Metabase consulta apenas usuário PostgreSQL de leitura e views autorizadas.
- Rotina de backup é executada e uma restauração é validada.
