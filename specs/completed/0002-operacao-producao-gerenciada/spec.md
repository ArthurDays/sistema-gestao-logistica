# Especificação integrada: Operação segura em Netlify e Render

| Campo | Valor |
| --- | --- |
| Formato | Specsfy/2.0 |
| ID | SPEC-0002 |
| Slug | 0002-operacao-producao-gerenciada |
| Status | Complete |
| Effort | 7 |
| Effort updated at | 2026-08-24 |
| Effort rationale | Endurecimento de produção entre Netlify, Render e PostgreSQL, com segurança, observabilidade, recuperação e CI. |
| ClickUp Task | Não vinculada |
| Milestones | Produção observável |
| Definition Gate | Passed |
| Plan Gate | Passed |
| Delivery Gate | Passed |
| Evidence Contract | 1 |
| Interface para pessoas | Não — a fatia altera somente configuração operacional, automação e documentação. |
| Atualizada em | 2026-08-24 |

## Ato I — Definir

### 1. Problema e resultado

#### Problema

O MVP LogiSync funciona com frontend no Netlify, API e PostgreSQL no Render, mas a operação ainda depende de configuração manual e não possui prova automatizada de URLs seguras, observabilidade, backup restaurável, CI e recuperação.

#### Resultado desejado

A operação gerenciada deve ser reproduzível, segura e recuperável sem introduzir Traefik onde Netlify e Render já terminam HTTPS.

#### Métricas de sucesso

- 100% dos contratos operacionais desta fatia validados no CI.
- Restauração de backup validada em banco descartável.
- Nenhum segredo persistido no Git ou emitido em logs.
- Runbook suficiente para deploy, rollback e recuperação.

### 2. Research e esclarecimentos

#### Researchs executados

- **R-001**: A topologia publicada já usa TLS gerenciado por Netlify e Render; Traefik seria redundante neste desenho.
- **R-002**: O Compose local deve ser preservado e separado da configuração gerenciada.

#### Fontes e contexto consultados

- `docker-compose.yml`, `.github/workflows/ci.yml`, `backend/app/core/config.py`, `frontend/next.config.ts` e SPEC-0001.

#### Documentação consultada

- Nenhuma fonte externa; a definição usa contratos e configurações locais já observados.

#### Artefatos de pesquisa armazenados

- `specs/completed/0002-operacao-producao-gerenciada/research/local-operational-evidence.md` — evidência exclusivamente local; nenhuma fonte externa foi consultada.

#### Dúvidas respondidas

- **Q**: Usar Traefik ou HTTPS gerenciado? → **A**: preservar Netlify + Render e usar o TLS gerenciado.
- **Q**: Alterar a finalidade do Compose? → **A**: não; ele continua como ambiente local e de validação.

#### Dúvidas abertas

- Nenhuma bloqueante; domínio personalizado e DSN do Sentry permanecem opcionais.

### 3. Escopo e atores

#### Incluído

- Contratos automatizados para HTTPS, CORS, callback OAuth e ausência de segredos.
- Configuração declarativa de Netlify e Render.
- Logs estruturados, Sentry opcional, backup/restauração, CI e runbook.

#### Fora de escopo

- VPS, Kubernetes, Docker Swarm ou Traefik.
- Compra de domínio ou plano pago.
- Mudanças funcionais, visuais ou de schema do MVP.

#### Atores

- **Responsável operacional**: publica versões, acompanha falhas e executa recuperação.
- **Pessoa usuária**: espera acesso HTTPS estável e preservação de dados.
- **Pipeline CI**: bloqueia violações dos contratos da entrega.

### 4. Princípios e restrições do projeto

- **PR-001**: Segredos entram somente por variáveis protegidas e nunca pelo Git.
- **PR-002**: Netlify hospeda frontend e Render hospeda API e PostgreSQL.
- **PR-003**: Backup só é válido após restauração isolada.
- **PR-004**: Logs não registram tokens, senhas, cookies ou URLs completas de banco.

