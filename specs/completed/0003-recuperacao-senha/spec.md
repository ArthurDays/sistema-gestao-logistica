# Especificação integrada: Recuperação e redefinição segura de senha

| Campo | Valor |
| --- | --- |
| Formato | Specsfy/2.0 |
| ID | SPEC-0003 |
| Slug | 0003-recuperacao-senha |
| Status | Complete |
| Effort | 7 |
| Effort updated at | 2026-08-26 |
| Effort rationale | Fluxo sensível de autenticação com migration, token efêmero, limitação de abuso, transporte de e-mail, interface pública e validação de segurança. |
| ClickUp Task | Não vinculada |
| Milestones | Produção segura |
| Definition Gate | Passed |
| Plan Gate | Passed |
| Delivery Gate | Passed |
| Evidence Contract | 1 |
| Interface para pessoas | Sim — ampliação do formulário público de autenticação |
| Atualizada em | 2026-08-27 |

## Ato I — Definir

### 1. Problema e resultado

#### Problema

Usuários cadastrados com e-mail e senha perdem o acesso quando esquecem a credencial e atualmente dependem de intervenção administrativa ou do Google OAuth.

#### Resultado desejado

A pessoa solicita um link seguro sem expor se a conta existe, define uma nova senha em até 30 minutos e volta a entrar sem suporte manual.

#### Métricas de sucesso

- Uma conta ativa conclui o fluxo com um único link válido e entra com a nova senha.
- Nenhuma resposta pública distingue e-mail existente, inexistente ou inativo.
- Token expirado, reutilizado ou concorrente nunca altera a senha.
- A suíte automatizada cobre solicitação, enumeração, expiração, consumo único, limite de abuso e interface.

### 2. Research e esclarecimentos

#### Researchs executados

- Nenhuma pesquisa externa foi necessária; os padrões internos de OAuth opaco, hash-only e throttle da SPEC-0002 são precedentes suficientes.

#### Fontes e contexto consultados

- `specs/inbox/2026-08-26-173953-recuperacao-e-redefinicao-segura-de-senha.md` e `specs/backlog/0001-recuperacao-senha.md`.
- `specs/completed/0001-gestao-logistica/spec.md` e `specs/completed/0002-operacao-producao-gerenciada/spec.md`.
- `backend/app/api.py`, `backend/app/auth.py`, `backend/app/core/security.py`, `backend/app/models.py` e migrations existentes.
- `frontend/components/operations-dashboard.tsx`, `INTERFACE.md` e `DESIGNSYSTEM.MD`.

#### Documentação consultada

- `.specsfy/Spec.md`, `.specsfy/STACK.md`, `.specsfy/RULES.md`, `.specsfy/DATABASE.md` e documentação técnica local em `docs/`.

#### Artefatos de pesquisa armazenados

- `specs/completed/0003-recuperacao-senha/research/local-implementation-evidence.md` — índice das fontes e provas locais; nenhuma documentação externa foi consultada.

#### Dúvidas respondidas

- **Q**: O sistema precisa depender de um provedor comercial específico? → **A**: Não; o contrato será SMTP/TLS configurável por ambiente.
- **Q**: A resposta pode revelar que uma conta existe? → **A**: Não; solicitação sempre retorna resposta neutra.
- **Q**: O token pode ser persistido em texto claro? → **A**: Não; somente SHA-256, seguindo o precedente do OAuth.

#### Dúvidas abertas

- Nenhuma lacuna de produto. Credenciais e remetente SMTP são configuração operacional protegida antes do deploy.

### 3. Escopo e atores

#### Incluído

- Solicitação pública de recuperação com resposta neutra.
- Token aleatório, hash-only, expirável, de uso único e protegido contra concorrência.
- Transporte SMTP/TLS configurável e sanitizado.
- Tela de solicitação e tela de definição da nova senha no shell visual atual.
- Limitação por identidade e origem, migration, testes e documentação operacional.

#### Fora de escopo

- Troca de e-mail, autenticação multifator, recuperação por telefone e alteração administrativa de senha.
- Revogação global dos JWT já emitidos; os tokens de acesso atuais expiram conforme a configuração vigente.
- Escolha ou contratação de fornecedor de e-mail, domínio personalizado e gestão de reputação do remetente.

#### Atores

- **Usuário sem sessão**: solicita recuperação e informa uma nova senha com o token recebido.
- **API LogiSync**: protege identidade, token, regras temporais e alteração da senha.
- **Servidor SMTP**: entrega o link ao e-mail cadastrado sem conhecer regras de domínio.
- **Operador técnico**: configura host, porta, credenciais e remetente como segredos do ambiente.

### 4. Princípios e restrições do projeto

- **PR-001**: Respostas e tempo de processamento não devem facilitar enumeração de contas.
- **PR-002**: Tokens e credenciais nunca entram em logs, respostas de solicitação ou banco em texto claro.
- **PR-003**: Toda mudança de schema usa migration Alembic e teste.
- **PR-004**: A nova senha deve ter de 12 a 128 caracteres e ser diferente da atual.
- **PR-005**: O transporte de e-mail é uma fronteira injetável e falhas externas não expõem detalhes ao solicitante.
- **PR-006**: A interface preserva o design LogiSync, alvos de 44 px, foco visível e funcionamento a partir de 360 px.

### 5. Histórias de usuário

#### US-001 — Recuperar o acesso por e-mail (P1)

Como usuário cadastrado por senha, quero receber um link temporário e criar uma nova senha, para recuperar meu acesso sem suporte manual.

**Por que P1**: o cadastro público não é operacionalmente sustentável sem recuperação de credencial.
**Teste independente**: solicitar recuperação, capturar o envio simulado, redefinir a senha, rejeitar reuso e autenticar somente com a nova senha.
**Requisitos**: FR-001, FR-002, FR-003, FR-004

### 6. Cenários BDD de aceite

#### AC-001 — Solicitação neutra e envio válido

**Cobre**: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004

