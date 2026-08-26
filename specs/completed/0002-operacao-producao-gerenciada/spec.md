# Especificação integrada: Operação segura em Netlify e Render

| Campo | Valor |
| --- | --- |
| Formato | Specsfy/2.0 |
| ID | SPEC-0002 |
| Slug | 0002-operacao-producao-gerenciada |
| Status | Complete |
| Effort | 8 |
| Effort updated at | 2026-08-25 |
| Effort rationale | A reabertura inclui correção de cinco achados de segurança em OAuth, sessão, proteção contra força bruta, exposição local do PostgreSQL e acesso administrativo ao BI, com migration e regressão completa. |
| ClickUp Task | Não vinculada |
| Milestones | Produção observável |
| Definition Gate | Passed |
| Plan Gate | Passed |
| Delivery Gate | Passed |
| Evidence Contract | 1 |
| Interface para pessoas | Não — a fatia altera somente configuração operacional, automação e documentação. |
| Atualizada em | 2026-08-26 |

## Ato I — Definir

### 1. Problema e resultado

#### Problema

O MVP LogiSync funciona com frontend no Netlify, API e PostgreSQL no Render, mas a revisão de segurança encontrou cinco limites ainda incompletos: correlação OAuth não vinculada ao navegador, JWT em URL, login sem bloqueio progressivo, PostgreSQL local publicado com senha padrão e BI administrativo sem fronteira explícita de exposição.

#### Resultado desejado

A operação gerenciada deve ser reproduzível, segura e recuperável, com autenticação resistente a login CSRF, vazamento de token e força bruta, e com banco/BI acessíveis somente pela fronteira administrativa local declarada.

#### Métricas de sucesso

- 100% dos contratos operacionais desta fatia validados no CI.
- Restauração de backup validada em banco descartável.
- Nenhum segredo persistido no Git ou emitido em logs.
- Runbook suficiente para deploy, rollback e recuperação.
- Nenhum JWT aparece em query string ou cabeçalho `Location`.
- Estado OAuth de outro navegador é rejeitado e códigos de troca são curtos, expiráveis e de uso único.
- Cinco falhas consecutivas de senha bloqueiam temporariamente a conta sem revelar se o e-mail existe.
- PostgreSQL e Metabase do Compose escutam somente em loopback e exigem segredos fornecidos externamente.

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
- Correlação OAuth por cookie protegido, código de sessão de uso único e bloqueio temporário de login.
- Migration Alembic e testes para os estados persistentes de autenticação.
- Endurecimento do Compose e definição do Metabase como ferramenta administrativa local, não tenant-facing.

#### Fora de escopo

- VPS, Kubernetes, Docker Swarm ou Traefik.
- Compra de domínio ou plano pago.
- Redesenho visual do MVP ou painel de BI multi-tenant voltado a clientes.

#### Atores

- **Responsável operacional**: publica versões, acompanha falhas e executa recuperação.
- **Pessoa usuária**: espera acesso HTTPS estável e preservação de dados.
- **Pipeline CI**: bloqueia violações dos contratos da entrega.
- **Administrador técnico local**: acessa PostgreSQL e Metabase apenas pelo loopback da máquina autorizada.

### 4. Princípios e restrições do projeto

- **PR-001**: Segredos entram somente por variáveis protegidas e nunca pelo Git.
- **PR-002**: Netlify hospeda frontend e Render hospeda API e PostgreSQL.
- **PR-003**: Backup só é válido após restauração isolada.
- **PR-004**: Logs não registram tokens, senhas, cookies ou URLs completas de banco.
- **PR-005**: Segredos de autenticação nunca transitam em URLs e dados temporários são armazenados somente como hash quando persistidos.
- **PR-006**: Serviços administrativos locais escutam em loopback; exposição remota exige uma nova decisão de arquitetura e controle de acesso por tenant.

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

#### AC-004 — OAuth vinculado ao navegador e sem JWT em URL

**Cobre**: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004

