# Especificação integrada: Gestão logística e controle operacional

| Campo | Valor |
| --- | --- |
| Formato | Specsfy/2.0 |
| ID | SPEC-0001 |
| Slug | 0001-gestao-logistica |
| Status | Complete |
| Effort | 9 |
| Effort updated at | 2026-08-24 |
| Effort rationale | MVP full-stack histórico já implementado; a operação de produção foi extraída para SPEC-0002 para adotar evidência Specsfy 2.0 sem fabricar TDD retroativo. |
| ClickUp Task | Não vinculada |
| Milestones | MVP operacional; Produção observável |
| Definition Gate | Passed |
| Plan Gate | Passed |
| Delivery Gate | Passed |
| Evidence Contract | 1 |
| Interface para pessoas | Sim — web app responsivo LogiSync |
| Atualizada em | 2026-08-25 |

## Ato I — Definir

### 1. Problema e resultado

#### Problema

Operadores e gestores precisam controlar veículos, quilometragem, receitas, despesas e manutenção sem perder a separação por organização nem subestimar o custo real da operação.

#### Resultado desejado

O LogiSync entrega uma plataforma web auditável para registrar a operação, calcular o lucro líquido real por veículo e período, antecipar manutenção e integrar dados externos pela API.

#### Métricas de sucesso

- Uma operação diária é registrada em até 2 minutos.
- O lucro líquido real fica disponível para qualquer veículo e período com dados cadastrados.
- Alertas críticos chegam ao n8n em até 1 minuto após a identificação.
- Reenvios com a mesma chave de idempotência não duplicam dados.

### 2. Research e esclarecimentos

#### Researchs executados

- **R-001** [critical] A planilha Google autorizada é utilizável como fonte mestre somente leitura — Verdict: verified — Confidence: high — Evidence: histórico consolidado nesta especificação e testes do sincronizador — Budget: 1/1.
- **R-002** [critical] PostgreSQL com views e papel de BI atende leitura isolada do Metabase — Verdict: verified — Confidence: high — Evidence: `backend/tests/test_bi_migration.py` e `infra/postgres/init-bi.sh` — Budget: 1/1.

#### Fontes e contexto consultados

- Código em `backend/`, `frontend/`, `infra/`, `docker-compose.yml` e documentação em `docs/`.
- Especificação, plano e tarefas legados de `specs/001-gestao-logistica/`, consolidados nesta fonte normativa.

#### Documentação consultada

- Contratos OpenAPI gerados pelo FastAPI e configuração local do Docker Compose.
- Specsfy 2.0 em `.specsfy/Spec.md` e templates oficiais em `.specsfy/templates/`.

#### Artefatos de pesquisa armazenados

- Nenhum artefato externo copiado; as conclusões normativas estão registradas neste `spec.md`.

#### Dúvidas respondidas

- **Q**: Qual banco é a fonte de verdade? → **A**: PostgreSQL; DBeaver serve somente para inspeção.
- **Q**: O n8n pode escrever nas tabelas? → **A**: Não; toda integração passa pela API autenticada.
- **Q**: Como publicar o frontend? → **A**: Exportação estática no Netlify e `standalone` no contêiner Docker.

#### Dúvidas abertas

- Critério padrão de rateio de custos fixos: por km, por dia ou configurável por despesa.
- Domínio e DNS definitivos, destino de backups criptografados e DSN do Sentry.

### 3. Escopo e atores

#### Incluído

- Organizações, usuários e papéis; veículos; operações; receitas; despesas; rentabilidade; manutenção; alertas; catálogo técnico; integrações; BI e web app responsivo.

#### Fora de escopo

- Roteirização, GPS em tempo real, emissão fiscal, conciliação bancária, aplicativo móvel nativo e previsão de falhas por aprendizado de máquina.

#### Atores

- **Operador**: registra operações e dados cotidianos autorizados.
- **Gestor**: analisa rentabilidade, custos e manutenção da própria organização.
- **Administrador**: cadastra a organização, usuários, veículos, catálogo e integrações.
- **n8n**: consome eventos assinados e chama somente endpoints autenticados.
- **Metabase**: consulta exclusivamente views concedidas ao papel de BI.

### 4. Princípios e restrições do projeto

- **PR-001**: Valores financeiros usam `Decimal` e `NUMERIC`; `float` é proibido.
- **PR-002**: Toda mudança de schema usa migration Alembic e teste.
- **PR-003**: O tenant vem do JWT, nunca de parâmetros enviados pelo cliente.
- **PR-004**: Eventos externos usam idempotência, assinatura HMAC e retentativa controlada.
- **PR-005**: n8n não recebe escrita direta nas tabelas de domínio.
- **PR-006**: Segredos e dados reais não entram no Git.

### 5. Histórias de usuário

#### US-001 — Registrar operação diária (P1)

Como operador, quero registrar quilometragem e faturamento de um veículo para acompanhar o resultado diário. **Teste independente**: registrar uma operação válida e consultar o resumo do dia. **Requisitos**: FR-004, FR-005, FR-015.

#### US-002 — Apurar lucro líquido real (P1)

Como gestor, quero consultar rentabilidade por veículo e período para decidir com base no custo total. **Teste independente**: cadastrar receita, combustível e manutenção e consultar o demonstrativo. **Requisitos**: FR-006, FR-007, FR-008, FR-013, FR-014.

#### US-003 — Controlar manutenção e alertas (P1)

Como gestor, quero cadastrar regras e receber alertas de manutenção para evitar indisponibilidade. **Teste independente**: criar regra por km, atingir o limite e confirmar o alerta. **Requisitos**: FR-009, FR-010, FR-011, FR-012.

#### US-004 — Administrar veículos e dados técnicos (P1)

Como administrador, quero manter veículos e especificações para calcular consumo e manutenção corretamente. **Teste independente**: cadastrar e consultar veículos de diferentes categorias e energias. **Requisitos**: FR-002, FR-003, FR-020.

#### US-005 — Importar dados por automação (P2)

Como administrador, quero sincronizar dados técnicos e preços pela API para reduzir cadastro manual com origem e auditoria. **Teste independente**: sincronizar a planilha autorizada e consultar carros, motos, caminhões e ônibus. **Requisitos**: FR-012, FR-018, FR-019, FR-020.

#### US-006 — Visualizar indicadores gerenciais (P2)

Como gestor, quero filtros por veículo, categoria e período para analisar KM, receitas, custos, lucro e alertas. **Teste independente**: consultar o mesmo painel em 360 px e desktop. **Requisitos**: FR-014, FR-016.

#### US-007 — Criar organização e acessar a plataforma (P1)

Como responsável por uma nova operação, quero cadastrar empresa e acesso para começar como administrador. **Teste independente**: cadastrar tenant com e-mail novo, receber JWT e consultar seus dados. **Requisitos**: FR-001, FR-017.