```gherkin
@US-001 @FR-001 @FR-002 @FR-003 @FR-004 @NFR-001 @NFR-002 @NFR-003 @NFR-004 @AC-001
Feature: Recuperação segura de senha

  Scenario: solicitar recuperação de uma conta ativa
    Given uma conta ativa cadastrada com e-mail e senha
    When a pessoa solicita recuperação pelo e-mail
    Then recebe resposta neutra e um único link HTTPS temporário é enviado
```

#### AC-002 — Conta não revelada e abuso limitado

**Cobre**: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004

```gherkin
@US-001 @FR-001 @FR-002 @FR-003 @FR-004 @NFR-001 @NFR-002 @NFR-003 @NFR-004 @AC-002
Feature: Recuperação segura de senha

  Scenario: solicitar com e-mail desconhecido ou em excesso
    Given um e-mail desconhecido ou três solicitações na mesma janela
    When uma nova solicitação é enviada
    Then a resposta não revela a conta e nenhum token utilizável adicional é criado
```

#### AC-003 — Redefinição única e autenticação posterior

**Cobre**: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004

```gherkin
@US-001 @FR-001 @FR-002 @FR-003 @FR-004 @NFR-001 @NFR-002 @NFR-003 @NFR-004 @AC-003
Feature: Recuperação segura de senha

  Scenario: usar um token válido uma única vez
    Given um token válido e uma nova senha diferente da atual
    When a pessoa confirma a redefinição
    Then a senha muda, tokens pendentes são invalidados e somente a nova senha autentica
```

#### AC-004 — Token ou senha rejeitados com segurança

**Cobre**: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004

```gherkin
@US-001 @FR-001 @FR-002 @FR-003 @FR-004 @NFR-001 @NFR-002 @NFR-003 @NFR-004 @AC-004
Feature: Recuperação segura de senha

  Scenario: rejeitar token expirado, reutilizado ou senha inválida
    Given um token inválido ou uma senha fraca, divergente ou igual à atual
    When a pessoa tenta concluir a redefinição
    Then a senha permanece inalterada e uma mensagem segura orienta nova solicitação
```

### 7. Requisitos

#### Funcionais

- **FR-001**: Expor solicitação pública que aceite e-mail normalizado e sempre retorne a mesma confirmação sem revelar estado da conta.
- **FR-002**: Para usuário ativo, criar token criptograficamente aleatório, persistir somente seu hash, expirar em 30 minutos e invalidar tokens pendentes anteriores.
- **FR-003**: Enviar link HTTPS pelo transporte SMTP/TLS configurado, com timeout limitado, remetente protegido e sem registrar token ou destinatário em logs.
- **FR-004**: Aceitar token válido e senha confirmada de 12 a 128 caracteres diferente da atual, trocar o hash transacionalmente e impedir expiração, reuso e consumo concorrente.

#### Não funcionais

- **NFR-001**: Limitar a três solicitações por hora por identidade e origem usando chaves HMAC hash-only. **Verificação**: testes de integração com e-mails e origens distintos.
- **NFR-002**: Não persistir ou registrar token, e-mail bruto de throttle, credencial SMTP ou senha. **Verificação**: inspeção da migration, models, logs sanitizados e testes de contrato.
- **NFR-003**: Responder à solicitação em até dois segundos no ambiente de teste, com timeout do SMTP configurável e falha externa sanitizada. **Verificação**: teste com transporte simulado lento/falho.
- **NFR-004**: Interface operável a partir de 360 px por teclado, com loading, sucesso, erro e foco perceptíveis. **Verificação**: lint, TypeScript, build e teste de contrato do componente.

#### Erros e casos-limite

- E-mail inexistente, inativo ou somente externo → confirmação neutra e nenhum token utilizável.
- SMTP ausente ou indisponível → confirmação neutra, token invalidado e evento técnico sanitizado.
- Token expirado, desconhecido, usado ou concorrente → `400` genérico e senha inalterada.
- Nova senha fraca, divergente ou igual à atual → `422`/`400`, token preservado enquanto ainda válido.
- Quarta solicitação na janela → confirmação neutra sem envio ou token adicional.

## Ato II — Projetar e provar

### 8. Plano técnico

#### Contexto existente

- FastAPI/Pydantic v2, SQLAlchemy 2, PostgreSQL/Alembic, Next.js 16/React 19/TypeScript e exportação estática no Netlify.
- Autenticação está em `backend/app/api.py`, `backend/app/auth.py` e `backend/app/core/security.py`; formulário público está em `frontend/components/operations-dashboard.tsx`.

#### Arquitetura e módulos

- `backend/app/password_reset.py` concentra criação, envio e consumo do token com transporte `EmailSender` injetável.
- `backend/app/api.py` expõe `POST /api/v1/auth/password-reset/request` e `POST /api/v1/auth/password-reset/confirm`.
- `frontend/components/operations-dashboard.tsx` amplia o estado de autenticação para login, cadastro, solicitação e redefinição.

#### Migrations

- Criar `password_reset_tokens` por Alembic após `20260825_0011`, com hash único, usuário, expiração, consumo, criação e índices. Downgrade remove apenas a tabela efêmera.

#### Models

- `PasswordResetToken`: UUID, `token_hash`, `user_id`, `expires_at`, `used_at`, `created_at`; somente o hash é persistido.
- Reutilizar `auth_login_throttles` com escopos específicos para recuperação, sem novo identificador bruto.

#### Controllers e casos de uso

- Request normaliza e-mail, verifica limite, mantém resposta constante e chama o serviço somente para usuário ativo.
- Confirm calcula hash, trava o registro elegível, valida senha, atualiza `User.password_hash` e marca tokens pendentes como usados na mesma transação.

#### Views e experiência


- O formulário atual recebe link `Esqueci minha senha`; solicitação usa o mesmo cartão. Quando a URL possui `reset_token`, o cartão mostra nova senha e confirmação, remove o token da URL após leitura e retorna ao login no sucesso.