### 5. Histórias de usuário

#### US-001 — Operar o LogiSync com segurança e recuperação (P1)

Como responsável operacional, quero uma entrega gerenciada verificável e recuperável, para publicar o sistema sem configuração implícita ou diagnóstico manual.

**Por que P1**: reduz risco de indisponibilidade, perda de dados e configuração insegura.
**Teste independente**: executar contratos operacionais, backup/restauração e workflow.
**Requisitos**: FR-001, FR-002, FR-003

### 6. Cenários BDD de aceite

#### AC-001 — Configuração segura e coerente

**Cobre**: US-001, FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003

```gherkin
@US-001 @FR-001 @FR-002 @FR-003 @NFR-001 @NFR-002 @NFR-003 @AC-001
Feature: Operação gerenciada do LogiSync
  Scenario: contratos de produção válidos
    Given a topologia Netlify, Render e PostgreSQL declarada no repositório
    When os contratos operacionais são validados
    Then URLs públicas usam HTTPS, origens são coerentes e segredos não estão versionados
```

#### AC-002 — Configuração insegura bloqueada

**Cobre**: US-001, FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003

```gherkin
@US-001 @FR-001 @FR-002 @FR-003 @NFR-001 @NFR-002 @NFR-003 @AC-002
Feature: Gate operacional
  Scenario: mudança insegura não é publicada
    Given uma configuração com HTTP público, segredo literal ou verificação ausente
    When o pipeline executa os gates
    Then a execução falha com diagnóstico acionável antes do deploy
```

#### AC-003 — Recuperação reproduzível

**Cobre**: US-001, FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003

```gherkin
@US-001 @FR-001 @FR-002 @FR-003 @NFR-001 @NFR-002 @NFR-003 @AC-003
Feature: Recuperação operacional
  Scenario: incidente recuperado com evidência
    Given um backup válido e uma versão anterior conhecida
    When o responsável segue somente o runbook
    Then restaura os dados isoladamente, executa rollback e confirma saúde sem expor segredos
```

### 7. Requisitos

#### Funcionais

- **FR-001**: O repositório deve declarar URLs HTTPS, URL do frontend, CORS e callback OAuth coerentes com Netlify e Render.
- **FR-002**: A API deve produzir logs estruturados e permitir Sentry opcional sem registrar dados sensíveis.
- **FR-003**: A operação deve gerar e restaurar backup isolado, executar todos os gates no CI e documentar deploy, rollback e incidentes.

#### Não funcionais

- **NFR-001**: Toda URL pública declarada usa HTTPS e nenhum segredo real fica versionado. **Verificação**: teste estático.
- **NFR-002**: Cada falha de contrato indica arquivo e correção esperada. **Verificação**: cenários negativos.
- **NFR-003**: Backup é restaurável sem destruir a origem e logs correlacionam requisições. **Verificação**: restauração descartável e teste de logging.

#### Erros e casos-limite

- Integração opcional ausente → serviço inicia com integração desativada.
- HTTP público ou origem ampla em produção → gate falha.
- Backup vazio ou corrompido → restauração falha sem tocar a origem.
- Instância gratuita hibernada → runbook comunica cold start e health check.

## Ato II — Projetar e provar

### 8. Plano técnico

#### Contexto existente

- Next.js estático no Netlify, FastAPI e PostgreSQL no Render e Compose local.

#### Arquitetura e módulos

- `infra/hosting/` concentra exemplos e validação gerenciada; `backend/app/core/logging.py` concentra logging; `infra/postgres/` contém backup/restauração; CI reúne os gates.

#### Migrations

- Não aplicável; nenhum schema muda.

#### Models

- Não aplicável; nenhum modelo persistente muda.

#### Controllers e casos de uso

- Não aplicável; endpoints existentes são preservados.

#### Views e experiência