### 6. Cenários BDD de aceite

#### AC-001 — Operação diária válida
**Cobre**: US-001, FR-004, FR-005, FR-015, NFR-001, NFR-002, NFR-003
```gherkin
Scenario: registrar fechamento diário
  Given um veículo ativo com hodômetro 10000
  When o operador registra hodômetro 10120 e receita de 350.00
  Then o sistema registra 120 km e recalcula os indicadores com precisão decimal
```

#### AC-002 — Regressão de hodômetro
**Cobre**: US-001, FR-004, FR-005, FR-015, NFR-001, NFR-002, NFR-003
```gherkin
Scenario: rejeitar hodômetro regressivo
  Given o último hodômetro validado de 10000
  When o operador informa 9999 sem ajuste autorizado
  Then o lançamento é rejeitado e a inconsistência é explicada
```

#### AC-003 — Reenvio idempotente
**Cobre**: US-001, FR-004, FR-005, FR-015, NFR-001, NFR-002, NFR-003
```gherkin
Scenario: não duplicar operação
  Given uma operação recebida com chave de idempotência conhecida
  When a mesma requisição é reenviada
  Then nenhuma operação ou receita duplicada é criada
```

#### AC-004 — Lucro líquido real
**Cobre**: US-002, FR-006, FR-007, FR-008, FR-013, FR-014, NFR-001, NFR-005
```gherkin
Scenario: calcular rentabilidade
  Given receita de 350.00 combustível de 70.00 e manutenção de 15.00
  When o período é calculado
  Then o lucro líquido real é 265.00
```

#### AC-005 — Rateio aplicável
**Cobre**: US-002, FR-006, FR-007, FR-008, FR-013, FR-014, NFR-001, NFR-005
```gherkin
Scenario: ratear despesa compartilhada
  Given uma despesa de frota com critério configurado
  When o demonstrativo é consultado
  Then somente veículos e períodos aplicáveis recebem a parcela
```

#### AC-006 — Histórico financeiro estável
**Cobre**: US-002, FR-006, FR-007, FR-008, FR-013, FR-014, NFR-001, NFR-005
```gherkin
Scenario: preservar preço histórico
  Given um preço vigente usado em período encerrado
  When uma nova vigência é importada
  Then o resultado histórico permanece inalterado e o painel responde em até 3 segundos
```

#### AC-007 — Alerta por quilometragem
**Cobre**: US-003, FR-009, FR-010, FR-011, FR-012, NFR-003, NFR-006
```gherkin
Scenario: gerar alerta de atenção
  Given troca de óleo a cada 5000 km com aviso a 500 km
  When faltam 500 km
  Then um alerta de atenção é criado
```

#### AC-008 — Evento de manutenção
**Cobre**: US-003, FR-009, FR-010, FR-011, FR-012, NFR-003, NFR-006
```gherkin
Scenario: publicar alerta crítico
  Given uma manutenção vencida
  When o alerta se torna crítico
  Then um evento idempotente e assinado fica disponível ao n8n
```

#### AC-009 — Execução encerra alerta
**Cobre**: US-003, FR-009, FR-010, FR-011, FR-012, NFR-003, NFR-006
```gherkin
Scenario: concluir manutenção
  Given uma manutenção aberta
  When a execução é registrada
  Then o próximo vencimento é recalculado e o alerta é encerrado
```

#### AC-010 — Sincronização válida do catálogo
**Cobre**: US-004, US-005, FR-002, FR-003, FR-012, FR-018, FR-019, FR-020, NFR-004, NFR-008, NFR-009
```gherkin
Scenario: importar catálogo somente leitura
  Given a planilha Google autorizada acessível por CSV HTTPS
  When um administrador sincroniza o catálogo
  Then registros válidos são inseridos ou atualizados sem escrever na planilha
```

#### AC-011 — Normalização determinística
**Cobre**: US-004, US-005, FR-002, FR-003, FR-012, FR-018, FR-019, FR-020, NFR-004, NFR-008, NFR-009
```gherkin
Scenario: herdar categoria omitida
  Given uma linha de 13 colunas após categoria validada
  When somente a categoria foi omitida
  Then a categoria anterior é herdada e valores decimais são preservados
```

#### AC-012 — Sincronização inválida é atômica
**Cobre**: US-004, US-005, FR-002, FR-003, FR-012, FR-018, FR-019, FR-020, NFR-004, NFR-008, NFR-009
```gherkin
Scenario: rejeitar linha incompatível
  Given uma linha com quantidade inesperada de colunas
  When a sincronização é executada
  Then ela falha antes de substituir o catálogo válido e informa a linha
```

#### AC-013 — Cadastro atômico de tenant
**Cobre**: US-007, FR-001, FR-017, NFR-003, NFR-004, NFR-006
```gherkin
Scenario: cadastrar organização
  Given organização e e-mail novos e senha com 12 caracteres
  When o cadastro é concluído
  Then organização e administrador são criados atomicamente e um JWT é emitido
```

#### AC-014 — E-mail duplicado
**Cobre**: US-007, FR-001, FR-017, NFR-003, NFR-004, NFR-006
```gherkin
Scenario: rejeitar e-mail existente
  Given um e-mail já cadastrado
  When um novo cadastro é enviado
  Then o sistema responde conflito sem criar organização órfã
```

#### AC-015 — Isolamento por organização
**Cobre**: US-007, FR-001, FR-017, NFR-003, NFR-004, NFR-006
```gherkin
Scenario: impedir leitura entre tenants
  Given um usuário autenticado na organização A
  When ele consulta um identificador pertencente à organização B
  Then nenhum dado da organização B é retornado
```

#### AC-016 — Painel móvel
**Cobre**: US-006, FR-014, FR-016, NFR-005, NFR-007
```gherkin
Scenario: usar painel em 360 pixels
  Given um dispositivo com largura de 360 px
  When o gestor abre o painel
  Then não há rolagem horizontal e a navegação inferior permanece acessível
```

#### AC-017 — Painel desktop
**Cobre**: US-006, FR-014, FR-016, NFR-005, NFR-007
```gherkin
Scenario: usar painel em desktop
  Given uma viewport desktop
  When o gestor abre o painel
  Then sidebar cartões filtros e ações usam o espaço sem ocultar funcionalidades
```

#### AC-018 — Estados acessíveis
**Cobre**: US-006, FR-014, FR-016, NFR-005, NFR-007
```gherkin
Scenario: navegar por teclado
  Given uma pessoa usando teclado
  When percorre formulário menu e painel lateral
  Then foco erros e confirmações permanecem perceptíveis e operáveis
```

### 7. Requisitos

#### Funcionais