#### Queries e repositórios

- Buscar token por hash único e janela temporal; índices em `token_hash`, `user_id` e `expires_at`. Limpeza oportunista remove expirados há mais de um dia.

#### Jobs e processamento assíncrono

- Não aplicável ao MVP; envio é síncrono com timeout curto. Evolução para fila não muda o contrato público.

#### Estrutura de arquivos

```text
backend/app/password_reset.py
backend/app/api.py
backend/app/models.py
backend/app/schemas.py
backend/app/core/config.py
backend/alembic/versions/20260826_0012_password_reset.py
backend/tests/test_password_reset.py
backend/tests/test_password_reset_migration.py
frontend/components/operations-dashboard.tsx
docs/
specs/draft/0003-recuperacao-senha/spec.md
```

### 9. Modelo de dados

#### Entidades

| Entidade | Identidade | Atributos e regras | Relações |
| --- | --- | --- | --- |
| PasswordResetToken | UUID | hash único, expiração de 30 min, uso opcional, criação; nenhum token bruto | N:1 User |
| AuthLoginThrottle | UUID | escopo, chave HMAC, contagem, janela, bloqueio | escopos `password_reset_identity` e `password_reset_origin` |

#### Estados e transições

| Entidade | Estado atual | Evento | Próximo estado | Invariantes |
| --- | --- | --- | --- | --- |
| PasswordResetToken | pending | confirmação válida | used | consumo único e senha alterada na mesma transação |
| PasswordResetToken | pending | expiração | expired | nunca altera senha |
| PasswordResetToken | pending | nova solicitação | invalidated/used | token anterior deixa de ser elegível |

#### Migração e retenção

- Migration aditiva; tokens expirados há mais de um dia são removidos oportunisticamente. Não há dados de domínio ou financeiros afetados.

### 10. Interfaces e contratos

#### Interface para pessoas

- **Há interface para pessoas**: Sim; o usuário sem sessão conclui solicitação e redefinição no cartão público de autenticação.

#### Stack e convenções de interface

- Preservar Next.js 16, React 19, TypeScript, Tailwind CSS, `OperationsDashboard`, cartão branco, azul elétrico, labels, `role=alert` e alvos mínimos de 44 px. Não introduzir biblioteca nova.

#### Telas e responsabilidades

- **Login**: ganha o link `Esqueci minha senha`.
- **Solicitar recuperação**: recebe e-mail e exibe confirmação neutra.
- **Criar nova senha**: recebe nova senha e confirmação quando há `reset_token` na URL.

#### Fluxo de informação e navegação

- Login → Esqueci minha senha → confirmação → link recebido → redefinição → login. Não há breadcrumb porque o fluxo é público e autocontido no cartão de autenticação.

#### Menus e navegação principal

- Não há menu principal ou secundário neste fluxo porque a pessoa ainda não está autenticada. O item `Esqueci minha senha` no cartão de login abre a solicitação; `Voltar ao login` retorna ao destino `/`; o link recebido abre `/?reset_token=<token>` e o sucesso retorna ao modo de login. Mobile e desktop usam os mesmos destinos no cartão responsivo.

#### Formulários e ações

- Solicitação: e-mail obrigatório, ação `Enviar link`, retorno neutro.
- Redefinição: nova senha e confirmação, 12–128 caracteres, ação `Redefinir senha`, erros perceptíveis sem expor token.

#### Composição e disposição

- Reusar shell, logomarca, contexto visual e cartão existentes; alternar apenas cabeçalho, campos e ações conforme o modo.

#### Blocos React e componentes selecionados

| Tela | Bloco React | Responsabilidade | Arquivo previsto | Componente ou composição | Origem | Reuso ou extensão |
| --- | --- | --- | --- | --- | --- | --- |
| Autenticação pública | LoginForm | Alternar login, cadastro e recuperação | `frontend/components/operations-dashboard.tsx` | formulário próprio existente | próprio | extensão do bloco atual |
| Solicitação | PasswordResetRequestForm | Capturar e-mail e mostrar confirmação | `frontend/components/operations-dashboard.tsx` | FieldLabel + cartão existente | próprio | novo bloco extraído se necessário |
| Redefinição | PasswordResetConfirmForm | Validar senha e confirmação | `frontend/components/operations-dashboard.tsx` | FieldLabel + cartão existente | próprio | novo bloco extraído se necessário |

- `INTERFACE.md` será atualizado com os blocos efetivamente materializados.

#### Estados e acessibilidade

- Loading desabilita a ação; sucesso usa `role=status`; erro usa `role=alert`; foco retorna ao título ou primeiro campo; token nunca é renderizado. Tabulação e envio por Enter permanecem funcionais.

#### APIs expostas

- `POST /api/v1/auth/password-reset/request`: sem autenticação; `{email}`; `202` com mensagem neutra em qualquer estado conhecido; validação `422` apenas para formato estrutural.
- `POST /api/v1/auth/password-reset/confirm`: sem autenticação; `{token,password,password_confirmation}`; `204` no sucesso; `400` genérico para token/senha sem validade; `422` para estrutura inválida.

#### APIs externas utilizadas

- SMTP autenticado com STARTTLS ou TLS implícito, timeout configurável e credenciais por ambiente. Sem retry automático na requisição para evitar duplicidade de envio.

#### Documentação das APIs consultadas

- Nenhuma documentação externa; usa protocolo SMTP pela biblioteca padrão Python e contrato interno injetável.

#### Eventos e outros contratos

- Não aplicável; logging registra apenas tipo de evento, resultado genérico e request ID sanitizado.

### 11. Estratégia TDD

- **Unidade**: geração/hash, expiração, validação de senha e transporte simulado.
- **Integração/contrato**: endpoints, banco SQLite de teste, migration e resposta uniforme.
- **BDD/aceite**: AC-001 a AC-004 orientam casos pytest com marcadores `SPECSFY:`.
- **Runner TDD**: pytest existente no backend; TypeScript e lint validam o frontend.
- **E2E**: fluxo HTTP completo com sender falso e login posterior.
- **Verificação manual**: apenas entrega SMTP real após configuração protegida no Render.