- Não aplicável; a interface publicada não muda.

#### Queries e repositórios

- Não aplicável; ferramentas PostgreSQL operam o backup.

#### Jobs e processamento assíncrono

- Agendamento fica documentado; ativação externa exige credencial protegida.

#### Estrutura de arquivos

```text
infra/hosting/production.env.example
infra/hosting/validate-production-config.ps1
infra/postgres/backup.ps1
infra/postgres/restore-check.ps1
backend/app/core/logging.py
backend/tests/production/test_production_contracts.py
.github/workflows/ci.yml
docs/runbook.md
```

### 9. Modelo de dados

#### Entidades

| Entidade | Identidade | Atributos e regras | Relações |
| --- | --- | --- | --- |
| Artefato de backup | timestamp + checksum | não vazio e restaurável | snapshot lógico do PostgreSQL |
| Evento de log | request_id | nível, mensagem, contexto sanitizado | correlaciona requisição e erro |

#### Estados e transições

| Entidade | Estado atual | Evento | Próximo estado | Invariantes |
| --- | --- | --- | --- | --- |
| Backup | gerado | restauração isolada aprovada | validado | origem não é alterada |
| Deploy | candidato | gates aprovados | publicável | todos os checks passam |
| Deploy | candidato | gate falha | bloqueado | diagnóstico identifica a falha |

#### Migração e retenção

- Sem migration. Retenção padrão: sete backups diários e quatro semanais, ajustável.

### 10. Interfaces e contratos

#### Interface para pessoas

- **Há interface para pessoas**: Não; trabalho operacional sem mudança de tela.

#### Stack e convenções de interface

- Não aplicável; Next.js e React existentes são preservados.

#### Telas e responsabilidades

- Não aplicável.

#### Fluxo de informação e navegação

- Não aplicável.

#### Menus e navegação principal

- Não aplicável.

#### Formulários e ações

- Não aplicável; variáveis ficam nos painéis dos provedores.

#### Composição e disposição

- Não aplicável.

#### Blocos React e componentes selecionados

| Tela | Bloco React | Responsabilidade | Arquivo previsto | Componente ou composição | Origem | Reuso ou extensão |
| --- | --- | --- | --- | --- | --- | --- |
| Não aplicável | Não aplicável | Sem alteração visual | Não aplicável | Não aplicável | Não aplicável | Preservar existente |

#### Estados e acessibilidade

- Não aplicável à fatia; requisitos existentes são preservados.

#### APIs expostas

- `GET /health` confirma processo ativo sem expor configuração; demais contratos não mudam.

#### APIs externas utilizadas

- Netlify e Render recebem variáveis protegidas; Sentry é opcional.

#### Documentação das APIs consultadas

- Nenhuma documentação externa consultada nesta definição.

#### Eventos e outros contratos

- Log JSON contém timestamp, nível, logger, mensagem e `request_id`, com sanitização.

### 11. Estratégia TDD

- **Unidade**: configuração, sanitização e comandos de backup.
- **Integração/contrato**: hosting, Compose, CI e restauração descartável.
- **BDD/aceite**: AC-001 a AC-003 orientam três testes TDD.
- **Runner TDD**: pytest já adotado no backend.
- **E2E**: smoke test de `/health` quando houver ambiente.
- **Verificação manual**: painéis somente para segredos e domínio opcional.

#### Evidência RED-GREEN-REFACTOR