- **FR-001**: Isolar dados por organização autenticada.
- **FR-002**: Cadastrar veículos com categoria, identificação, energia, capacidade, consumo, hodômetro e status.
- **FR-003**: Suportar gasolina, etanol, diesel, GNV, elétrico, híbrido, humano e outro.
- **FR-004**: Registrar operações, receitas e despesas com data, valor, veículo, origem e responsável.
- **FR-005**: Impedir regressão de hodômetro, salvo ajuste autorizado e auditado.
- **FR-006**: Categorizar despesas operacionais, de manutenção, impostos, seguro e demais custos.
- **FR-007**: Calcular faturamento, custos, custo e receita por km, margem e lucro líquido real.
- **FR-008**: Apropriar manutenção prevista proporcionalmente à quilometragem.
- **FR-009**: Cadastrar regras preventivas por veículo ou categoria, por km, data ou ambos.
- **FR-010**: Manter histórico de execuções e recalcular vencimentos.
- **FR-011**: Gerar alertas informativo, atenção e crítico e publicar eventos ao n8n.
- **FR-012**: Autenticar e tornar idempotentes as integrações, registrando fonte, payload e coleta.
- **FR-013**: Armazenar preços com localidade, vigência e fonte sem alterar períodos históricos.
- **FR-014**: Disponibilizar agregados aos painéis React e Metabase.
- **FR-015**: Auditar alterações financeiras, de hodômetro e manutenção.
- **FR-016**: Adaptar toda a interface a celular, tablet e desktop sem remover operações.
- **FR-017**: Cadastrar organização e primeiro administrador atomicamente e autenticar após sucesso.
- **FR-018**: Sincronizar, somente para leitura, a planilha autorizada `1aLlhNvD3K0ztU9Rq-x7yKnLryoCGCF4lhxswHvsyG5I`, aba `1122938118`.
- **FR-019**: Validar cabeçalho e colunas, normalizar apenas categoria omitida e preservar decimais.
- **FR-020**: Mapear categoria e energia do catálogo e criar somente regras de manutenção válidas.

#### Não funcionais

- **NFR-001**: Valores financeiros usam `Decimal` e `NUMERIC`. **Verificação**: testes de domínio e inspeção de migrations.
- **NFR-002**: Horários ficam em UTC com fuso configurável por organização. **Verificação**: testes de serialização e persistência.
- **NFR-003**: Escritas externas usam chave de idempotência. **Verificação**: reenvio automatizado.
- **NFR-004**: Contratos HTTP são documentados por OpenAPI. **Verificação**: inspeção de `/openapi.json`.
- **NFR-005**: Dashboard de até 100 veículos responde em até 3 segundos. **Verificação**: teste no ambiente de referência.
- **NFR-006**: Schema muda somente por migrations versionadas e testadas. **Verificação**: Alembic e suite de migrations.
- **NFR-007**: Interface funciona a partir de 360 px, sem rolagem horizontal e com alvos de 44 px. **Verificação**: viewport móvel e auditoria de interação.
- **NFR-008**: Catálogo aceita apenas HTTPS em `docs.google.com`, com timeout e sem credenciais. **Verificação**: testes do cliente de integração.
- **NFR-009**: Sincronização inválida não substitui parcialmente o catálogo anterior. **Verificação**: teste transacional.

#### Erros e casos-limite

- Hodômetro regressivo → `422` explicando a inconsistência.
- E-mail repetido → `409` sem tenant órfão.
- Chave idempotente repetida → retorno estável sem duplicação.
- Linha de catálogo inválida → sincronização abortada antes do commit.
- Serviço externo indisponível → timeout limitado, log estruturado e catálogo anterior preservado.

## Ato II — Projetar e provar

### 8. Plano técnico

#### Contexto existente

- Monólito modular com Next.js 16/React 19, FastAPI/Pydantic v2, PostgreSQL 18, SQLAlchemy 2, Alembic, Docker Compose, n8n e Metabase.

#### Arquitetura e módulos

- `frontend/` consome exclusivamente a API; `backend/app/` concentra autenticação, domínio, integrações, persistência e workers; PostgreSQL é a fonte de verdade.

#### Migrations

- Todas as tabelas e views são versionadas em `backend/alembic/`; bootstrap do papel de BI fica em `infra/postgres/init-bi.sh` e possui teste real em PostgreSQL.

#### Models

- Models de organização, usuário, veículo, operação, finanças, manutenção, integração, catálogo e outbox ficam em `backend/app/models/` com valores monetários decimais.

#### Controllers e casos de uso

- Rotas versionadas em `backend/app/api/v1/`; serviços em `backend/app/services/` aplicam tenant, validações e transações.

#### Views e experiência

- App Router em `frontend/app/`, componentes reutilizáveis em `frontend/components/` e integrações HTTP em `frontend/lib/`.

#### Queries e repositórios

- SQLAlchemy aplica `organization_id`; views `bi_vehicle_daily` e `bi_maintenance_alerts` expõem somente leitura ao papel `metabase_bi`.

#### Jobs e processamento assíncrono

- Outbox transacional entrega webhooks HMAC ao n8n com chave estável e retentativa limitada; sincronização periódica do catálogo é configurável.

#### Estrutura de arquivos

```text
backend/app/        API, domínio, models, serviços e workers
backend/alembic/    migrations versionadas
backend/tests/      testes pytest
frontend/app/       rotas e telas Next.js
frontend/components/ componentes de interface
infra/              banco e proxy
docs/               documentação técnica
specs/in-progress/0001-gestao-logistica/spec.md
```

### 9. Modelo de dados

#### Entidades

| Entidade | Identidade | Atributos e regras | Relações |
| --- | --- | --- | --- |
| Organization | UUID | nome, fuso, ativo | possui usuários e dados operacionais |
| User | UUID | e-mail único, hash, papel | pertence a uma organização |
| Vehicle | UUID | categoria, energia, hodômetro, status | pertence à organização e recebe operações |
| OperationalRecord | UUID | data, KM, receita, idempotência | pertence a veículo e usuário |
| Revenue / Expense | UUID | valor NUMERIC, categoria, origem | pertence à organização e opcionalmente veículo |
| MaintenanceRule / Execution | UUID | intervalo, custo, vencimento | pertence a veículo ou categoria |
| MaintenanceAlert | UUID | nível, estado, vencimento | deriva de regra e execução |
| FuelPrice | UUID | energia, localidade, vigência, fonte | histórico imutável por vigência |
| VehicleCatalogSpec | UUID | marca, modelo, versão, categoria, energia | chave natural de sincronização |
| OutboxEvent | UUID | tipo, payload, tentativas, entrega | produzido na transação de domínio |

#### Estados e transições

