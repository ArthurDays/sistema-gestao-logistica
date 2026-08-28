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
| LoginForm | Entrar, criar organização, iniciar OAuth Google e orquestrar os modos de recuperação no mesmo cartão público. | `frontend/components/operations-dashboard.tsx` | Usuários sem sessão e pessoas que abriram link de recuperação |
| Solicitação de recuperação | Coletar e-mail, enviar por Enter ou `Enviar link` e apresentar sempre a confirmação neutra da API. | modo `reset-request` de `LoginForm`; `POST /api/v1/auth/password-reset/request` | Pessoas que selecionam `Esqueci minha senha` |
| Redefinição de senha | Capturar e remover `reset_token` da URL, validar duas senhas e retornar ao login após o 204. | modo `reset-confirm` de `LoginForm`; `POST /api/v1/auth/password-reset/confirm` | Pessoas que abrem o link único enviado por e-mail |
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
- Recuperação: o cartão mantém largura fluida até 360 px, foco inicial no
  primeiro campo útil, envio por teclado, ações com altura mínima de 44 px e
  retorno explícito ao login.
- Privacidade: conta conhecida, desconhecida, limitada ou transporte SMTP
  indisponível produzem a mesma confirmação visual. O token nunca é
  renderizado; ele é removido da URL assim que capturado e limpo do estado ao
  concluir ou cancelar.
- Erros: validação local de confirmação evita envio divergente; token inválido,
  expirado ou reutilizado recebe a mensagem genérica da API com `role="alert"`.

## Verificação normativa

Os contratos AC-016 a AC-018 são caracterizados em
`backend/tests/acceptance/test_mvp_acceptance.py`; lint e TypeScript são gates
obrigatórios do frontend. A recuperação é rastreada por AC-001 a AC-004 em
`backend/tests/test_password_reset.py` e pelos gates `npm run lint`,
`npm run test` e `npm run build`.
