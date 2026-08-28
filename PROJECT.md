# Projeto

## História e motivação

O LogiSync nasceu para reunir em uma única plataforma o controle operacional, financeiro e preventivo de veículos. O problema central é a fragmentação entre hodômetro, faturamento, combustível, despesas e manutenção, que impede conhecer o lucro líquido real da operação.

## Finalidade

Entregar uma visão auditável da operação logística por organização, veículo e período, incluindo custo e lucro por quilômetro, manutenção apropriada e alertas preventivos.

## Pessoas e contexto de uso

- **Operador**: registra fechamentos diários e consulta os veículos autorizados.
- **Gestor**: acompanha indicadores financeiros, frota e alertas.
- **Administrador**: configura a organização, usuários, catálogo técnico, integrações e regras.
- **Administrador técnico**: inspeciona banco, infraestrutura, BI e automações sem contornar a API de domínio.

## Capacidades principais

- Organizações e usuários isolados por tenant com autenticação JWT e OAuth Google configurável.
- OAuth vinculado ao navegador e trocado por código opaco de uso único; login por senha limitado por identidade e origem.
- Recuperação de senha por link HTTPS de uso único, com resposta pública neutra, expiração de 30 minutos e limite por identidade e origem.
- Cadastro de veículos e catálogo técnico sincronizado em modo somente leitura com Google Sheets.
- Fechamento operacional com validação de hodômetro e idempotência.
- Receitas, despesas, rentabilidade e custo de manutenção por quilômetro usando precisão decimal.
- Regras, execuções e alertas de manutenção com outbox e webhooks assinados para n8n.
- Dashboard responsivo, views read-only para Metabase e API documentada por OpenAPI.

## Limites

O MVP não inclui roteirização, despacho, GPS em tempo real, emissão fiscal, conciliação bancária, aplicativo móvel nativo nem previsão de falhas por aprendizado de máquina. Integrações escrevem somente pela API; n8n e Metabase não recebem escrita direta nas tabelas de domínio.

## Contexto técnico

O sistema usa Next.js/React no frontend, FastAPI/SQLAlchemy no backend, PostgreSQL como fonte de verdade e Docker Compose para execução local com banco e BI presos ao loopback. O frontend é exportado estaticamente no Netlify e o backend roda no Render; detalhes verificáveis ficam em `.specsfy/STACK.md`, `.specsfy/DATABASE.md` e `docs/`.
