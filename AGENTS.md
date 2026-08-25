# Instruções para agentes do projeto

## Fluxo obrigatório

1. Leia `specs/completed/0001-gestao-logistica/spec.md` como linha de base antes de propor alteração funcional; para trabalho novo, use também a spec ativa aplicável.
2. Atualize ou consulte as seções `8. Plano técnico` e `14. Tarefas` da mesma `spec.md` antes de iniciar mudança estrutural.
3. Execute uma tarefa limitada por vez e valide-a antes de seguir.
4. Registre decisões relevantes na fonte normativa única `spec.md` do Specsfy 2.0.

## Segurança e qualidade

- Não acesse ou altere produção, segredos ou dados reais sem autorização explícita.
- Não execute comandos destrutivos sem confirmação.
- Nunca use `float` para valores financeiros; use `Decimal` e `NUMERIC`.
- Toda alteração de banco deve ter migration Alembic e teste.
- n8n integra-se pela API; não recebe permissão direta de escrita nas tabelas de domínio.
- Eventos externos usam idempotência, assinatura e retentativa controlada.

## Gates de entrega

- Backend: testes, lint e tipagem aprovados.
- Frontend: lint, testes e build aprovados.
- Infraestrutura: Compose e health checks aprovados.
- Regras de lucro, KM e manutenção: cenário de negócio coberto por teste.

Consulte `docs/agent-harness.md` para o grafo de responsabilidades e permissões.

<!-- specsfy:framework:start -->
## Framework Specsfy

Leia e siga integralmente `.specsfy/Spec.md` antes de trabalhar com
backlogs, refinamentos do backlog, especificações, tarefas, testes ou implementação. Esse
arquivo contém o fluxo, os caminhos canônicos e os gates do framework.

- Preserve as instruções próprias deste projeto.
- O diretório do projeto é o caminho informado durante `$specsfy-setup`. Use-o
  em toda leitura e escrita posterior. Se ele estiver dentro de um Hub, não
  promova o trabalho para a raiz Git nem crie contexto, specs ou código fora
  desse caminho.
- Leia `PROJECT.md`, `DESIGNSYSTEM.MD`, `.specsfy/STACK.md`,
  `.specsfy/RULES.md`, `.specsfy/DATABASE.md`, `.specsfy/PACKAGES.md` e
  `.specsfy/USER-PROFILE.md` como contexto persistente antes de planejar
  mudanças.
- Antes de perguntar, consulte `.specsfy/USER-PROFILE.md`, a conversa atual e
  as fontes do projeto. Não repita uma pergunta cuja resposta já esteja
  confirmada; registre respostas novas no perfil com a fonte e o alcance.
- Quando `.specsfy/SPECKIT.md` existir, leia
  `.specify/memory/constitution.md` e cada fonte do GitHub Spec Kit listada na
  projeção. Preserve `.specify/` e os artefatos já existentes em `specs/`; o
  Specsfy não os migra nem os substitui.
- Antes de iniciar qualquer skill do framework, execute obrigatoriamente
  `$specsfy-setup` para verificar e reconciliar o contexto e os blocos
  reservados. A própria `$specsfy-setup` não se chama recursivamente. Em uma
  transição automática, execute-a de novo com a mesma raiz já confirmada antes
  de carregar a skill de destino. Execute `$specsfy-documentator` quando
  `PACKAGES.md` estiver ausente ou desatualizado.
- Execute o monitor de contexto no início, após cada tarefa e antes de concluir
  a entrega; resolva todo resultado `PENDING`.
- Use as skills `specsfy-aux-*` para manter stack, regras e banco sem apagar
  conteúdo humano.
- Execute `$specsfy-documentator` depois de cada implementação para reconstruir
  a documentação técnica completa em `docs/` e o registro de dependências em
  `.specsfy/PACKAGES.md`.
- Use `specs/inbox/` para capturas imediatas ainda não refinadas.
- Use `specs/backlog/` para itens refináveis ainda não promovidos.
- Use `specs/<estado>/<NNNN>-<slug>/spec.md` como fonte normativa de cada
  fatia, em uma única pasta de estado.
- Não crie `plan.md`, `tasks.md`, `research.md` ou outra fonte normativa
  paralela.
<!-- specsfy:framework:end -->