| IDs | BDD de referência | Teste TDD informado pelo BDD | RED observado | GREEN observado | Refactor/regressão |
| --- | --- | --- | --- | --- | --- |
| US-001, FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003, AC-001 | AC-001 | `test_managed_hosting_contract_is_secure` em `backend/tests/production/test_production_contracts.py` | `docker`/pytest exit 1 em 2026-08-24: ausência de `infra/hosting/production.env.example` | Docker/pytest: passou em 2026-08-24 após T004 | Ruff aprovado; exemplo não contém segredos reais |
| US-001, FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003, AC-002 | AC-002 | `test_insecure_production_configuration_is_rejected` no mesmo arquivo | Docker/pytest exit 1 em 2026-08-24: validador inseguro ainda ausente | Docker/pytest: passou em 2026-08-24 após T004 | Validador exige HTTPS, CORS restrito, sanitização e falha explícita |
| US-001, FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003, AC-003 | AC-003 | `test_recovery_contract_is_reproducible` no mesmo arquivo | Docker/pytest exit 1 em 2026-08-24: backup, restauração e runbook ausentes | Docker/pytest: passou em 2026-08-24 após T006 e T008 | Restauração real ocorreu em banco descartável; runbook incorporou checksum, health e rollback seguro |

### 12. Plano de testes e rastreabilidade

| Requisito | Cenário BDD | Nível | Arquivo/comando esperado | Evidência |
| --- | --- | --- | --- | --- |
| FR-001 a FR-003, NFR-001 a NFR-003 | AC-001 | Contrato | `pytest backend/tests/production/test_production_contracts.py -k managed_hosting` | Passed: 2 testes focais junto de AC-002 |
| FR-001 a FR-003, NFR-001 a NFR-003 | AC-002 | Contrato negativo | `pytest backend/tests/production/test_production_contracts.py -k insecure` | Passed: validador estático e PowerShell exit 0 no exemplo seguro |
| FR-001 a FR-003, NFR-001 a NFR-003 | AC-003 | Integração | `pytest backend/tests/production/test_production_contracts.py -k recovery` | Passed: scripts de backup/restauração e runbook validados; restauração descartável real registrada em T006 |

### 13. Validações

#### Gate do Ato I — Definição

- **Resultado**: Passed em 2026-08-24.
- **Comando**: `node .agents/skills/specsfy-04-validate/scripts/validate_spec.mjs specs/draft/0002-operacao-producao-gerenciada/spec.md`.
- **Achados**: estrutura Specsfy 2.0 válida; topologia, escopo, segurança e recuperação possuem comportamento observável; nenhum blocker aberto.

#### Gate do Ato II — Plano

- **Resultado**: Passed em 2026-08-24.
- **Comando**: `node .agents/skills/specsfy-05-tasks/scripts/validate_tasks.mjs specs/draft/0002-operacao-producao-gerenciada/spec.md`.
- **Achados**: 8 tarefas, 3 predecessores TDD concluídos com RED válido, 10/10 IDs rastreáveis e dependências acíclicas.

#### Gate do Ato III — Entrega

- **Resultado**: Passed em 2026-08-24.
- **Comando**: `node .agents/skills/specsfy-06-tdd-bdd/scripts/check_traceability.mjs specs/in-progress/0002-operacao-producao-gerenciada/spec.md backend/tests/production --full-chain`.
- **Achados**: T001–T008 concluídas; 29 testes backend, Ruff, mypy, lint, TypeScript e exportação estática passaram; os três contratos de produção e 10/10 IDs estão cobertos sem gaps; documentação e monitor de contexto estão atuais.

#### Aceite final

- **Resultado**: READY em 2026-08-24; nenhum `BLOCKER` ou finding P1 aberto para a SPEC-0002.
- **Revisão**: produto, arquitetura e segurança permanecem coerentes com Netlify, Render e restauração isolada; `validate_spec.mjs` e `review_findings.mjs` passaram.
- **Ressalva de repositório atualizada em 2026-08-25**: tarefas e catálogo de skills foram regularizados. A rastreabilidade da SPEC-0002 passou com 10/10 IDs no escopo canônico `backend/tests/production`; o agregador oficial `verify_repo.mjs` ainda produz falso negativo ao varrer também marcadores pertencentes à SPEC-0001. Nenhum script de enforcement ou evidência foi alterado para mascarar essa limitação.

### 14. Tarefas

#### Fase 1 — RED de contratos operacionais