#### Evidência RED-GREEN-REFACTOR

| IDs | BDD de referência | Teste TDD informado pelo BDD | RED observado | GREEN observado | Refactor/regressão |
| --- | --- | --- | --- | --- | --- |
| US-001, FR-001–FR-004, NFR-001–NFR-004, AC-001 | AC-001 | `test_ac001_requests_password_reset_without_exposing_account` | RED válido em 2026-08-27: HTTP 404 porque a rota pública ainda não existe | GREEN em 2026-08-27: 202 neutro, link HTTPS único e resposta abaixo de dois segundos | Oráculo corrigido antes do RED para configurar campos SMTP futuros sem falha de fixture |
| US-001, FR-001–FR-004, NFR-001–NFR-004, AC-002 | AC-002 | `test_ac002_unknown_account_and_rate_limit_are_neutral` | RED válido em 2026-08-27: HTTP 404 porque a solicitação neutra ainda não existe | GREEN em 2026-08-27: desconhecido e quarta solicitação retornam o mesmo 202; três envios e um token pendente | Oráculo separa desconhecido e janela de abuso, mede envios e token pendente |
| US-001, FR-001–FR-004, NFR-001–NFR-004, AC-003 | AC-003 | `test_ac003_consumes_token_once_and_allows_new_login` | RED válido em 2026-08-27: HTTP 404 na solicitação porque o fluxo ainda não existe | GREEN em 2026-08-27: token atual consumido uma vez, anterior/reuso rejeitados e login aceita somente a nova senha | Oráculo cobre token anterior, reuso, senha antiga e login novo |
| US-001, FR-001–FR-004, NFR-001–NFR-004, AC-004 | AC-004 | `test_ac004_rejects_expired_reused_or_invalid_password` | RED válido em 2026-08-27: HTTP 404 na solicitação porque validação/consumo ainda não existem | GREEN em 2026-08-27: senhas inválidas, token usado, expirado e desconhecido rejeitados com contratos previstos | Oráculo tabelado preserva token após erro de senha e compara respostas de token expirado/desconhecido |
| US-001, FR-002, FR-004, NFR-002, AC-001, AC-003, AC-004 | Contrato de persistência | `test_password_reset_migration_is_hash_only_indexed_and_reversible` | RED válido em 2026-08-27: migration `20260826_0012` ausente | GREEN: migration/model hash-only; 5 testes Alembic passaram | Ruff corrigiu somente ordenação de imports; mypy aprovado |

### 12. Plano de testes e rastreabilidade

| Requisito | Cenário BDD | Nível | Arquivo/comando esperado | Evidência |
| --- | --- | --- | --- | --- |
| FR-001–FR-004 | AC-001 | Integração | `pytest tests/test_password_reset.py::test_ac001_requests_password_reset_without_exposing_account -q` | Passed; incluído na regressão final de 72 testes |
| FR-001–FR-004 | AC-002 | Segurança | `pytest tests/test_password_reset.py::test_ac002_unknown_account_and_rate_limit_are_neutral -q` | Passed; incluído na regressão final de 72 testes |
| FR-001–FR-004 | AC-003 | E2E HTTP | `pytest tests/test_password_reset.py::test_ac003_consumes_token_once_and_allows_new_login -q` | Passed; incluído na regressão final de 72 testes |
| FR-001–FR-004 | AC-004 | Regra/limite | `pytest tests/test_password_reset.py::test_ac004_rejects_expired_reused_or_invalid_password -q` | Passed; incluído na regressão final de 72 testes |
| NFR-001–NFR-003 | AC-001–AC-004 | Contrato | `pytest tests/test_password_reset_migration.py tests/test_password_reset.py -q` | GREEN; migration focal 5 passed e suíte completa 72 passed |
| NFR-004 | AC-001–AC-004 | Estático/interface | `npm run lint && npm run test && npm run build` | GREEN; lint, TypeScript e 9 páginas estáticas aprovados |

### 13. Validações

#### Gate do Ato I — Definição

- **Resultado**: READY — 2026-08-26
- **Comando**: `node .agents/skills/specsfy-04-validate/scripts/validate_spec.mjs specs/draft/0003-recuperacao-senha/spec.md`
- **Achados**: Estrutura válida; 1 US, 4 FR e 4 NFR cobertos por quatro AC distintos; revisão PROD/ARCH/SEC sem finding P1 aberto.

#### Gate do Ato II — Plano

- **Resultado**: Passed — 2026-08-27
- **Comando**: `node .agents/skills/specsfy-05-tasks/scripts/validate_tasks.mjs specs/defined/0003-recuperacao-senha/spec.md`
- **Achados**: 16 tarefas, 5 predecessores TDD concluídos com RED válido, 6 tarefas de código, 80 itens de checklist e 13/13 IDs cobertos; interface validada para as três telas públicas.

#### Gate do Ato III — Entrega

- **Resultado**: Passed — 2026-08-27
- **Comando**: `docker compose -p logisync-spec3-gate --profile test run --rm api-tests`
- **Achados**: Gate isolado aprovado com 72 testes, Ruff em `app tests` e mypy em 17 fontes dentro do container; localmente também passaram 72 testes, 5 testes de migration, lint, TypeScript, build de 9 páginas e rastreabilidade 13/13. PostgreSQL e API ficaram `healthy`; frontend, n8n e Metabase responderam com sucesso. O projeto sintético e seus volumes foram removidos após a verificação, preservando os volumes originais. O aceite rígido retornou `READY`, as lentes de revisão passaram e o enforcement local do repositório aprovou todas as specs e canários.

### 14. Tarefas

#### Fase 1 — RED TDD informado pelo BDD

