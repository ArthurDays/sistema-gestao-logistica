# Aplicação e implementações

<!-- specsfy:documentator:start -->
## Superfícies

Categorias: Serviços, Rotas e APIs, Páginas, Componentes, Testes e Outras fontes.

Relação: relaciona cada arquivo observado à sua superfície.

| Categoria | Arquivo | Símbolos |
| --- | --- | --- |
| Páginas | frontend/app/catalogo/page.tsx | CatalogPage |
| Páginas | frontend/app/financeiro/page.tsx | FinancePage |
| Páginas | frontend/app/frota/page.tsx | FleetPage |
| Páginas | frontend/app/globals.css | — |
| Páginas | frontend/app/layout.tsx | RootLayout |
| Páginas | frontend/app/manifest.ts | manifest |
| Páginas | frontend/app/page.tsx | Home |
| Componentes | frontend/components/operations-dashboard.tsx | API_URL, apiFetch, KpiIcon, OperationsDashboard, synchronizeCatalog, openClosing, openVehicleDetails, openMaintenance |
| Outras fontes | frontend/next-env.d.ts | — |
| Outras fontes | frontend/next.config.ts | — |
<!-- specsfy:documentator:end -->

## Superfícies confirmadas no código-fonte

| Camada | Responsabilidade | Evidência |
| --- | --- | --- |
| Web | shell responsivo e páginas de visão geral, catálogo, financeiro e frota | `frontend/app/`, `frontend/components/operations-dashboard.tsx` |
| Autenticação | senha, cadastro, OAuth correlacionado e troca de código de uso único | `backend/app/api.py`, `backend/app/auth.py` |
| Domínio | frota, operação, finanças, catálogo e manutenção tenant-aware | `backend/app/api.py`, `backend/app/models.py` |
| Integrações | catálogo CSV somente leitura e outbox/webhooks assinados | `backend/app/catalog.py`, `backend/app/outbox_worker.py` |

O login limita cinco falhas por identidade e origem em 15 minutos. OAuth exige
cookie HttpOnly correlacionado; o frontend remove `auth_code` da URL antes de
trocá-lo por JWT e nenhum JWT é transportado em query string.