| Entidade | Estado atual | Evento | Próximo estado | Invariantes |
| --- | --- | --- | --- | --- |
| Vehicle | active | desativar | inactive | histórico é preservado |
| MaintenanceAlert | open | executar manutenção | closed | próximo vencimento recalculado |
| OutboxEvent | pending | entrega confirmada | delivered | mesma chave não é reenviada como novo evento |

#### Migração e retenção

- Alembic executa upgrade antes da API aceitar tráfego; rollback é testado quando suportado e dados financeiros/auditoria não são apagados por atualização ordinária.

### 10. Interfaces e contratos

#### Interface para pessoas

- **Há interface para pessoas**: Sim. Operador, gestor e administrador usam o web app responsivo LogiSync.

#### Stack e convenções de interface

- Next.js 16, React 19 e TypeScript; shell azul-marinho, azul elétrico, ícones lineares, cartões claros, sidebar no desktop e navegação inferior no celular.

#### Telas e responsabilidades

- Login/cadastro cria sessão; dashboard resume operação; frota mantém veículos; catálogo sincroniza modelos; financeiro mostra receitas, custos e lucro; manutenção administra regras, execuções e alertas.

#### Fluxo de informação e navegação

- Após autenticar, a pessoa chega ao Dashboard. O breadcrumb preserva `LogiSync > módulo > tela`; listas abrem formulários ou painéis laterais e retornam mantendo filtros.

#### Menus e navegação principal

- Menu desktop em sidebar e menu móvel inferior possuem itens Dashboard, Frota, Catálogo, Financeiro e Manutenção, com destino às respectivas rotas e visibilidade conforme papel.

#### Formulários e ações

- Campos obrigatórios exibem ajuda e erro junto ao controle; salvar é a ação principal; exclusões e operações irreversíveis pedem confirmação; cadastro e edição usam página ou painel lateral conforme densidade.

#### Composição e disposição

- Shell contém cabeçalho, breadcrumb, navegação e conteúdo; cartões substituem tabelas em telas estreitas; grids se ajustam sem rolagem horizontal.

#### Blocos React e componentes selecionados

| Tela | Bloco React | Responsabilidade | Arquivo previsto | Componente ou composição | Origem | Reuso ou extensão |
| --- | --- | --- | --- | --- | --- | --- |
| Shell | AppShell | navegação e sessão | `frontend/components/app-shell.tsx` | Sidebar, MobileNav, Breadcrumb | próprio | extensão existente |
| Dashboard | DashboardView | indicadores e atalhos | `frontend/app/page.tsx` | StatCard, filters, charts | próprio | reuso existente |
| Frota | VehicleList | listar e editar veículos | `frontend/app/frota/page.tsx` | cards, table, form | próprio | reuso existente |
| Catálogo | CatalogView | consultar e sincronizar | `frontend/app/catalogo/page.tsx` | filters, cards, action bar | próprio | reuso existente |
| Login | AuthForm | autenticar e cadastrar tenant | `frontend/app/login/page.tsx` | inputs, feedback, submit | próprio | reuso existente |

#### Estados e acessibilidade

- Toda tela define loading, vazio, erro, sucesso e permissão insuficiente; foco é visível, campos possuem rótulo, feedback usa texto e cor e o breadcrumb marca a página atual.

#### APIs expostas

- `POST /api/v1/auth/token`, `POST /api/v1/auth/register`, CRUD de veículos/operações/finanças/manutenção e `GET|POST /api/v1/vehicle-catalog`; autenticação JWT, OpenAPI e respostas de erro estruturadas.

#### APIs externas utilizadas

- Google Sheets CSV por HTTPS, somente leitura e timeout; n8n por webhook HMAC com retry; nenhuma credencial é enviada à planilha.

#### Documentação das APIs consultadas

- OpenAPI local do FastAPI e contrato da exportação CSV autorizado, conforme código e testes do repositório.

#### Eventos e outros contratos

- Eventos de alerta usam tipo versionável, payload JSON, `Idempotency-Key` e assinatura HMAC; produtor é a outbox e consumidor é o n8n.

### 11. Estratégia TDD

- **Unidade**: cálculos financeiros, hodômetro, manutenção, catálogo e autenticação.
- **Integração/contrato**: API, PostgreSQL, migrations, views de BI, Google CSV e webhook n8n.
- **BDD/aceite**: AC-001 a AC-018 orientam novos testes e regressões.
- **Runner TDD**: `pytest` no backend; runner configurado no `package.json` do frontend.
- **E2E**: login, cadastro de tenant, operação diária, catálogo e consulta gerencial.
- **Verificação manual**: layout responsivo e provedores externos após deploy.

#### Evidência RED-GREEN-REFACTOR

| IDs | BDD de referência | Teste TDD informado pelo BDD | RED observado | GREEN observado | Refactor/regressão |
| --- | --- | --- | --- | --- | --- |
| US-001, US-002, AC-001 a AC-006 | Operação e finanças | `backend/tests/` | evidência histórica anterior à migração | 24 testes backend aprovados em 2026-08-24 | Ruff e mypy aprovados |
| US-003, AC-007 a AC-009 | Manutenção e outbox | `backend/tests/` | evidência histórica anterior à migração | suite backend aprovada | regressão aprovada |
| US-004, US-005, AC-010 a AC-012 | Catálogo Google | `backend/tests/` | evidência histórica anterior à migração | sincronização de 421 modelos validada | catálogo anterior preservado em falha |
| US-006, US-007, AC-013 a AC-018 | Identidade e interface | `frontend/` e `backend/tests/` | evidência histórica anterior à migração | lint, testes e build estático aprovados | exportação de logo corrigida |

### 12. Plano de testes e rastreabilidade

| Requisito | Cenário BDD | Nível | Arquivo/comando esperado | Evidência |
| --- | --- | --- | --- | --- |
| FR-001, FR-017 | AC-013, AC-014, AC-015 | integração | `pytest -q` | Passed em 2026-08-25 na suíte completa (`47 passed`) |
| FR-004, FR-005, FR-015 | AC-001, AC-002, AC-003 | unidade e API | `pytest -q` | Passed em 2026-08-25 na suíte completa (`47 passed`) |
| FR-006 a FR-008 | AC-004, AC-005, AC-006 | domínio | `pytest -q` | Passed em 2026-08-25; focal financeiro `6 passed` e suíte completa `47 passed` |
| FR-009 a FR-012 | AC-007, AC-008, AC-009 | domínio e webhook | `pytest -q` | Passed em 2026-08-25 na suíte completa (`47 passed`) |
| FR-018 a FR-020 | AC-010, AC-011, AC-012 | integração | `pytest -q` | Passed em 2026-08-25 na suíte completa (`47 passed`) |
| FR-014, FR-016 | AC-016, AC-017, AC-018 | frontend | `npm run lint`, `npm test`, `npm run build` | Passed em Node 22 Linux em 2026-08-25; 7 rotas estáticas geradas |
| NFR-006 | AC-007, AC-013, AC-015 | infraestrutura | `pytest tests/test_bi_migration.py` e Compose | Passed em 2026-08-25; PostgreSQL/API saudáveis e workers com zero restarts |