- [x] T001 [TEST] [TDD] [US-001] Derivar AC-001 em `backend/tests/test_password_reset.py` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-001 — Depends: none
  - [x] **PREP**: Resposta neutra, conta ativa, transporte injetável, link HTTPS único e orçamento de dois segundos confirmados no AC-001.
  - [x] **EXECUTE**: Caso pytest criado com marcador `SPECSFY:`, SMTP falso e inspeção somente do link entregue em memória.
  - [x] **VERIFY**: Após corrigir uma falha de fixture do Pydantic, o teste focal observou RED válido: esperado HTTP 202, recebido 404 por rota ausente.
  - [x] **EVIDENCE**: `pytest tests/test_password_reset.py::test_ac001_requests_password_reset_without_exposing_account -q` terminou com `1 failed`; causa e IDs registrados nas seções 11–13.
  - [x] **IMPROVE**: O oráculo mede dois segundos, exige um único link HTTPS e impede e-mail da conta na resposta pública.
- [x] T002 [TEST] [TDD] [US-001] Derivar AC-002 em `backend/tests/test_password_reset.py` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-002 — Depends: none
  - [x] **PREP**: Equivalência pública para conta desconhecida e limite de três solicitações por hora por identidade/origem confirmados no AC-002.
  - [x] **EXECUTE**: Caso pytest criado com marcador `SPECSFY:` cobrindo desconhecido, quarta solicitação, envios e quantidade de token pendente.
  - [x] **VERIFY**: Teste focal observou RED válido: esperado HTTP 202 neutro, recebido 404 porque a rota ainda não existe.
  - [x] **EVIDENCE**: `pytest tests/test_password_reset.py::test_ac002_unknown_account_and_rate_limit_are_neutral -q` terminou com `1 failed`; causa e IDs registrados nas seções 11–13.
  - [x] **IMPROVE**: O oráculo compara corpo/status uniformes e isola os buckets antes da janela de quatro tentativas.
- [x] T003 [TEST] [TDD] [US-001] Derivar AC-003 em `backend/tests/test_password_reset.py` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-003 — Depends: none
  - [x] **PREP**: Consumo único transacional, invalidação dos pendentes e autenticação apenas com a nova senha confirmados no AC-003.
  - [x] **EXECUTE**: Caso pytest criado com marcador `SPECSFY:` para duas solicitações, confirmação, token anterior, reuso e login antigo/novo.
  - [x] **VERIFY**: Teste focal observou RED válido: esperado HTTP 202, recebido 404 na primeira solicitação porque o fluxo ainda não existe.
  - [x] **EVIDENCE**: `pytest tests/test_password_reset.py::test_ac003_consumes_token_once_and_allows_new_login -q` terminou com `1 failed`; causa e IDs registrados nas seções 11–13.
  - [x] **IMPROVE**: O oráculo prova mudança real de credencial e impede falso positivo baseado somente na confirmação HTTP.
- [x] T004 [TEST] [TDD] [US-001] Derivar AC-004 em `backend/tests/test_password_reset.py` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-004 — Depends: none
  - [x] **PREP**: Token expirado/desconhecido/usado, senha fraca/divergente/igual e preservação após erro confirmados no AC-004.
  - [x] **EXECUTE**: Caso tabelado criado com marcador `SPECSFY:`, atualização controlada da expiração e comparações seguras.
  - [x] **VERIFY**: Teste focal observou RED válido: esperado HTTP 202, recebido 404 na solicitação porque o fluxo ainda não existe.
  - [x] **EVIDENCE**: `pytest tests/test_password_reset.py::test_ac004_rejects_expired_reused_or_invalid_password -q` terminou com `1 failed`; causa e IDs registrados nas seções 11–13.
  - [x] **IMPROVE**: O oráculo exige mensagem idêntica para token expirado/desconhecido e prova que erros de senha não consomem o token válido.
- [x] T005 [TEST] [TDD] [US-001] Provar migration e armazenamento hash-only em `backend/tests/test_password_reset_migration.py` — Refs: US-001, FR-002, FR-004, NFR-002, AC-001, AC-003, AC-004 — Depends: none
  - [x] **PREP**: Revisão `20260826_0012`, colunas, chaves, índices, downgrade e ausência de token bruto confirmados no plano técnico.
  - [x] **EXECUTE**: Teste de contrato Alembic criado com marcador `SPECSFY:` e inspeção de upgrade/downgrade.
  - [x] **VERIFY**: Teste focal observou RED válido: `MIGRATION_PATH.is_file()` falhou porque a migration ainda não existe.
  - [x] **EVIDENCE**: `pytest tests/test_password_reset_migration.py::test_password_reset_migration_is_hash_only_indexed_and_reversible -q` terminou com `1 failed`; causa e IDs registrados nas seções 11–13.
  - [x] **IMPROVE**: O contrato rejeita explicitamente `token`, `email` e `password` e exige unicidade e índices operacionais.

#### Fase 2 — Persistência e domínio

- [x] T006 [CODE] [US-001] Criar `PasswordResetToken` e migration em `backend/app/models.py` e `backend/alembic/versions/20260826_0012_password_reset.py` — Refs: US-001, FR-002, FR-004, NFR-002, AC-001, AC-003, AC-004 — Depends: T001, T003, T004, T005
  - [x] **PREP**: RED da T005, revisão `20260825_0011`, tipos UUID/timestamp, unicidade do hash, relação restritiva, índices e retenção efêmera confirmados; baseline anterior aprovado com 65 testes.
  - [x] **EXECUTE**: Model e migration hash-only implementados; `$specsfy-documentator` reconstruiu `docs/` e `.specsfy/PACKAGES.md` com `--check` aprovado.
  - [x] **VERIFY**: Cinco testes Alembic passaram; Ruff passou após ordenar imports e mypy não encontrou problemas no model.
  - [x] **EVIDENCE**: GREEN, arquivos e comandos registrados no contrato abaixo; a mudança isolada de persistência ainda não altera a capacidade pública descrita em `PROJECT.md`, prevista na T013.
  - [x] **IMPROVE**: Migration explicita unique constraint e índices de hash, usuário e expiração; nenhum campo redundante ou secreto foi criado.
  <!-- specsfy:evidence {"task":"T006","refs":["US-001","FR-002","FR-004","NFR-002","AC-001","AC-003","AC-004"],"files":["backend/app/models.py","backend/alembic/versions/20260826_0012_password_reset.py","backend/tests/test_password_reset_migration.py"],"commands":[{"run":"pytest tests/test_password_reset_migration.py tests/test_auth_hardening_migration.py tests/test_bi_migration.py -q","exit":0},{"run":"ruff check app/models.py alembic/versions/20260826_0012_password_reset.py tests/test_password_reset_migration.py","exit":0},{"run":"mypy app/models.py","exit":0},{"run":"node .agents/skills/specsfy-documentator/scripts/build_documentation.mjs --project <raiz> --check","exit":0}]} -->