```gherkin
@US-001 @FR-001 @FR-002 @FR-003 @FR-004 @NFR-001 @NFR-002 @NFR-003 @NFR-004 @AC-004
Feature: Autenticação OAuth protegida
  Scenario: concluir OAuth somente no navegador iniciador
    Given um navegador iniciou o login Google e recebeu a correlação protegida
    When o callback apresenta o estado correto e a identidade autorizada
    Then o backend redireciona com um código de uso único sem incluir JWT na URL
```

#### AC-005 — Tentativas de senha limitadas

**Cobre**: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004

```gherkin
@US-001 @FR-001 @FR-002 @FR-003 @FR-004 @NFR-001 @NFR-002 @NFR-003 @NFR-004 @AC-005
Feature: Proteção da autenticação por senha
  Scenario: bloquear temporariamente credenciais repetidamente inválidas
    Given uma conta ativa sem bloqueio
    When cinco senhas inválidas consecutivas são apresentadas
    Then novas tentativas recebem limite temporário e uma autenticação válida volta a funcionar após o prazo
```

#### AC-006 — Banco e BI administrativos restritos ao host local

**Cobre**: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004

```gherkin
@US-001 @FR-001 @FR-002 @FR-003 @FR-004 @NFR-001 @NFR-002 @NFR-003 @NFR-004 @AC-006
Feature: Fronteira administrativa local
  Scenario: validar serviços administrativos do Compose
    Given o ambiente local recebe senhas por variáveis protegidas
    When o contrato do Compose é inspecionado
    Then PostgreSQL e Metabase escutam somente em loopback e nenhuma credencial padrão conhecida é aceita
```

### 7. Requisitos

#### Funcionais

- **FR-001**: O repositório deve declarar URLs HTTPS, URL do frontend, CORS e callback OAuth coerentes com Netlify e Render.
- **FR-002**: A API deve produzir logs estruturados e permitir Sentry opcional sem registrar dados sensíveis.
- **FR-003**: A operação deve gerar e restaurar backup isolado, executar todos os gates no CI e documentar deploy, rollback e incidentes.
- **FR-004**: A autenticação deve vincular o OAuth ao navegador iniciador, trocar um código curto de uso único por JWT fora da URL, limitar falhas consecutivas de senha e manter PostgreSQL/Metabase administrativos restritos ao loopback com credenciais obrigatórias.

#### Não funcionais

- **NFR-001**: Toda URL pública declarada usa HTTPS e nenhum segredo real fica versionado. **Verificação**: teste estático.
- **NFR-002**: Cada falha de contrato indica arquivo e correção esperada. **Verificação**: cenários negativos.
- **NFR-003**: Backup é restaurável sem destruir a origem e logs correlacionam requisições. **Verificação**: restauração descartável e teste de logging.
- **NFR-004**: Dados temporários de autenticação expiram, não são reutilizáveis e persistem somente como hash; a migration correspondente possui upgrade/downgrade testados. **Verificação**: testes de API, migration e contratos estáticos.

#### Erros e casos-limite

- Integração opcional ausente → serviço inicia com integração desativada.
- HTTP público ou origem ampla em produção → gate falha.
- Backup vazio ou corrompido → restauração falha sem tocar a origem.
- Instância gratuita hibernada → runbook comunica cold start e health check.
- Callback com estado válido de outro navegador → `401` e nenhuma sessão emitida.
- Código de troca ausente, expirado ou reutilizado → `401` genérico sem JWT.
- Quinta senha inválida consecutiva → bloqueio temporário e resposta `429` com `Retry-After`.
- Variável `POSTGRES_PASSWORD` ausente → Compose falha antes de iniciar os serviços.

## Ato II — Projetar e provar

### 8. Plano técnico

#### Contexto existente

- Next.js estático no Netlify, FastAPI e PostgreSQL no Render e Compose local.

#### Arquitetura e módulos

- `infra/hosting/` concentra exemplos e validação gerenciada; `backend/app/core/logging.py` concentra logging; `infra/postgres/` contém backup/restauração; CI reúne os gates.

#### Migrations