### 13. Validações

#### Gate do Ato I — Definição

- **Resultado**: Passed em 2026-08-24.
- **Comando**: `node .agents/skills/specsfy-04-validate/scripts/validate_spec.mjs specs/in-progress/0001-gestao-logistica/spec.md`.
- **Achados**: estrutura Specsfy 2.0, requisitos, BDD e interface consolidados; nenhum bloqueio estrutural.

#### Gate do Ato II — Plano

- **Resultado**: Passed em 2026-08-25 após explicitar T043.
- **Comando**: `node .agents/skills/specsfy-05-tasks/scripts/validate_tasks.mjs specs/in-progress/0001-gestao-logistica/spec.md --allow-draft`.
- **Achados**: 19 tarefas válidas, 18 casos TDD preservados e T043 [OPS] pronta, dependente apenas de T032/T034 concluídas.

#### Gate do Ato III — Entrega

- **Resultado**: Passed em 2026-08-25.
- **Comando**: `pytest -q`; `ruff check app tests`; `mypy app`; `npm run lint`; `npm test`; `npm run build`; validadores Specsfy e health checks Compose.
- **Achados**: backend `47 passed`, Ruff/mypy aprovados; frontend lint/TypeScript/build aprovados; QA Passed, rastreabilidade 54/54, 19/19 tarefas, PostgreSQL/API saudáveis, frontend HTTP 200 e workers com zero reinicializações.

#### Aceite final

- **Resultado**: READY em 2026-08-25; nenhum `BLOCKER` ou finding P1 aberto para a SPEC-0001.
- **Rastreabilidade**: o verificador oficial executado em Linux aprovou 54/54 IDs; a SPEC-0002 aprovou separadamente 10/10 IDs no escopo canônico `backend/tests/production`.
- **Enforcement global**: os checks de estrutura, tarefas, aceite, evidência, pesquisa e catálogo de skills passaram. O agregador oficial `verify_repo.mjs` continua retornando falso negativo ao misturar marcadores de testes de múltiplas specs; nenhuma política, script ou evidência foi alterada para ocultar essa limitação.

### 14. Tarefas

T001–T024 identificam a implementação histórica preservada por DEC-007. As tarefas executáveis atuais começam em T025 e caracterizam o comportamento presente em `backend/tests/acceptance/test_mvp_acceptance.py`.

#### Fase 1 — Operação diária