- [x] T007 [DOC] [US-001] Atualizar persistência em `.specsfy/DATABASE.md` — Refs: US-001, FR-002, FR-004, NFR-002, AC-001, AC-003, AC-004 — Depends: T006
  - [x] **PREP**: Model, migration `0012` e política de retenção foram confrontados antes da atualização.
  - [x] **EXECUTE**: `.specsfy/DATABASE.md` registra tabela, campos, relação, índices, uso único, expiração e limpeza hash-only; o conteúdo humano preexistente foi preservado.
  - [x] **VERIFY**: `monitor_context.mjs --check --paths .specsfy/DATABASE.md backend/app/models.py backend/alembic/versions/20260826_0012_password_reset.py specs/in-progress/0003-recuperacao-senha/spec.md` retornou `Context monitor: CURRENT`.
  - [x] **EVIDENCE**: Evidências em `.specsfy/DATABASE.md`, `backend/app/models.py`, migration `20260826_0012_password_reset.py` e saída CURRENT do monitor em 2026-08-27.
  - [x] **IMPROVE**: A projeção automática incompleta foi corrigida para restaurar o inventário existente e acrescentar apenas `password_reset_tokens` e sua decisão de retenção.
- [x] T008 [CODE] [US-001] Implementar geração, throttle, envio e consumo em `backend/app/password_reset.py` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, AC-001, AC-002, AC-003, AC-004 — Depends: T001, T002, T003, T004, T006
  - [x] **PREP**: RED das T001–T004 e precedentes de HMAC/throttle foram confirmados; relógio e sender são injetáveis e a confirmação bloqueia a linha do token.
  - [x] **EXECUTE**: Serviço implementado com token aleatório, SHA-256, TTL de 30 minutos, invalidação, limite hash-only de 3/h, SMTP/STARTTLS injetável, consumo único e log sanitizado; documentator executado.
  - [x] **VERIFY**: Testes focais retornaram 2 passed; Ruff e mypy passaram sem token bruto persistido ou segredo em log.
  - [x] **EVIDENCE**: GREEN, arquivos e comandos registrados no contrato abaixo.
  - [x] **IMPROVE**: Falha SMTP invalida o token emitido; escopos internos `reset_identity` e `reset_origin` respeitam `varchar(20)`; constantes e transações ficaram isoladas no serviço.
  <!-- specsfy:evidence {"task":"T008","refs":["US-001","FR-001","FR-002","FR-003","FR-004","NFR-001","NFR-002","NFR-003","AC-001","AC-002","AC-003","AC-004"],"files":["backend/app/password_reset.py","backend/tests/test_password_reset_service.py"],"commands":[{"run":"pytest tests/test_password_reset_service.py -q","exit":0},{"run":"ruff check app/password_reset.py tests/test_password_reset_service.py","exit":0},{"run":"mypy app/password_reset.py","exit":0},{"run":"node .agents/skills/specsfy-documentator/scripts/build_documentation.mjs --project <raiz> --check","exit":0}]} -->
- [x] T009 [CODE] [US-001] Expor schemas, configuração e endpoints em `backend/app/schemas.py`, `backend/app/core/config.py` e `backend/app/api.py` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, AC-001, AC-002, AC-003, AC-004 — Depends: T001, T002, T003, T004, T008
  - [x] **PREP**: Contratos 202/204/400/422, normalização, confirmação, origem derivada e neutralidade foram fixados nos schemas e testes.
  - [x] **EXECUTE**: Serviço e sender SMTP/STARTTLS integrados a endpoints públicos; configuração fica somente em `Settings`/ambiente e o documentator foi executado.
  - [x] **VERIFY**: 6 testes focais e de serviço e 17 testes de autenticação passaram; Ruff e mypy passaram; logs não incluem e-mail, token ou segredo.
  - [x] **EVIDENCE**: GREEN, arquivos e comandos registrados no contrato abaixo.
  - [x] **IMPROVE**: Mensagens públicas foram centralizadas; conta ausente, limite e falha de transporte seguem o mesmo 202, e token inválido/expirado segue o mesmo 400.
  <!-- specsfy:evidence {"task":"T009","refs":["US-001","FR-001","FR-002","FR-003","FR-004","NFR-001","NFR-002","NFR-003","AC-001","AC-002","AC-003","AC-004"],"files":["backend/app/api.py","backend/app/schemas.py","backend/app/core/config.py","backend/app/password_reset.py","backend/tests/test_password_reset.py"],"commands":[{"run":"pytest tests/test_password_reset.py tests/test_password_reset_service.py -q","exit":0},{"run":"pytest tests/test_auth.py tests/test_auth_hardening.py -q","exit":0},{"run":"ruff check app/api.py app/schemas.py app/core/config.py app/password_reset.py tests/test_password_reset.py tests/test_password_reset_service.py","exit":0},{"run":"mypy app/api.py app/schemas.py app/core/config.py app/password_reset.py","exit":0},{"run":"node .agents/skills/specsfy-documentator/scripts/build_documentation.mjs --project <raiz> --check","exit":0}]} -->

#### Fase de interface

