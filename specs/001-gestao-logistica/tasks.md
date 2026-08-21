# Tarefas: Gestão Logística

## Fase 1 — Fundação e operação diária

- [x] T001 Criar Docker Compose com PostgreSQL, FastAPI e Next.js.
- [x] T002 Criar migration de organizações, veículos e registros operacionais.
- [x] T003 Implementar cadastro e listagem de veículos.
- [x] T004 Implementar fechamento diário com validação de hodômetro.
- [x] T005 Implementar idempotência por organização.
- [x] T006 Criar interface React para cadastro e fechamento diário.
- [x] T007 Cobrir regressão de hodômetro e reenvio idempotente com testes.
- [x] T008 Validar lint, tipagem, build, auditoria de dependências e smoke test.

## Fase 2 — Financeiro e lucro líquido real

- [x] T009 Modelar receitas operacionais, despesas e categorias financeiras.
- [x] T010 Criar migrations e endpoints financeiros.
- [x] T011 Implementar serviço determinístico de rentabilidade com `Decimal`.
- [x] T012 Expor resumo por período e veículo.
- [x] T013 Criar resumo financeiro no frontend.
- [x] T014 Testar faturamento, combustível e despesas categorizadas.

## Fase 3 — Manutenção e alertas

- [x] T015 Modelar regras, execuções, reserva por KM e alertas de manutenção.
- [x] T016 Calcular vencimento por KM, data ou o primeiro dos dois.
- [x] T017 Implementar outbox transacional.
- [x] T018 Publicar webhooks assinados e idempotentes para n8n.
- [x] T019 Criar telas e testes de manutenção.

## Fase 4 — Identidade, automação e BI

- [x] T020 Implementar usuários, autenticação e papéis.
- [x] T021 Isolar todas as consultas por organização autenticada.
- [x] T022 Adicionar n8n e Metabase ao Compose.
- [x] T023 Criar endpoints de integração para dados técnicos e preços.
- [ ] T024 Criar views read-only e usuário de BI.

## Fase 5 — Operação e produção

- [ ] T025 Adicionar Traefik e HTTPS.
- [ ] T026 Configurar logs estruturados, Sentry e métricas.
- [ ] T027 Automatizar backup e teste de restauração.
- [ ] T028 Criar CI com testes, build e auditoria.
- [ ] T029 Produzir runbook de homologação e produção.
