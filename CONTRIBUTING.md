# Como contribuir

1. Leia `AGENTS.md`, a linha de base em `specs/completed/0001-gestao-logistica/spec.md` e a spec ativa aplicável.
2. Registre mudanças funcionais e estruturais na `spec.md` integrada do Specsfy 2.0.
3. Trabalhe em uma branch curta e mantenha commits focados.
4. Inclua migration e teste ao alterar persistência ou regra de negócio.
5. Atualize a documentação afetada.

## Validação

```powershell
docker compose --profile test run --rm api-tests
docker compose build frontend
docker compose up -d --wait
```

- Nunca use `float` para dinheiro.
- Nunca versione `.env`, tokens, dumps ou dados reais.
- Não permita escrita direta do n8n nas tabelas.
- Preserve idempotência e auditoria financeira.
- Comente decisões não óbvias; evite repetir o código em comentários.