- [x] T010 [CODE] [US-001] Implementar entrada de recuperação no Login em `frontend/components/operations-dashboard.tsx` — Refs: US-001, FR-001, FR-003, FR-004, NFR-003, NFR-004, AC-001, AC-002, AC-003, AC-004 — Depends: T001, T002, T003, T004, T009
  - [x] **PREP**: Modo do `LoginForm`, links de ida/volta, foco, teclado e largura fluida de 360 px foram preservados no cartão existente.
  - [x] **EXECUTE**: Navegação entre login e recuperação adicionada sem duplicar shell; documentator executado.
  - [x] **VERIFY**: Contrato estático inspecionado; lint, TypeScript e build Next.js com 9 páginas prerenderizadas passaram.
  - [x] **EVIDENCE**: GREEN, arquivo e comandos registrados no contrato abaixo.
  - [x] **IMPROVE**: O mesmo cartão e `FieldLabel` permanecem como composição única; ações têm alvos mínimos de 44 px.
  <!-- specsfy:evidence {"task":"T010","refs":["US-001","FR-001","FR-003","FR-004","NFR-003","NFR-004","AC-001","AC-002","AC-003","AC-004"],"files":["frontend/components/operations-dashboard.tsx"],"commands":[{"run":"npm run lint","exit":0},{"run":"npm run test","exit":0},{"run":"npm run build","exit":0},{"run":"node .agents/skills/specsfy-documentator/scripts/build_documentation.mjs --project <raiz> --check","exit":0}]} -->
- [x] T015 [CODE] [US-001] Implementar tela de solicitação em `frontend/components/operations-dashboard.tsx` — Refs: US-001, FR-001, FR-003, NFR-003, NFR-004, AC-001, AC-002, AC-004 — Depends: T001, T002, T004, T009, T010
  - [x] **PREP**: Campo de e-mail, ação, mensagem neutra, loading, sucesso, erro, foco e Enter foram confirmados no contrato.
  - [x] **EXECUTE**: Formulário de solicitação implementado no cartão existente e ligado ao endpoint 202; documentator executado.
  - [x] **VERIFY**: Contrato responsivo inspecionado; lint, TypeScript e build de 9 páginas passaram.
  - [x] **EVIDENCE**: GREEN, arquivo e comandos registrados no contrato abaixo.
  - [x] **IMPROVE**: A UI apresenta exatamente a mensagem neutra da API, sem distinção entre conta conhecida, desconhecida ou limitada.
  <!-- specsfy:evidence {"task":"T015","refs":["US-001","FR-001","FR-003","NFR-003","NFR-004","AC-001","AC-002","AC-004"],"files":["frontend/components/operations-dashboard.tsx"],"commands":[{"run":"npm run lint","exit":0},{"run":"npm run test","exit":0},{"run":"npm run build","exit":0},{"run":"node .agents/skills/specsfy-documentator/scripts/build_documentation.mjs --project <raiz> --check","exit":0}]} -->
- [x] T016 [CODE] [US-001] Implementar tela de nova senha em `frontend/components/operations-dashboard.tsx` — Refs: US-001, FR-001, FR-004, NFR-003, NFR-004, AC-001, AC-003, AC-004 — Depends: T001, T003, T004, T009, T010
  - [x] **PREP**: Captura/remoção do token, duas senhas, ação, erros genéricos e retorno ao login foram confirmados no contrato.
  - [x] **EXECUTE**: Formulário de confirmação implementado sem renderizar o token; 204 limpa estado e retorna ao login; documentator executado.
  - [x] **VERIFY**: Contrato responsivo e por teclado inspecionado; lint, TypeScript e build de 9 páginas passaram.
  - [x] **EVIDENCE**: GREEN, arquivo e comandos registrados no contrato abaixo.
  - [x] **IMPROVE**: `reset_token` é removido da URL antes da transição visual; segredo e erro são limpos ao concluir ou cancelar.
  <!-- specsfy:evidence {"task":"T016","refs":["US-001","FR-001","FR-004","NFR-003","NFR-004","AC-001","AC-003","AC-004"],"files":["frontend/components/operations-dashboard.tsx"],"commands":[{"run":"npm run lint","exit":0},{"run":"npm run test","exit":0},{"run":"npm run build","exit":0},{"run":"node .agents/skills/specsfy-documentator/scripts/build_documentation.mjs --project <raiz> --check","exit":0}]} -->
- [x] T011 [DOC] [US-001] Registrar os blocos de recuperação em `INTERFACE.md` — Refs: US-001, FR-001, FR-003, FR-004, NFR-004, AC-001, AC-002, AC-003, AC-004 — Depends: T010, T015, T016
  - [x] **PREP**: Modos efetivos, consumidores, API, estados e composição do cartão foram inspecionados no componente entregue.
  - [x] **EXECUTE**: Inventário canônico atualizado com `reset-request` e `reset-confirm`, sem atribuir bibliotecas não usadas.
  - [x] **VERIFY**: Caminhos, teclado, estados, responsividade e `DESIGNSYSTEM.MD` foram conferidos; monitor retornou `CURRENT`.
  - [x] **EVIDENCE**: Evidências em `INTERFACE.md`, `frontend/components/operations-dashboard.tsx` e saída CURRENT do monitor em 2026-08-27.
  - [x] **IMPROVE**: Acessibilidade, neutralidade pública e remoção do segredo da URL substituíram qualquer ambiguidade documental.

#### Fase 3 — Operação, documentação e gate final

