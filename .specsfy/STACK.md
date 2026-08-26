# Stack do sistema

## Inventário detectado

<!-- specsfy:stack:start -->
| Camada | Tecnologia | Evidência |
| --- | --- | --- |
| Infraestrutura | Containers | arquivo Compose |
<!-- specsfy:stack:end -->

## Stack confirmada pelo projeto

| Camada | Tecnologia | Responsabilidade | Evidência |
| --- | --- | --- | --- |
| Frontend | Next.js 16.3.1, React 19.2.4 e TypeScript 5.9.2 | Aplicação web responsiva e exportação estática para o Netlify | `frontend/package.json` e `frontend/next.config.ts` |
| Estilos | Tailwind CSS 4.3.3 | Design responsivo da interface LogiSync | `frontend/package.json` |
| API | FastAPI 0.116.1 e Uvicorn 0.35.0 sobre Python 3.12 | Regras de domínio e contratos HTTP | `backend/requirements.txt` e `backend/Dockerfile` |
| Persistência | PostgreSQL 18, SQLAlchemy 2.0.43 e Alembic 1.16.5 | Fonte de verdade e migrations versionadas | `docker-compose.yml` e `backend/requirements.txt` |
| Automação e BI | n8n 1.116.2 e Metabase 0.58.7 | Integrações via API/webhook; BI administrativo local com bind em loopback | `docker-compose.yml` e `docs/runbook.md` |
| Harness | Specsfy CLI 0.7.0 | Painel TUI, acompanhamento de specs e skills | `.vscode/tasks.json` e CLI instalado |

### Estratégia de imagens do frontend

`frontend/next.config.ts` mantém a otimização padrão no build Docker `standalone` e usa imagens sem otimização dinâmica somente quando `NETLIFY_STATIC_EXPORT=true`. Assim, o Netlify publica `/logisync-logo.png` diretamente, sem depender da rota de servidor `/_next/image`.
