# Checklist de publicação do repositório

Este documento separa o que pertence ao produto do que deve permanecer apenas
na máquina de desenvolvimento. Ele não contém valores de ambiente nem
credenciais.

## Conteúdo que deve ser versionado

| Pasta ou arquivo | Motivo para publicar |
| --- | --- |
| `backend/` | API, domínio, migrations Alembic e testes automatizados. |
| `frontend/` | Aplicação Next.js, componentes, rotas e manifests npm. |
| `infra/` | Inicialização idempotente do PostgreSQL e configuração de infraestrutura. |
| `docs/` | Arquitetura, operação, segurança, deploy e este checklist. |
| `specs/`, `.specsfy/` e `specs.md` | Fonte normativa e painel do ciclo Specsfy 2.0. |
| `.agents/` e `skills-lock.json` | Skills e correções do harness usadas para reproduzir o fluxo do projeto. |
| `.github/` | Automação de integração contínua. |
| `.vscode/tasks.json` | Atalho versionado para abrir o painel Specsfy. |
| `docker-compose.yml`, `netlify.toml` e Dockerfiles | Construção, execução e publicação dos serviços. |
| `.env.example` | Nomes das variáveis e exemplos não secretos para configuração. |
| `spec-kit` | Ponteiro do submódulo usado pelo processo de especificação. |

## Conteúdo que não deve ser versionado

- `.env` e qualquer variante real de ambiente.
- JSON baixado do Google com `client_secret`, credenciais ou service account.
- Chaves privadas, certificados pessoais e tokens de acesso.
- `node_modules/`, `.next/`, `out/`, `build/` e `dist/`.
- `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/` e `.ruff_cache/`.
- Cobertura, logs, relatórios locais e arquivos temporários.
- Bancos SQLite/DB locais e arquivos específicos do sistema operacional ou IDE.

Esses padrões estão protegidos por `.gitignore` e `.dockerignore`. Se um
segredo já tiver sido publicado no histórico, ignorá-lo não é suficiente: a
credencial precisa ser revogada e substituída.

## Antes de cada commit

- [ ] Confirmar que a branch está sincronizada com `origin/main`.
- [ ] Revisar `git status`, `git diff --check` e a lista exata de arquivos.
- [ ] Confirmar que `.env`, credenciais e dados reais não estão rastreados.
- [ ] Executar testes, lint, tipagem e build das camadas alteradas.
- [ ] Aplicar migrations em banco descartável e verificar o rollback previsto.
- [ ] Reconstruir a documentação e atualizar o painel Specsfy.
- [ ] Escrever título e descrição do commit em português, resumindo cada pasta.

## Antes do deploy

- [ ] Publicar a revisão aprovada em `origin/main` sem reescrever o histórico.
- [ ] Confirmar no Render as variáveis obrigatórias sem revelar seus valores.
- [ ] Trocar qualquer segredo que tenha aparecido em captura de tela ou log.
- [ ] Confirmar que a migration Alembic chegou ao `head` no PostgreSQL.
- [ ] Validar `/health` e os logs de inicialização do backend.
- [ ] Aguardar o build do Netlify e validar as rotas `/`, `/catalogo`,
      `/financeiro` e `/frota`.
- [ ] Testar login por senha, Google OAuth, logout e troca de organização.
- [ ] Confirmar que o código OAuth não permanece na URL ou no histórico.
- [ ] Fazer um teste funcional de cadastro sem usar dados pessoais reais.
- [ ] Registrar resultado, revisão publicada e procedimento de rollback.