- [x] T001 [TEST] [TDD] [US-001] Derivar AC-001 em `backend/tests/production/test_production_contracts.py` — Refs: US-001, FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003, AC-001 — Depends: none
  - [x] **PREP**: Topologia gerenciada, caminhos e IDs do contrato seguro confirmados.
  - [x] **EXECUTE**: Caso pytest criado com marcador próprio `SPECSFY:`.
  - [x] **VERIFY**: RED observado pela ausência da configuração segura, sem erro de sintaxe ou fixture.
  - [x] **EVIDENCE**: Docker/pytest exit 1; falha em `HOSTING_ENV.is_file()` registrada na seção 11.
  - [x] **IMPROVE**: Teste usa apenas nomes e exemplos públicos, sem depender de segredos reais.

- [x] T002 [TEST] [TDD] [US-001] Derivar AC-002 em `backend/tests/production/test_production_contracts.py` — Refs: US-001, FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003, AC-002 — Depends: none
  - [x] **PREP**: HTTP público, CORS aberto, segredo literal e ausência de falha foram confirmados como entradas inseguras.
  - [x] **EXECUTE**: Caso pytest negativo criado com marcador próprio `SPECSFY:`.
  - [x] **VERIFY**: RED observado porque `validate-production-config.ps1` ainda não existe.
  - [x] **EVIDENCE**: Docker/pytest exit 1; falha em `HOSTING_VALIDATOR.is_file()` registrada na seção 11.
  - [x] **IMPROVE**: As asserções exigem diagnóstico determinístico sem incluir valores secretos.

- [x] T003 [TEST] [TDD] [US-001] Derivar AC-003 em `backend/tests/production/test_production_contracts.py` — Refs: US-001, FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003, AC-003 — Depends: none
  - [x] **PREP**: Backup, restauração isolada, rollback e health check confirmados como artefatos mínimos.
  - [x] **EXECUTE**: Caso pytest criado com marcador próprio `SPECSFY:`.
  - [x] **VERIFY**: RED observado pela ausência de `backup.ps1`, `restore-check.ps1` e `docs/runbook.md`.
  - [x] **EVIDENCE**: Docker/pytest exit 1 e lista exata dos três artefatos ausentes registrada na seção 11.
  - [x] **IMPROVE**: Contrato exige restauração isolada e nunca autoriza alteração do banco de origem.

#### Fase 2 — Operação gerenciada

- [x] T004 [OPS] [US-001] Declarar hosting seguro em `infra/hosting/` — Refs: US-001, FR-001, FR-003, NFR-001, NFR-002, AC-001, AC-002 — Depends: T001, T002, T003
  - [x] **PREP**: Frontend `https://teal-dodol-0d0d22.netlify.app`, backend `https://sistema-gestao-logistica.onrender.com`, CORS restrito ao frontend e callback OAuth no backend confirmados; baseline RED em AC-001/AC-002.
  - [x] **EXECUTE**: `production.env.example` sem segredos e validador PowerShell declarativo criados para Netlify e Render; monitor de contexto `CURRENT`.
  - [x] **VERIFY**: Docker/pytest aprovou AC-001 e AC-002 (`2 passed`); PowerShell aprovou o exemplo; Ruff passou.
  - [x] **EVIDENCE**: `infra/hosting/production.env.example`, `validate-production-config.ps1` e teste focal registrados com US-001, FR-001/FR-003, NFR-001/NFR-002 e AC-001/AC-002.
  - [x] **IMPROVE**: Contrato público foi separado dos segredos e o teste foi isolado em `tests/production/` para evitar mistura de IDs entre specs.