- [x] T025 [TEST] [TDD] [US-001] Caracterizar AC-001: fechamento diário válido em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-001, FR-004, FR-005, FR-015, NFR-001, NFR-002, NFR-003, AC-001 — Depends: none
  - [x] **PREP**: Cálculo decimal, distância, receita e registro operacional confirmados no endpoint atual; RED de rastreabilidade observado com AC-001 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador `SPECSFY:` exclusivo para AC-001.
  - [x] **VERIFY**: Teste focal aprovou distância 120.00, receita 350.00 e lucro 280.00.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed`; arquivo e IDs registrados nesta tarefa.
  - [x] **IMPROVE**: Assertions convertem respostas em `Decimal`, evitando comparação financeira por ponto flutuante.
  <!-- specsfy:evidence {"task":"T025","refs":["US-001","FR-004","FR-005","FR-015","NFR-001","NFR-002","NFR-003","AC-001"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac001_registers_valid_daily_closing_with_decimal_distance -q","exit":0}]} -->
- [x] T026 [TEST] [TDD] [US-001] Caracterizar AC-002: rejeição de hodômetro regressivo em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-001, FR-004, FR-005, FR-015, NFR-001, NFR-002, NFR-003, AC-002 — Depends: none
  - [x] **PREP**: Regra monotônica e resposta 422 confirmadas; RED de rastreabilidade observado com AC-002 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador `SPECSFY:` exclusivo para AC-002.
  - [x] **VERIFY**: Teste focal aprovou rejeição do hodômetro 9999 contra baseline 10000.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed` e confirmou diagnóstico acionável.
  - [x] **IMPROVE**: O teste verifica também a mensagem de inconsistência, não somente o status HTTP.
  <!-- specsfy:evidence {"task":"T026","refs":["US-001","FR-004","FR-005","FR-015","NFR-001","NFR-002","NFR-003","AC-002"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac002_rejects_odometer_regression_with_actionable_error -q","exit":0}]} -->
- [x] T027 [TEST] [TDD] [US-001] Caracterizar AC-003: reenvio idempotente em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-001, FR-004, FR-005, FR-015, NFR-001, NFR-002, NFR-003, AC-003 — Depends: none
  - [x] **PREP**: Chave idempotente, retorno estável e agregado mensal confirmados; RED de rastreabilidade observado com AC-003 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador `SPECSFY:` exclusivo para AC-003.
  - [x] **VERIFY**: Teste focal aprovou o mesmo ID no reenvio e receita mensal sem duplicação.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed` para a chave `spec-0001-ac003`.
  - [x] **IMPROVE**: O oráculo passou a verificar também o agregado, protegendo contra duplicação silenciosa.
  <!-- specsfy:evidence {"task":"T027","refs":["US-001","FR-004","FR-005","FR-015","NFR-001","NFR-002","NFR-003","AC-003"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac003_replay_returns_same_operation_without_duplicate -q","exit":0}]} -->

#### Fase 2 — Financeiro e rentabilidade

- [x] T028 [TEST] [TDD] [US-002] Caracterizar AC-004: lucro líquido real em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-002, FR-006, FR-007, FR-008, FR-013, FR-014, NFR-001, NFR-005, AC-004 — Depends: none
  - [x] **PREP**: Receita, combustível e reserva por KM confirmados com `Decimal`; RED de rastreabilidade observado com AC-004 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador exclusivo e valores do Gherkin.
  - [x] **VERIFY**: Teste focal aprovou manutenção 15.00 e lucro líquido 265.00.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed` para AC-004.
  - [x] **IMPROVE**: O teste usa exatamente os valores de aceite, eliminando ambiguidade de arredondamento.
  <!-- specsfy:evidence {"task":"T028","refs":["US-002","FR-006","FR-007","FR-008","FR-013","FR-014","NFR-001","NFR-005","AC-004"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac004_calculates_exact_real_net_profit -q","exit":0}]} -->
- [x] T029 [TEST] [TDD] [US-002] Caracterizar AC-005: rateio aplicável em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-002, FR-006, FR-007, FR-008, FR-013, FR-014, NFR-001, NFR-005, AC-005 — Depends: none
  - [x] **PREP**: Apropriação configurada por `vehicle_id` e aplicabilidade delimitada por `expense_date` confirmadas; RED de rastreabilidade observado com AC-005 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador exclusivo, duas viaturas e três despesas para isolar simultaneamente veículo e período.
  - [x] **VERIFY**: Docker/pytest aprovou o caso focal e as regressões `test_profitability.py` e `test_operations.py` (`6 passed`).
  - [x] **EVIDENCE**: O teste prova que somente a parcela de `120.00` do veículo-alvo dentro de agosto compõe `other_expenses`.
  - [x] **IMPROVE**: A asserção converte a resposta para `Decimal`, impedindo comparação financeira por ponto flutuante.
  <!-- specsfy:evidence {"task":"T029","refs":["US-002","FR-006","FR-007","FR-008","FR-013","FR-014","NFR-001","NFR-005","AC-005"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac005_applies_expense_only_to_configured_vehicle_and_period tests/test_profitability.py tests/test_operations.py -q","exit":0}]} -->
- [x] T030 [TEST] [TDD] [US-002] Caracterizar AC-006: histórico financeiro estável em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-002, FR-006, FR-007, FR-008, FR-013, FR-014, NFR-001, NFR-005, AC-006 — Depends: none
  - [x] **PREP**: Preço unitário persistido no lançamento e limite de 3 segundos confirmados; RED de rastreabilidade observado com AC-006 em 0/1.
  - [x] **EXECUTE**: Caso pytest altera o preço vigente após o lançamento e consulta o período com marcador exclusivo.
  - [x] **VERIFY**: Teste focal preservou o custo histórico e respondeu abaixo de 3 segundos.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed` para AC-006.
  - [x] **IMPROVE**: O teste mede o orçamento de resposta e preservação histórica no mesmo fluxo observável.
  <!-- specsfy:evidence {"task":"T030","refs":["US-002","FR-006","FR-007","FR-008","FR-013","FR-014","NFR-001","NFR-005","AC-006"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac006_preserves_historical_cost_and_responds_within_budget -q","exit":0}]} -->

#### Fase 3 — Manutenção e eventos

- [x] T031 [TEST] [TDD] [US-003] Caracterizar AC-007: alerta por quilometragem em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-003, FR-009, FR-010, FR-011, FR-012, NFR-003, NFR-006, AC-007 — Depends: none
  - [x] **PREP**: Intervalo 5000 km, aviso 500 km e nível warning confirmados; RED de rastreabilidade observado com AC-007 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador exclusivo e limiar do Gherkin.
  - [x] **VERIFY**: Teste focal aprovou alerta warning com vencimento em 15000 km.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed` para AC-007.
  - [x] **IMPROVE**: O oráculo verifica severidade e hodômetro de vencimento, não apenas existência.
  <!-- specsfy:evidence {"task":"T031","refs":["US-003","FR-009","FR-010","FR-011","FR-012","NFR-003","NFR-006","AC-007"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac007_creates_warning_at_maintenance_threshold -q","exit":0}]} -->
- [x] T032 [TEST] [TDD] [US-003] Caracterizar AC-008: evento assinado e idempotente em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-003, FR-009, FR-010, FR-011, FR-012, NFR-003, NFR-006, AC-008 — Depends: none
  - [x] **PREP**: Outbox, envelope, HMAC e idempotência confirmados; RED de rastreabilidade observado com AC-008 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador exclusivo e sender capturado.
  - [x] **VERIFY**: Após corrigir o oráculo para o envelope real, o teste aprovou entrega única, chave e assinatura HMAC.
  - [x] **EVIDENCE**: Docker/pytest final terminou com `1 passed`; a falha intermediária foi classificada como erro do teste, não do produto.
  - [x] **IMPROVE**: O teste passou a validar explicitamente o payload interno versionável.
  <!-- specsfy:evidence {"task":"T032","refs":["US-003","FR-009","FR-010","FR-011","FR-012","NFR-003","NFR-006","AC-008"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac008_delivers_critical_event_once_with_hmac_signature -q","exit":0}]} -->
- [x] T033 [TEST] [TDD] [US-003] Caracterizar AC-009: execução encerra alerta em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-003, FR-009, FR-010, FR-011, FR-012, NFR-003, NFR-006, AC-009 — Depends: none
  - [x] **PREP**: Alerta aberto, execução e reinício do ciclo confirmados; RED de rastreabilidade observado com AC-009 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador exclusivo para regra, operação e execução.
  - [x] **VERIFY**: Teste focal aprovou a execução e a ausência de alertas abertos após o fechamento.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed` para AC-009.
  - [x] **IMPROVE**: O fluxo confirma o estado antes e depois da execução para impedir falso positivo.
  <!-- specsfy:evidence {"task":"T033","refs":["US-003","FR-009","FR-010","FR-011","FR-012","NFR-003","NFR-006","AC-009"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac009_execution_closes_alert_and_restarts_cycle -q","exit":0}]} -->

#### Fase 4 — Catálogo e integrações

- [x] T034 [TEST] [TDD] [US-004] [US-005] Caracterizar AC-010: sincronização válida do catálogo em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-004, US-005, FR-002, FR-003, FR-012, FR-018, FR-019, FR-020, NFR-004, NFR-008, NFR-009, AC-010 — Depends: none
  - [x] **PREP**: Parser somente leitura, persistência local e cadastro derivado confirmados; RED de rastreabilidade observado com AC-010 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador exclusivo para CSV válido e cadastro de veículo.
  - [x] **VERIFY**: Teste focal aprovou catálogo, mapeamento de categoria e duas regras válidas.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed` para AC-010.
  - [x] **IMPROVE**: O caso valida o efeito local sem qualquer escrita ou credencial na fonte Google.
  <!-- specsfy:evidence {"task":"T034","refs":["US-004","US-005","FR-002","FR-003","FR-012","FR-018","FR-019","FR-020","NFR-004","NFR-008","NFR-009","AC-010"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac010_imports_valid_catalog_without_writing_to_source -q","exit":0}]} -->
- [x] T035 [TEST] [TDD] [US-004] [US-005] Caracterizar AC-011: normalização determinística em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-004, US-005, FR-002, FR-003, FR-012, FR-018, FR-019, FR-020, NFR-004, NFR-008, NFR-009, AC-011 — Depends: none
  - [x] **PREP**: Herança exclusiva da categoria omitida e preservação de decimais confirmadas no parser atual; RED de rastreabilidade observado com AC-011 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador `SPECSFY:` exclusivo para AC-011.
  - [x] **VERIFY**: Teste focal aprovou a herança de `Carro` somente na linha omitida e os consumos 13.5/9.4 como `Decimal`.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed`; arquivo e IDs registrados nesta tarefa.
  - [x] **IMPROVE**: Assertions explícitas impedem coerção silenciosa dos números do catálogo para ponto flutuante.
  <!-- specsfy:evidence {"task":"T035","refs":["US-004","US-005","FR-002","FR-003","FR-012","FR-018","FR-019","FR-020","NFR-004","NFR-008","NFR-009","AC-011"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac011_inherits_only_omitted_category_and_preserves_decimals -q","exit":0}]} -->
- [x] T036 [TEST] [TDD] [US-004] [US-005] Caracterizar AC-012: sincronização inválida atômica em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-004, US-005, FR-002, FR-003, FR-012, FR-018, FR-019, FR-020, NFR-004, NFR-008, NFR-009, AC-012 — Depends: none
  - [x] **PREP**: Falha do parser antes do commit e diagnóstico pela linha confirmados; RED de rastreabilidade observado com AC-012 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador `SPECSFY:` exclusivo para AC-012.
  - [x] **VERIFY**: Teste focal aprovou erro em `linha 2` e contagem persistida inalterada.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed`; arquivo e IDs registrados nesta tarefa.
  - [x] **IMPROVE**: O caso mede o estado antes e depois da tentativa para tornar a atomicidade observável.
  <!-- specsfy:evidence {"task":"T036","refs":["US-004","US-005","FR-002","FR-003","FR-012","FR-018","FR-019","FR-020","NFR-004","NFR-008","NFR-009","AC-012"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac012_rejects_invalid_catalog_atomically -q","exit":0}]} -->

#### Fase 5 — Identidade e isolamento

- [x] T037 [TEST] [TDD] [US-007] Caracterizar AC-013: cadastro atômico de tenant em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-007, FR-001, FR-017, NFR-003, NFR-004, NFR-006, AC-013 — Depends: none
  - [x] **PREP**: Transação de organização/usuário e emissão de JWT confirmadas; RED de rastreabilidade observado com AC-013 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador `SPECSFY:` exclusivo para AC-013.
  - [x] **VERIFY**: Teste focal aprovou cadastro, sessão autenticada, organização, e-mail e papel `admin`.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed`; arquivo e IDs registrados nesta tarefa.
  - [x] **IMPROVE**: A sessão obtida com o token emitido valida o fluxo completo, não apenas o status de cadastro.
  <!-- specsfy:evidence {"task":"T037","refs":["US-007","FR-001","FR-017","NFR-003","NFR-004","NFR-006","AC-013"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac013_registers_tenant_and_returns_authenticated_admin -q","exit":0}]} -->
- [x] T038 [TEST] [TDD] [US-007] Caracterizar AC-014: e-mail duplicado em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-007, FR-001, FR-017, NFR-003, NFR-004, NFR-006, AC-014 — Depends: none
  - [x] **PREP**: Conflito por e-mail normalizado e rollback da organização confirmados; RED de rastreabilidade observado com AC-014 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador `SPECSFY:` exclusivo para AC-014.
  - [x] **VERIFY**: Teste focal aprovou HTTP 409 e contagens de organizações/usuários inalteradas após a duplicata.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed`; arquivo e IDs registrados nesta tarefa.
  - [x] **IMPROVE**: A busca nominal adicional demonstra diretamente que nenhuma organização órfã foi persistida.
  <!-- specsfy:evidence {"task":"T038","refs":["US-007","FR-001","FR-017","NFR-003","NFR-004","NFR-006","AC-014"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac014_rejects_duplicate_email_without_orphan_organization -q","exit":0}]} -->
- [x] T039 [TEST] [TDD] [US-007] Caracterizar AC-015: isolamento por organização em `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-007, FR-001, FR-017, NFR-003, NFR-004, NFR-006, AC-015 — Depends: none
  - [x] **PREP**: Tenant derivado do JWT e filtros por organização confirmados; RED de rastreabilidade observado com AC-015 em 0/1.
  - [x] **EXECUTE**: Caso pytest criado com marcador `SPECSFY:` exclusivo para AC-015.
  - [x] **VERIFY**: Após corrigir no oráculo os parâmetros obrigatórios de período (primeira execução 422), o teste focal aprovou lista vazia e HTTP 404 para o veículo alheio.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed`; arquivo e IDs registrados nesta tarefa.
  - [x] **IMPROVE**: O teste cobre simultaneamente coleção e recurso individual, evitando falso isolamento por apenas uma rota.
  <!-- specsfy:evidence {"task":"T039","refs":["US-007","FR-001","FR-017","NFR-003","NFR-004","NFR-006","AC-015"],"files":["backend/tests/acceptance/test_mvp_acceptance.py"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac015_isolates_vehicle_data_by_token_organization -q","exit":0}]} -->

#### Fase de interface

- [x] T040 [TEST] [TDD] [US-006] Caracterizar AC-016 em Dashboard, Frota, Catálogo, Financeiro, Login e AppShell responsivos via `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-006, FR-014, FR-016, NFR-005, NFR-007, AC-016 — Depends: none
  - [x] **PREP**: Rotas, navegação inferior fixa e proteção contra overflow desde 320 px confirmadas; RED de rastreabilidade observado com AC-016 em 0/1.
  - [x] **EXECUTE**: Contrato pytest criado para as quatro rotas, componente compartilhado e estilos responsivos.
  - [x] **VERIFY**: Teste focal aprovou shell móvel, alvos de navegação com altura mínima e ausência de rolagem horizontal; lint/TypeScript integram o gate final.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed`; componente, estilos, rotas e IDs registrados nesta tarefa.
  - [x] **IMPROVE**: O contrato verifica cada entrada do App Router, evitando uma navegação móvel visualmente presente mas desconectada.
  <!-- specsfy:evidence {"task":"T040","refs":["US-006","FR-014","FR-016","NFR-005","NFR-007","AC-016"],"files":["backend/tests/acceptance/test_mvp_acceptance.py","frontend/components/operations-dashboard.tsx","frontend/app/globals.css","frontend/app/page.tsx","frontend/app/frota/page.tsx","frontend/app/catalogo/page.tsx","frontend/app/financeiro/page.tsx"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac016_mobile_shell_prevents_overflow_and_keeps_navigation_available -q","exit":0}]} -->
- [x] T041 [TEST] [TDD] [US-006] Caracterizar AC-017 em sidebar, cartões, filtros, formulários e ações desktop via `backend/tests/acceptance/test_mvp_acceptance.py` — Refs: US-006, FR-014, FR-016, NFR-005, NFR-007, AC-017 — Depends: none
  - [x] **PREP**: AppShell, sidebar expansível, cartões, filtros, formulários e ações desktop confirmados; RED de rastreabilidade observado com AC-017 em 0/1.
  - [x] **EXECUTE**: Contrato pytest criado para a composição desktop compartilhada pelas rotas previstas.
  - [x] **VERIFY**: Teste focal aprovou sidebar, paddings desktop, indicadores, classificação, busca e três fluxos de formulário; lint/TypeScript integram o gate final.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed`; componente e IDs registrados nesta tarefa.
  - [x] **IMPROVE**: O contrato inclui ações primárias de exportação e fechamento, cobrindo funcionalidade além da estrutura visual.
  <!-- specsfy:evidence {"task":"T041","refs":["US-006","FR-014","FR-016","NFR-005","NFR-007","AC-017"],"files":["backend/tests/acceptance/test_mvp_acceptance.py","frontend/components/operations-dashboard.tsx"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac017_desktop_shell_exposes_sidebar_cards_filters_forms_and_actions -q","exit":0}]} -->
- [x] T042 [TEST] [TDD] [US-006] Caracterizar AC-018 em foco, rótulos, erros, loading, vazio, sucesso e permissão via `backend/tests/acceptance/test_mvp_acceptance.py` e atualizar `INTERFACE.md` — Refs: US-006, FR-014, FR-016, NFR-005, NFR-007, AC-018 — Depends: none
  - [x] **PREP**: Foco, rótulos, erros, loading, vazio, sucesso e identidade/papel perceptíveis confirmados; RED de rastreabilidade observado com AC-018 em 0/1.
  - [x] **EXECUTE**: Contrato pytest criado e inventário observado consolidado em `INTERFACE.md`.
  - [x] **VERIFY**: Teste focal aprovou foco visível, alertas, navegação atual, labels, controles operáveis e estados; documentação determinística passou em `--check`; lint/TypeScript integram o gate final.
  - [x] **EVIDENCE**: Docker/pytest terminou com `1 passed`; documentador e `--check` terminaram com exit 0.
  - [x] **IMPROVE**: `INTERFACE.md` deixou de ser placeholder e agora registra stack, componentes, contratos responsivos e gates reais sem atribuir primitives externas.
  <!-- specsfy:evidence {"task":"T042","refs":["US-006","FR-014","FR-016","NFR-005","NFR-007","AC-018"],"files":["backend/tests/acceptance/test_mvp_acceptance.py","frontend/components/operations-dashboard.tsx","INTERFACE.md","docs/frontend.md",".specsfy/PACKAGES.md"],"commands":[{"run":"pytest tests/acceptance/test_mvp_acceptance.py::test_ac018_keyboard_focus_errors_confirmations_and_states_are_perceptible -q","exit":0},{"run":"node .agents/skills/specsfy-documentator/scripts/build_documentation.mjs --project <raiz> --check","exit":0}]} -->

#### Fase 6 — Gate operacional

- [x] T043 [OPS] [US-003] [US-004] Fornecer `JWT_SECRET_KEY` aos workers em `docker-compose.yml` — Refs: US-003, US-004, FR-012, NFR-003, AC-008, AC-010 — Depends: T032, T034
  - [x] **PREP**: Logs confirmaram `ValidationError` para `jwt_secret_key` ausente em `catalog-sync` e `outbox-worker`; a API usa a mesma configuração obrigatória.
  - [x] **EXECUTE**: `docker-compose.yml` injeta `${JWT_SECRET_KEY:?...}` em `catalog-sync` e `outbox-worker`, sem valor literal.
  - [x] **VERIFY**: `docker compose config --quiet` passou; após recriação e 29 segundos, ambos estavam `running` com `RESTARTS=0`.
  - [x] **EVIDENCE**: `docker compose up -d --force-recreate catalog-sync outbox-worker` e `docker inspect` comprovaram estabilidade sem expor o segredo.
  - [x] **IMPROVE**: A expansão obrigatória `:?` agora falha cedo quando a chave não existe, evitando ciclos silenciosos de restart.

### 15. Ordem de execução

- Caminho crítico de caracterização: T025–T042; T043 fecha o gate operacional depois de T032/T034.
- T001–T024 permanecem IDs históricos descritos em DEC-007, não tarefas executáveis atuais.
- `SPEC-0002` concluída governa hosting, observabilidade, backup, CI e runbook.

## Ato III — Entregar e validar

### 16. Dependências, riscos e suposições

#### Dependências

- Credenciais de produção, domínio/DNS, armazenamento externo de backups e DSN do Sentry.

#### Riscos

- Instância gratuita do Render hibernar → comunicar cold start e avaliar plano conforme uso.
- Banco gratuito expirar → definir upgrade ou migração antes do prazo do provedor.
- Evidência TDD histórica incompleta no formato 2.0 → exigir contrato completo em toda tarefa nova.

#### Suposições

- PostgreSQL permanece fonte de verdade; Netlify hospeda frontend estático e Render hospeda API e banco enquanto forem viáveis.

### 17. Decisões

- **DEC-001**: Adotar monólito modular Next.js + FastAPI + PostgreSQL para velocidade e separação clara de responsabilidades.
- **DEC-002**: Usar JWT HMAC com tenant derivado do token; login Google permanece opcional e depende de configuração OAuth válida.
- **DEC-003**: Consumir Google Sheets somente como CSV HTTPS de leitura e manter projeção local atômica.
- **DEC-004**: Expor BI apenas por views e papel `metabase_bi`, sem grants em tabelas-base.
- **DEC-005**: Publicar frontend como `out/` no Netlify e preservar `standalone` no Docker.
- **DEC-006**: Migrar em 2026-08-24 o legado `spec.md` + `plan.md` + `tasks.md` para uma única fonte Specsfy/2.0.
- **DEC-007**: Extrair a operação de produção para SPEC-0002 e não fabricar checklists ou RED retroativos para T001–T024.
- **DEC-008**: Em 2026-08-25, substituir a lista executável legada por T025–T042 de caracterização atual, usando como RED honesto a falha do contrato de rastreabilidade e sem alegar que o comportamento já implementado nasceu por TDD.
- **DEC-009**: Todos os processos que carregam `Settings`, inclusive workers sem rotas HTTP, recebem a referência protegida `JWT_SECRET_KEY` no Compose.
- **DEC-010**: Validar rastreabilidade por spec com seu escopo canônico enquanto o agregador oficial não isolar marcadores entre múltiplas specs; preservar o falso negativo global de forma explícita, sem alterar o enforcement.

### 18. Definition of Done

- [x] `Definition Gate` está `Passed`.
- [x] `Plan Gate` está `Passed`.
- [x] `Delivery Gate` está `Passed`.
- [x] Todos os cenários `AC` aplicáveis passam com evidência no contrato 2.0.
- [x] Todos os requisitos possuem evidência de verificação no formato 2.0.
- [x] Todas as tarefas na seção 14 estão concluídas.
- [x] Testes, lint, tipagem, build, Compose e health checks passam.