- [x] T012 [OPS] [US-001] Documentar configuração SMTP e deploy seguro em `docs/runbook.md` — Refs: US-001, FR-003, NFR-002, NFR-003, AC-001, AC-002 — Depends: T009
  - [x] **PREP**: Os sete nomes reais, STARTTLS, timeout, remetente e comportamento indisponível foram confirmados no código.
  - [x] **EXECUTE**: Runbook, exemplo local, contrato de produção e Compose atualizados sem valores reais nem dependência de fornecedor.
  - [x] **VERIFY**: `docker compose config --quiet` passou com valores sintéticos; validador de produção passou; nenhum segredo real foi incluído.
  - [x] **EVIDENCE**: Evidências em `docs/runbook.md`, `.env.example`, `docker-compose.yml`, `infra/hosting/production.env.example`, validador e monitor `CURRENT`.
  - [x] **IMPROVE**: Troubleshooting sanitizado cobre conexão, STARTTLS, autenticação, remetente, timeout e correlação sem dados sensíveis.
- [x] T013 [DOC] [US-001] Registrar capacidade e regras duráveis em `PROJECT.md` e `.specsfy/RULES.md` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-001, AC-002, AC-003, AC-004 — Depends: T007, T009, T011, T012
  - [x] **PREP**: Somente capacidade e decisões comprovadas pelos testes e código entregues foram reunidas.
  - [x] **EXECUTE**: `PROJECT.md` atualizado e quatro regras duráveis adicionadas pela skill `specsfy-aux-rules`, preservando conteúdo existente.
  - [x] **VERIFY**: Documentator `--check` passou e o monitor retornou `CURRENT` sem pendência indevida.
  - [x] **EVIDENCE**: Evidências em `PROJECT.md`, `.specsfy/RULES.md`, documentação projetada e saídas dos validadores em 2026-08-27.
  - [x] **IMPROVE**: Regras operacionais ficaram consolidadas sem duplicar a narrativa normativa detalhada da spec.
- [x] T014 [TEST] [US-001] Executar regressão e rastreabilidade finais em `backend/tests/test_password_reset.py` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-001, AC-002, AC-003, AC-004 — Depends: T006, T007, T008, T009, T010, T015, T016, T011, T012, T013
  - [x] **PREP**: Todas as 15 predecessoras, suites, gates e contratos aplicáveis foram confirmados; daemon Docker do host foi diagnosticado antes do gate operacional.
  - [x] **EXECUTE**: Pytest completo, Ruff normativo, mypy, lint, TypeScript, build, migrations, Compose config, full-chain, containers e health checks passaram.
  - [x] **VERIFY**: Quatro AC, 13/13 IDs, Evidence Contract estrito e runtime do Compose foram confirmados sem gaps ou segredos.
  - [x] **EVIDENCE**: Seções 11–13 registram 72 passed local e no container, 5 migrations passed, lint/tipagem/build, rastreabilidade completa e health checks aprovados em 2026-08-27.
  - [x] **IMPROVE**: Divergência naive/UTC e caches Ruff/mypy incompatíveis com o mount somente leitura foram corrigidos; dependências frontend foram instaladas com CA do Windows; débitos Ruff históricos fora do escopo normativo foram registrados sem alteração oportunista.

### 15. Ordem de execução

- Caminho crítico: T001/T002/T003/T004/T005 → T006 → T007/T008 → T009 → T010 → T015/T016 → T011 e T012 → T013 → T014.
- T001–T005 podem ser preparados em paralelo porque escrevem testes distintos ou arquivos distintos; a execução permanece sequencial quando compartilhar fixtures ou banco.
- T007 e T008 podem avançar após T006; T015 e T016 compartilham componente e serão sequenciais; T011 e T012 podem avançar após seus predecessores sem compartilhar arquivos.
- Estratégia de MVP: comprovar primeiro todos os RED e o contrato de migration; depois entregar persistência, serviço, API, interface pública e fechar documentação/gates.

## Ato III — Entregar e validar

### 16. Dependências, riscos e suposições

#### Dependências

- Servidor SMTP com TLS, remetente autorizado e credenciais protegidas no Render para envio real.
- `FRONTEND_URL` HTTPS correto para formar o link.

#### Riscos

- Enumeração de conta → resposta neutra, trabalho equivalente e throttle hash-only.
- Vazamento/reuso de token → entropia, hash, curta expiração e consumo transacional.
- Falha do SMTP → invalidar token não entregue, sanitizar log e permitir nova solicitação.
- Serviço gratuito hibernado → mensagem de loading no frontend e timeout limitado.

#### Suposições

- SMTP/TLS é o adaptador inicial reversível; o provedor concreto não altera o domínio.
- Expiração de 30 minutos e limite de três solicitações por hora equilibram usabilidade e abuso.
- JWT existentes não são globalmente revogados nesta fatia; expiram pelo limite atual.

### 17. Decisões

- **DEC-001**: Usar token opaco aleatório e persistir somente SHA-256, preservando o padrão do OAuth e evitando segredo recuperável no banco.
- **DEC-002**: Usar SMTP/TLS configurável em vez de SDK comercial, reduzindo acoplamento e deixando a escolha operacional reversível.
- **DEC-003**: Retornar confirmação neutra inclusive em falha conhecida de conta, sem incluir token ou estado do envio.
- **DEC-004**: Não revogar JWT existentes nesta entrega porque o modelo atual não possui versão de sessão; essa evolução exige spec própria.

### 18. Definition of Done

- [x] `Definition Gate` está `Passed`.
- [x] `Plan Gate` está `Passed`.
- [x] `Delivery Gate` está `Passed`.
- [x] AC-001 a AC-004 passam e possuem marcadores `SPECSFY:` próprios.
- [x] Migration, models e documentação de banco refletem somente hashes e retenção efêmera.
- [x] `.specsfy/DATABASE.md` registra a tabela, os índices e a retenção dos tokens.
- [x] `PROJECT.md` e `.specsfy/RULES.md` registram a nova capacidade e suas regras duráveis de segurança.
- [x] Resposta uniforme, throttle, expiração, consumo único, concorrência e falha SMTP estão testados.
- [x] Interface de solicitação/redefinição passa lint, TypeScript, build e verificação responsiva.
- [x] Backend passa pytest, Ruff e mypy; frontend passa lint, TypeScript e build.
- [x] Configuração SMTP e procedimento de deploy estão documentados sem segredos.
