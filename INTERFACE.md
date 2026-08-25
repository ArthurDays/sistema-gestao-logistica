# Interface do sistema

## Contexto detectado

Stack observada em `frontend/package.json`: Next.js 16.3.1, React 19.2.4,
TypeScript 5.9.2 e Tailwind CSS 4.3.3. A interface usa componentes próprios;
nenhuma biblioteca externa de primitives foi identificada.

## Fontes canônicas

- `frontend/app/`: páginas e rotas do App Router.
- `frontend/components/`: componentes React reutilizáveis.
- `frontend/app/globals.css`: tokens e estilos globais.

## Inventário

| Bloco | Responsabilidade | Fonte | Consumidores |
| --- | --- | --- | --- |
| RootLayout | Metadados, viewport móvel, idioma e CSS global. | `frontend/app/layout.tsx` | Todas as rotas |
| App Router | Selecionar a visão `overview`, `fleet`, `catalog` ou `finances`. | `frontend/app/page.tsx`, `frontend/app/frota/page.tsx`, `frontend/app/catalogo/page.tsx`, `frontend/app/financeiro/page.tsx` | OperationsDashboard |
| OperationsDashboard | Orquestrar autenticação, consultas, indicadores, catálogo, frota, financeiro, alertas e painéis de ação. | `frontend/components/operations-dashboard.tsx` | Todas as rotas funcionais |
| LoginForm | Entrar, criar organização e iniciar OAuth Google com erros perceptíveis. | `frontend/components/operations-dashboard.tsx` | Usuários sem sessão |
| DashboardSidebar | Navegação desktop recolhível e navegação móvel inferior fixa. | `frontend/components/operations-dashboard.tsx` | Usuários autenticados |
| Painel lateral | Fechamento diário, manutenção, cadastro e detalhe do veículo. | `frontend/components/operations-dashboard.tsx` | Operação de frota |
| Estilos globais | Largura mínima, bloqueio de overflow horizontal, safe area e campos móveis. | `frontend/app/globals.css` | Toda a interface |

## Contratos observados

- Mobile: viewport a partir de 320 px, `overflow-x: hidden`, navegação inferior
  com alvos de no mínimo 56 px e safe area.
- Desktop: sidebar expansível, conteúdo com padding adaptativo, cartões, filtros,
  tabelas e ações preservados nas quatro visões.
- Acessibilidade: labels associados por composição, `aria-label`, `aria-current`,
  mensagens de erro com `role="alert"`, foco visível e controles com altura mínima.
- Estados: loading, vazio, erro, sucesso, sincronização e sessão/papel são
  representados no componente compartilhado.

## Verificação normativa

Os contratos AC-016 a AC-018 são caracterizados em
`backend/tests/acceptance/test_mvp_acceptance.py`; lint e TypeScript são gates
obrigatórios do frontend.