- Criar migration Alembic para `oauth_exchange_codes` e `auth_login_throttles`; armazenar somente hashes SHA-256 dos códigos, identidades normalizadas e origens de rede, com expiração/consumo.

#### Models

- `AuthLoginThrottle` mantém escopo, hash da chave, janela, contador e bloqueio; `OAuthExchangeCode` mantém hash único, usuário, expiração, consumo e criação.

#### Controllers e casos de uso

- `GET /api/v1/auth/google` grava correlação HttpOnly/SameSite=Lax; callback exige igualdade em tempo constante, elimina a correlação e redireciona apenas com código opaco curto.
- `POST /api/v1/auth/exchange` consome o código de uso único em transação e retorna o JWT no corpo JSON.
- `POST /api/v1/auth/token` aplica limites persistentes combinados por identidade normalizada e origem de rede, bloqueia temporariamente após o limiar e usa derivação PBKDF2 equivalente para e-mail inexistente.

#### Views e experiência

- Não aplicável; a interface publicada não muda.

#### Queries e repositórios

- Consultas de autenticação bloqueiam a linha afetada durante atualização de contador e consumo do código; ferramentas PostgreSQL continuam operando backup sem acessar esses valores.

#### Jobs e processamento assíncrono

- Agendamento fica documentado; ativação externa exige credencial protegida.

#### Estrutura de arquivos