- [x] T005 [OPS] [US-001] Configurar observabilidade em `backend/app/core/logging.py` — Refs: US-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003, AC-001, AC-002 — Depends: T001, T002, T003
  - [x] **PREP**: Eventos HTTP e exceções, cabeçalho `X-Request-ID` e campos `authorization`, `cookie`, `password`, `secret`, `token`, `database_url` e `dsn` confirmados; baseline atual não possui logging estruturado.
  - [x] **EXECUTE**: Logs JSON com correlação `X-Request-ID`, sanitização recursiva e Sentry opcional sem PII implementados.
  - [x] **VERIFY**: Docker/pytest aprovou sanitização e regressão de autenticação (`8 passed`); Ruff e mypy passaram.
  - [x] **EVIDENCE**: `backend/app/core/logging.py`, middleware em `main.py` e `tests/production/test_logging.py` rastreiam US-001, FR-002/FR-003, NFR-001–NFR-003 e AC-001/AC-002.
  - [x] **IMPROVE**: Tracing do Sentry permanece desativado por padrão e o SDK só envia quando `SENTRY_DSN` protegido é configurado.

- [x] T006 [OPS] [US-001] Automatizar backup e restauração em `infra/postgres/` — Refs: US-001, FR-003, NFR-001, NFR-002, NFR-003, AC-002, AC-003 — Depends: T001, T002, T003
  - [x] **PREP**: Retenção padrão de sete backups diários, dump customizado com checksum e restauração obrigatoriamente isolada em URL diferente da origem confirmados.
  - [x] **EXECUTE**: `backup.ps1` e `restore-check.ps1` implementam dump customizado, SHA-256 e destino isolado por variável protegida.
  - [x] **VERIFY**: Snapshot local foi restaurado e consultado em `logistica_restore_t006`; a base descartável foi removida ao final e a origem permaneceu intacta.
  - [x] **EVIDENCE**: Parser PowerShell aprovado; checksum `43bc42db...552547` e consulta `current_database()` confirmaram a restauração sem registrar URLs ou credenciais.
  - [x] **IMPROVE**: Retenção segura de sete dias remove somente `logistica-*.dump*` antigos no diretório de backup informado.

- [x] T007 [OPS] [US-001] Consolidar gates em `.github/workflows/ci.yml` — Refs: US-001, FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003, AC-001, AC-002, AC-003 — Depends: T004, T005, T006
  - [x] **PREP**: Baseline confirmado: backend executa pytest, Ruff e mypy; frontend executava apenas build e ainda precisava incluir lint e tipagem; contratos de produção pertencem à suite pytest e o exemplo seguro possui validador PowerShell próprio.
  - [x] **EXECUTE**: Workflow passou a validar o contrato de hosting, executar pytest, Ruff, mypy, lint, tipagem e build estático com `NETLIFY_STATIC_EXPORT=true`, sem incluir segredos.
  - [x] **VERIFY**: YAML válido; hosting aprovado; 28 testes passaram com o caso de recuperação T008 excluído; Ruff, mypy, lint, TypeScript e exportação estática passaram. O pytest completo bloqueia corretamente AC-003 enquanto `docs/runbook.md` ainda não existe.
  - [x] **EVIDENCE**: `.github/workflows/ci.yml` cobre US-001, FR-001–FR-003, NFR-001–NFR-003 e AC-001–AC-003; comandos Docker locais e o validador PowerShell terminaram com saída zero nos gates aplicáveis à T007.
  - [x] **IMPROVE**: Caches nativos de pip e npm foram preservados com lockfiles explícitos; nenhuma nova regra durável ou mudança narrativa de produto foi necessária.
  <!-- specsfy:evidence {"task":"T007","refs":["US-001","FR-001","FR-002","FR-003","NFR-001","NFR-002","NFR-003","AC-001","AC-002","AC-003"],"files":[".github/workflows/ci.yml"],"commands":[{"run":"pwsh -File infra/hosting/validate-production-config.ps1 -Path infra/hosting/production.env.example","exit":0},{"run":"pytest -k 'not recovery_contract'","exit":0},{"run":"ruff check app tests","exit":0},{"run":"mypy app","exit":0},{"run":"npm run lint && npm run test","exit":0},{"run":"NETLIFY_STATIC_EXPORT=true npm run build","exit":0}]} -->

