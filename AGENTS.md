# Instruções para agentes do projeto

## Fluxo obrigatório

1. Leia `specs/001-gestao-logistica/spec.md` antes de propor alteração funcional.
2. Atualize ou consulte `specs/001-gestao-logistica/plan.md` antes de iniciar mudança estrutural.
3. Execute uma tarefa limitada por vez e valide-a antes de seguir.
4. Registre decisões relevantes nos documentos de especificação ou plano.

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