```text
infra/hosting/production.env.example
infra/hosting/validate-production-config.ps1
infra/postgres/backup.ps1
infra/postgres/restore-check.ps1
backend/app/core/logging.py
backend/app/core/security.py
backend/app/auth.py
backend/app/models.py
backend/app/api.py
backend/alembic/versions/20260825_0011_auth_hardening.py
frontend/components/operations-dashboard.tsx
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
| Código de troca OAuth | hash SHA-256 | expiração curta, consumo único | pertence ao usuário autorizado |
| Estado de bloqueio | escopo + hash da chave | janela, falhas consecutivas e `blocked_until` | protege identidade e origem sem guardar e-mail ou IP em claro |

#### Estados e transições

| Entidade | Estado atual | Evento | Próximo estado | Invariantes |
| --- | --- | --- | --- | --- |
| Backup | gerado | restauração isolada aprovada | validado | origem não é alterada |
| Deploy | candidato | gates aprovados | publicável | todos os checks passam |
| Deploy | candidato | gate falha | bloqueado | diagnóstico identifica a falha |
| Código OAuth | emitido | troca válida | consumido | hash único, não reutilizável e não contém JWT |
| Conta | ativa | quinta falha consecutiva | bloqueada temporariamente | sucesso posterior ao prazo zera o contador |

#### Migração e retenção

- Migration Alembic adiciona os estados de autenticação com downgrade explícito. Códigos OAuth expiram em até dois minutos e registros expirados podem ser removidos operacionalmente; retenção de backup permanece sete diários e quatro semanais.

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

- `GET /health` confirma processo ativo sem expor configuração; `POST /api/v1/auth/exchange` troca uma autorização efêmera por JWT e rejeita ausência, expiração e reuso com resposta genérica.

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
| US-001, FR-001–FR-004, NFR-001–NFR-004, AC-004 | AC-004 | testes de OAuth, frontend e migration em `backend/tests/test_auth_hardening.py` e `backend/tests/test_auth_hardening_migration.py` | RED em 2026-08-25: cookie ausente, estado aceito em outro navegador, endpoint de troca 404, frontend lê JWT da query e migration inexiste; RED adicional em 2026-08-26 confirmou rollback da limpeza em troca inválida | GREEN em 2026-08-26: correlação por cookie, código opaco de uso único, limpeza confirmada inclusive no caminho 401 e migration aprovada | Replay, navegador distinto, expiração, limpeza e ausência de texto claro cobertos |
| US-001, FR-001–FR-004, NFR-001–NFR-004, AC-005 | AC-005 | testes de bloqueio e migration nos mesmos arquivos | RED em 2026-08-25: quinta/sexta falhas retornam 401, origem não é limitada, e-mail inexistente pula derivação e migration inexiste; RED adicional em 2026-08-26 confirmou negação de login correto por origem compartilhada | GREEN em 2026-08-26: identidade e peer de rede são limitados, senha correta atravessa apenas o bloqueio compartilhado e `X-Forwarded-For` não altera a origem | Identidade, origem, NAT compartilhado, spoof de proxy e enumeração temporal cobertos |
| US-001, FR-001–FR-004, NFR-001–NFR-004, AC-006 | AC-006 | contratos em `backend/tests/production/test_security_hardening_contracts.py` | RED em 2026-08-25: senha padrão e publicação sem loopback permanecem; runbook não declara BI administrativo | GREEN em 2026-08-26: contratos, Compose, papéis PostgreSQL e smoke test real aprovados | Bind amplo rejeitado, serviços de domínio usam `logistica_app` sem privilégios administrativos e BI permanece local |

### 12. Plano de testes e rastreabilidade

| Requisito | Cenário BDD | Nível | Arquivo/comando esperado | Evidência |
| --- | --- | --- | --- | --- |
| FR-001 a FR-003, NFR-001 a NFR-003 | AC-001 | Contrato | `pytest backend/tests/production/test_production_contracts.py -k managed_hosting` | Passed: 2 testes focais junto de AC-002 |
| FR-001 a FR-003, NFR-001 a NFR-003 | AC-002 | Contrato negativo | `pytest backend/tests/production/test_production_contracts.py -k insecure` | Passed: validador estático e PowerShell exit 0 no exemplo seguro |
| FR-001 a FR-003, NFR-001 a NFR-003 | AC-003 | Integração | `pytest backend/tests/production/test_production_contracts.py -k recovery` | Passed: scripts de backup/restauração e runbook validados; restauração descartável real registrada em T006 |
| FR-001 a FR-004, NFR-001 a NFR-004 | AC-004 | API e persistência | `pytest backend/tests/test_auth_hardening.py -k oauth` | Passed: navegador distinto, troca única, replay, limpeza em sucesso/erro e frontend sem JWT na URL |
| FR-001 a FR-004, NFR-001 a NFR-004 | AC-005 | API e persistência | `pytest backend/tests/test_auth_hardening.py -k login` | Passed: identidade, origem, credencial correta após abuso compartilhado, recuperação e PBKDF2 equivalente |
| FR-001 a FR-004, NFR-001 a NFR-004 | AC-006 | Contrato e migration | `pytest backend/tests/production/test_security_hardening_contracts.py backend/tests/test_auth_hardening_migration.py` | Passed: 7 testes de contrato/migration e smoke PostgreSQL/API real |

### 13. Validações

#### Gate do Ato I — Definição

- **Resultado**: Passed após reabertura de segurança em 2026-08-25.
- **Comando**: `validate_spec.mjs --allow-draft`, revisão semântica PROD/ARCH/SEC e `review_findings.mjs`.
- **Achados**: estrutura válida; US-001, FR-001–FR-004 e NFR-001–NFR-004 possuem ao menos seis AC distintos; os cinco achados são implementáveis sem decisão material pendente e permanecem abertos como trabalho T009–T016.

- **FIND-SEC-001** [P2] [Resolved] Estado OAuth vinculado ao navegador por cookie HttpOnly/SameSite e comparação constante antes do provedor — Refs: FR-004, NFR-004 — Evidence: backend/app/api.py — Effect: login CSRF não atravessa navegador distinto — Suggestion: manter o teste de correlação no gate de autenticação.
- **FIND-SEC-002** [P2] [Resolved] JWT removido da URL; redirect contém somente código opaco de dois minutos, hash-only e uso único, trocado por POST — Refs: FR-004, NFR-004 — Evidence: frontend/components/operations-dashboard.tsx — Effect: bearer reutilizável não transita em query, histórico ou referrer — Suggestion: manter replay, expiração e limpeza na regressão.
- **FIND-SEC-003** [P2] [Resolved] Login limitado por identidade e peer de rede, sem confiar em `X-Forwarded-For`; senha correta permanece funcional atrás de origem compartilhada — Refs: FR-004, NFR-004 — Evidence: backend/app/auth.py — Effect: spraying é limitado sem negar credencial correta por bloqueio compartilhado — Suggestion: manter o smoke de cabeçalhos falsificados e login legítimo.
- **FIND-SEC-004** [P2] [Resolved] PostgreSQL exige senha externa, publica somente em loopback e serviços usam papel `logistica_app` sem privilégios administrativos — Refs: FR-004, NFR-001 — Evidence: docker-compose.yml — Effect: acesso local não reutiliza superusuário nem expõe a porta à rede — Suggestion: manter o smoke de migration e ownership em banco descartável.
- **FIND-SEC-005** [P2] [Resolved] Metabase é ferramenta administrativa local em loopback; qualquer BI tenant-facing exige nova spec e isolamento próprio — Refs: FR-004, NFR-001 — Evidence: docs/runbook.md — Effect: a view global não é exposta como produto multi-tenant — Suggestion: exigir isolamento por organização antes de qualquer publicação tenant-facing.
- **Comando**: `node .agents/skills/specsfy-04-validate/scripts/validate_spec.mjs specs/draft/0002-operacao-producao-gerenciada/spec.md`.
- **Achados**: estrutura Specsfy 2.0 válida; topologia, escopo, segurança e recuperação possuem comportamento observável; nenhum blocker aberto.

#### Gate do Ato II — Plano

- **Resultado**: Passed em 2026-08-25 após validação das tarefas T009–T016 e observação RED reproduzível.
- **Comando**: `node .agents/skills/specsfy-05-tasks/scripts/validate_tasks.mjs specs/defined/0002-operacao-producao-gerenciada/spec.md --root . --allow-draft`.
- **Achados**: 16 tarefas totais, 11 concluídas, 6 TDD, 15/15 IDs rastreáveis e dependências acíclicas; T009–T011 registram 12 falhas esperadas antes da implementação.

#### Gate do Ato III — Entrega

- **Resultado**: Passed localmente em 2026-08-26 para AC-001–AC-006; publicação continua sendo uma ação externa separada.
- **Comandos**: `pytest -q`; Ruff; mypy; lint; TypeScript; build estático Netlify; `docker compose config --quiet`; builds das imagens; documentator/monitor; smoke PostgreSQL/API.
- **Achados**: 64 testes backend passaram; Ruff e mypy passaram; lint, TypeScript e build estático com nove rotas passaram; migration `20260825_0011`, owner `logistica_app`, `/health`, proteção contra spoof e login legítimo foram provados em contêineres descartáveis.

#### Aceite final

- **Resultado**: READY para revisão e publicação em 2026-08-26; nenhum deploy de produção foi executado nesta validação.
- **Revisão**: os cinco achados originais e as três regressões encontradas pela revisão independente foram corrigidos; comportamento malicioso deixou de reproduzir e login/OAuth legítimos permaneceram funcionais.
- **Ressalva de repositório atualizada em 2026-08-25**: tarefas e catálogo de skills foram regularizados. A rastreabilidade da SPEC-0002 passou com 10/10 IDs no escopo canônico `backend/tests/production`; o agregador oficial `verify_repo.mjs` ainda produz falso negativo ao varrer também marcadores pertencentes à SPEC-0001. Nenhum script de enforcement ou evidência foi alterado para mascarar essa limitação.
- **Ressalva de enforcement em 2026-08-26**: a validação direta da SPEC-0002 passou com 15/15 IDs, 16/16 tarefas e evidência estrita. O agregador global continua `FAILED` por duas pendências históricas/estruturais fora desta entrega: o scanner de rastreabilidade retorna zero arquivos em subpastas no Windows e a SPEC-0001 concluída antecede o contrato atual de research. O bug Windows do verificador de evidência foi corrigido sem afrouxar a fronteira de caminhos.

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

#### Fase 3 — RED TDD informado pelo BDD de segurança

- [x] T009 [TEST] [TDD] [US-001] Derivar AC-004 em `backend/tests/test_auth_hardening.py` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-004 — Depends: none
  - [x] **PREP**: Login CSRF, JWT em URL e fluxo OAuth legítimo confirmados no callback e no frontend atuais.
  - [x] **EXECUTE**: Casos criados com clientes distintos, cookie protegido, endpoint de troca, frontend e migration, cada um com marcador próprio `SPECSFY:`.
  - [x] **VERIFY**: RED válido: estado de outro navegador retornou 307, cookie inexiste, troca retorna 404 e o frontend ainda lê `access_token`.
  - [x] **EVIDENCE**: Docker/pytest focal terminou com falhas de comportamento esperadas em AC-004.
  - [x] **IMPROVE**: Replay, expiração estrutural e ausência de código em texto claro foram incorporados aos oráculos.

- [x] T010 [TEST] [TDD] [US-001] Derivar AC-005 em `backend/tests/test_auth_hardening.py` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-005 — Depends: none
  - [x] **PREP**: Limites por identidade/origem, resposta uniforme e autenticação legítima posterior confirmados como invariantes.
  - [x] **EXECUTE**: Casos criados para cinco falhas, múltiplas identidades na mesma origem, e-mail inexistente e schema hash-only.
  - [x] **VERIFY**: RED válido: quinta/sexta tentativas retornaram 401, origem não bloqueou e e-mail inexistente não executou verificação equivalente.
  - [x] **EVIDENCE**: Docker/pytest focal registrou as falhas esperadas em AC-005.
  - [x] **IMPROVE**: O oráculo de e-mail inexistente mede diretamente a derivação equivalente sem depender de timing instável.

- [x] T011 [TEST] [TDD] [US-001] Derivar AC-006 em `backend/tests/production/test_security_hardening_contracts.py` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-006 — Depends: none
  - [x] **PREP**: Uso local do DBeaver/Metabase e ausência deles na topologia gerenciada confirmados nas fontes normativas.
  - [x] **EXECUTE**: Contratos criados para senha obrigatória, bind loopback e BI administrativo, cada um com marcador próprio `SPECSFY:`.
  - [x] **VERIFY**: RED válido: fallback conhecido e publicação ampla foram encontrados, e o runbook não continha a fronteira nova.
  - [x] **EVIDENCE**: Docker/pytest focal registrou três falhas esperadas em AC-006.
  - [x] **IMPROVE**: Cenário negativo rejeita bind amplo independentemente da força da senha.

#### Fase 4 — Hardening de autenticação e fronteiras administrativas

- [x] T012 [CODE] [US-001] Versionar estados de autenticação em `backend/app/models.py` e `backend/alembic/versions/20260825_0011_auth_hardening.py` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-004, AC-005, AC-006 — Depends: T009, T010, T011
  - [x] **PREP**: Confirmar RED, constraints, índices, hashes, expiração e downgrade.
  - [x] **EXECUTE**: Adicionar models e migration sem persistir código, e-mail ou IP em texto claro; documentação consolidada em T016.
  - [x] **VERIFY**: Aprovar migration, models e regressão de banco.
  - [x] **EVIDENCE**: `pytest tests/test_auth_hardening_migration.py -q` aprovou 2 testes; Ruff apontou somente ordenação de imports, corrigida em seguida.
  - [x] **IMPROVE**: Índices de expiração/bloqueio suportam limpeza futura; consumo concorrente será fechado no endpoint de troca em T013.
  - Evidência: `backend/app/models.py`; `backend/alembic/versions/20260825_0011_auth_hardening.py`; migration `20260825_0011` encadeada a `20260821_0010`.
  <!-- specsfy:evidence {"task":"T012","refs":["US-001","FR-001","FR-002","FR-003","FR-004","NFR-001","NFR-002","NFR-003","NFR-004","AC-004","AC-005","AC-006"],"files":["backend/app/models.py","backend/alembic/versions/20260825_0011_auth_hardening.py"],"commands":[{"run":"pytest tests/test_auth_hardening_migration.py -q","exit":0},{"run":"ruff check app tests","exit":0}]} -->

- [x] T013 [CODE] [US-001] Proteger OAuth e retirar JWT da URL em `backend/app/api.py` e `frontend/components/operations-dashboard.tsx` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-004, AC-005, AC-006 — Depends: T009, T010, T011, T012
  - [x] **PREP**: Confirmar correlação HttpOnly, expiração, troca única e compatibilidade Netlify/Render.
  - [x] **EXECUTE**: Implementar cookie, código hash, endpoint de troca e consumo após limpar a URL; documentação consolidada em T016.
  - [x] **VERIFY**: Aprovar outro navegador, reuso, expiração, fluxo legítimo, lint e TypeScript no gate final.
  - [x] **EVIDENCE**: 5 testes focais de OAuth/frontend passaram; Ruff corrigiu e aprovou a ordenação mecânica dos imports.
  - [x] **IMPROVE**: `netlify.toml` define `Referrer-Policy: no-referrer` como defesa adicional.
  - Evidência: cookie `oauth_correlation` HttpOnly/SameSite, redirect com `auth_code`, `POST /api/v1/auth/exchange`, código hash de dois minutos e consumo transacional de uso único.
  <!-- specsfy:evidence {"task":"T013","refs":["US-001","FR-001","FR-002","FR-003","FR-004","NFR-001","NFR-002","NFR-003","NFR-004","AC-004","AC-005","AC-006"],"files":["backend/app/api.py","frontend/components/operations-dashboard.tsx","netlify.toml"],"commands":[{"run":"pytest tests/test_auth_hardening.py -q","exit":0},{"run":"npm run lint && npm run test","exit":0},{"run":"NETLIFY_STATIC_EXPORT=true npm run build","exit":0}]} -->

- [x] T014 [CODE] [US-001] Limitar falhas por identidade e origem em `backend/app/auth.py` e `backend/app/api.py` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-004, AC-005, AC-006 — Depends: T009, T010, T011, T012
  - [x] **PREP**: Confirmar limiar, janela, mensagem genérica, PBKDF2 equivalente e reset seguro.
  - [x] **EXECUTE**: Implementar buckets persistentes, bloqueio temporário e `Retry-After`; documentação consolidada em T016.
  - [x] **VERIFY**: Aprovar identidade, origem, e-mail inexistente, expiração e sucesso normal.
  - [x] **EVIDENCE**: 3 cenários principais e o cenário isolado de recuperação passaram; Ruff aprovou após ordenação mecânica de imports.
  - [x] **IMPROVE**: Sucesso limpa apenas o bucket da identidade e nunca zera o bucket compartilhado da origem.
  - Evidência: limiar de cinco falhas em 15 minutos, `Retry-After`, chaves HMAC sem e-mail/IP em claro e PBKDF2 equivalente para identidade inexistente.
  <!-- specsfy:evidence {"task":"T014","refs":["US-001","FR-001","FR-002","FR-003","FR-004","NFR-001","NFR-002","NFR-003","NFR-004","AC-004","AC-005","AC-006"],"files":["backend/app/auth.py","backend/app/api.py","backend/Dockerfile"],"commands":[{"run":"pytest tests/test_auth_hardening.py tests/production/test_security_hardening_contracts.py -q","exit":0},{"run":"ruff check app tests","exit":0},{"run":"mypy app","exit":0}]} -->

- [x] T015 [OPS] [US-001] Restringir PostgreSQL e Metabase em `docker-compose.yml` e no runbook — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-006 — Depends: T011
  - [x] **PREP**: Confirmar que BI é ferramenta administrativa local e não interface tenant-facing.
  - [x] **EXECUTE**: Exigir senha do PostgreSQL, publicar PostgreSQL/Metabase somente em `127.0.0.1` e documentar a fronteira.
  - [x] **VERIFY**: Aprovar contratos positivos/negativos e `docker compose config` com variáveis de teste.
  - [x] **EVIDENCE**: 3 contratos AC-006 passaram e `docker compose config --quiet` aprovou sem revelar valores.
  - [x] **IMPROVE**: Runbook exige nova spec com credenciais por organização, isolamento no banco e testes cruzados antes de BI tenant-facing.
  - Evidência: senha PostgreSQL sem fallback, binds loopback, Metabase apenas na rede interna e `DATABASE_URL` obrigatória na aplicação.

- [x] T016 [DOC] [US-001] Atualizar `.specsfy/DATABASE.md`, `docs/` e `PROJECT.md` — Refs: US-001, FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004, AC-004, AC-005, AC-006 — Depends: T013, T014, T015
  - [x] **PREP**: Fontes executáveis, schema, papéis PostgreSQL, autenticação e decisões implementadas conferidos.
  - [x] **EXECUTE**: Documentação técnica reconstruída; PROJECT e inventário de banco registram OAuth opaco, throttle hash-only, limpeza e fronteiras administrativas.
  - [x] **VERIFY**: Documentator `--check` e monitor de contexto terminaram `CURRENT`.
  - [x] **EVIDENCE**: `.specsfy/DATABASE.md`, `PROJECT.md`, `docs/application.md`, `docs/database.md`, `docs/flows.md` e `docs/runbook.md`; build documental e monitor com saída zero.
  - [x] **IMPROVE**: Orientação de proxy wildcard foi removida; serviços administrativos permanecem locais e a documentação proíbe BI tenant-facing sem nova spec.
  <!-- specsfy:evidence {"task":"T016","refs":["US-001","FR-001","FR-002","FR-003","FR-004","NFR-001","NFR-002","NFR-003","NFR-004","AC-004","AC-005","AC-006"],"files":[".specsfy/DATABASE.md","PROJECT.md","docs/application.md","docs/database.md","docs/flows.md","docs/runbook.md"],"commands":[{"run":"pytest -q","exit":0},{"run":"ruff check app tests","exit":0},{"run":"mypy app","exit":0},{"run":"npm run lint && npm run test","exit":0},{"run":"NETLIFY_STATIC_EXPORT=true npm run build","exit":0},{"run":"node .agents/skills/specsfy-documentator/scripts/build_documentation.mjs --project . --check","exit":0},{"run":"node .agents/skills/specsfy-setup/scripts/monitor_context.mjs --project . --paths <arquivos-alterados> --check","exit":0}]} -->

### 15. Ordem de execução

- Caminho crítico histórico: T001/T002/T003 → T004/T005/T006 → T007 → T008.
- Caminho crítico da reabertura: T009/T010 → T012 → T013/T014; T011 → T015; T013/T014/T015 → T016.
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
- **DEC-004**: Em 2026-08-25, reabrir a spec desde o Ato I porque os achados alteram segurança, persistência e contratos públicos de autenticação.
- **DEC-005**: Entregar OAuth por código opaco de uso único armazenado como hash; JWT continua retornado no corpo JSON e nunca em URL.
- **DEC-006**: Tratar Metabase como ferramenta administrativa local; dashboards tenant-facing futuros exigem nova spec e isolamento no banco.
- **DEC-007**: Não confiar em cabeçalhos de proxy no runtime; o throttle usa o peer de rede e permite credencial correta quando apenas a origem compartilhada está bloqueada.

### 18. Definition of Done

- [x] `Definition Gate` está `Passed` para a versão reaberta.
- [x] `Plan Gate` está `Passed` para T009–T016.
- [x] `Delivery Gate` está `Passed` para AC-004–AC-006.
- [x] AC-001, AC-002 e AC-003 possuem evidência automatizada.
- [x] Backup foi restaurado sem alterar a origem.
- [x] Testes, lint, tipagem, build, migration e contratos passam após o hardening.
- [x] `.specsfy/DATABASE.md` reflete `oauth_exchange_codes` e `auth_login_throttles` sem valores sensíveis.
- [x] `docs/runbook.md` cobre configuração, deploy, rollback e recuperação.
- [x] O painel Specsfy reflete tarefas e gates atuais.