- [x] T008 [DOC] [US-001] Produzir runbook em `docs/runbook.md` — Refs: US-001, FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003, AC-001, AC-002, AC-003 — Depends: T007
  - [x] **PREP**: Netlify publica `frontend/out`, Render executa a imagem do backend com Alembic antes do Uvicorn, `/health` é o smoke test e os scripts de hosting, backup e restauração isolada foram confirmados; cold start, migração e exposição de segredo são os riscos operacionais principais.
  - [x] **EXECUTE**: `docs/runbook.md` documenta configuração protegida, gates, deploy, rollback, backup, restauração isolada, cold start, health check, incidentes e evidência mínima.
  - [x] **VERIFY**: Os três contratos de produção passaram; a simulação reutiliza a restauração real aprovada em T006 e exige banco descartável diferente da origem, checksum e consulta de leitura antes da remoção.
  - [x] **EVIDENCE**: `pytest tests/production/test_production_contracts.py -q` terminou com `3 passed`; documentator e `--check` passaram; rastreabilidade resultou em 10/10 IDs sem gaps.
  - [x] **IMPROVE**: O aprendizado da simulação foi incorporado ao exigir armazenamento criptografado externo, proibir downgrade impulsivo e condicionar troca de banco a autorização explícita.
  <!-- specsfy:evidence {"task":"T008","refs":["US-001","FR-001","FR-002","FR-003","NFR-001","NFR-002","NFR-003","AC-001","AC-002","AC-003"],"files":["docs/runbook.md"],"commands":[{"run":"pytest tests/production/test_production_contracts.py -q","exit":0},{"run":"node .agents/skills/specsfy-documentator/scripts/build_documentation.mjs --project . --check","exit":0},{"run":"node .agents/skills/specsfy-06-tdd-bdd/scripts/check_traceability.mjs specs/in-progress/0002-operacao-producao-gerenciada/spec.md backend/tests/production --full-chain","exit":0}]} -->

### 15. Ordem de execução

- Caminho crítico: T001/T002/T003 → T004/T005/T006 → T007 → T008.
- Tarefas paralelas: T001–T003; depois T004–T006 em fronteiras distintas.
- Estratégia de MVP: T001–T004 provam hosting seguro; T005–T008 completam operação.

## Ato III — Entregar e validar

### 16. Dependências, riscos e suposições

#### Dependências

- Acesso existente a Netlify e Render para variáveis protegidas.
- Docker e PostgreSQL locais para restauração isolada.

#### Riscos

- Plano gratuito hibernar ou expirar → documentar limites e migração.
- Painéis divergirem do repositório → validador e runbook são o contrato sem valores reais.
- Backup não restaurar → impedir aceite sem restauração descartável.

#### Suposições

- URLs gerenciadas atuais permanecem válidas até domínio personalizado.
- Segredos continuam sendo aplicados manualmente nos painéis quando necessário.

### 17. Decisões

- **DEC-001**: Usar HTTPS de Netlify e Render, sem Traefik, porque não há proxy autogerenciado.
- **DEC-002**: Usar pytest para contratos operacionais, preservando o runner existente.
- **DEC-003**: Exemplos contêm somente nomes e valores não secretos.

### 18. Definition of Done

- [x] `Definition Gate` está `Passed`.
- [x] `Plan Gate` está `Passed`.
- [x] `Delivery Gate` está `Passed`.
- [x] AC-001, AC-002 e AC-003 possuem evidência automatizada.
- [x] Backup foi restaurado sem alterar a origem.
- [x] Testes, lint, tipagem, build e contratos passam.
- [x] `docs/runbook.md` cobre configuração, deploy, rollback e recuperação.
- [x] O painel Specsfy reflete tarefas e gates atuais.
