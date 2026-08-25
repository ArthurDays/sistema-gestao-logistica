# Runbook de produção do LogiSync

Este runbook cobre a operação do frontend no Netlify, da API no Render e do
PostgreSQL gerenciado. Ele não contém credenciais. Valores sensíveis devem ser
fornecidos somente por variáveis protegidas nos provedores ou na sessão local.

## Topologia e sinais de saúde

| Componente | Contrato | Verificação |
| --- | --- | --- |
| Frontend | Netlify publica `frontend/out` por HTTPS | abrir a URL pública e uma rota interna |
| API | Render executa `backend/Dockerfile` | `GET <BACKEND_URL>/health` retorna `{"status":"ok"}` |
| Banco | PostgreSQL é a fonte de verdade | migrations concluem antes do Uvicorn iniciar |
| Observabilidade | logs JSON usam `request_id`; Sentry é opcional | correlacionar resposta e log por `X-Request-ID` |

As URLs públicas canônicas ficam em
`infra/hosting/production.env.example`. Uma instância gratuita do Render pode
hibernar; antes de classificar o primeiro timeout como incidente, aguarde o
cold start e repita o health check com um novo `X-Request-ID`.

## Configuração inicial

1. Execute o validador do contrato público:

   ```powershell
   pwsh -File infra/hosting/validate-production-config.ps1 `
     -Path infra/hosting/production.env.example
   ```

2. No Netlify, use o `netlify.toml` versionado e configure
   `NEXT_PUBLIC_API_URL` com a URL HTTPS da API. O build usa
   `NETLIFY_STATIC_EXPORT=true`, base `frontend` e publica `out`.
3. No Render, crie o serviço web a partir de `backend/Dockerfile`, exponha a
   porta `8000` e configure o health check em `/health`.
4. Configure somente nos painéis protegidos:

   - `DATABASE_URL`;
   - `JWT_SECRET_KEY` com valor aleatório forte;
   - `CORS_ORIGINS` com a origem HTTPS exata do frontend;
   - `FRONTEND_URL`;
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e
     `GOOGLE_OAUTH_REDIRECT_URI`, quando OAuth estiver habilitado;
   - `SENTRY_DSN` e `SENTRY_ENVIRONMENT`, quando Sentry estiver habilitado.

5. Não copie valores reais para `.env.example`, logs, issues, commits ou
   comandos compartilhados. O Sentry é opcional; sem DSN a API deve iniciar
   normalmente.

## Gate antes de publicar

Uma versão só pode ser publicada quando o workflow `CI` estiver verde. O gate
executa contratos de produção, pytest, Ruff, mypy, lint, TypeScript e o build
estático do Netlify. Para reproduzir a parte declarativa localmente:

```powershell
pwsh -File infra/hosting/validate-production-config.ps1
docker compose --profile test run --rm api-tests
Set-Location frontend
npm ci
npm run lint
npm run test
$env:NETLIFY_STATIC_EXPORT = 'true'
npm run build
```

Confirme que o diff não contém segredos e que qualquer migration possui teste.
Antes de uma mudança de schema ou operação de risco, gere um backup e valide a
restauração isolada conforme a próxima seção.

## Backup e restauração isolada

Pré-requisitos: PowerShell 7, `pg_dump` e `pg_restore` compatíveis com o
PostgreSQL 18. Use variáveis protegidas; não imprima URLs de banco.

### Gerar e validar o backup

```powershell
$env:DATABASE_URL = '<origem-protegida>'
pwsh -File infra/postgres/backup.ps1 `
  -BackupDirectory '<diretorio-seguro>' `
  -RetentionDays 7
```

O comando só aceita dump customizado não vazio, grava um checksum SHA-256 e
remove apenas arquivos `logistica-*.dump*` mais antigos no diretório informado.
Copie o dump e o `.sha256` para armazenamento criptografado fora do host.

### Provar a recuperação

Crie um banco temporário vazio e diferente da origem. Em seguida:

```powershell
$env:DATABASE_URL = '<origem-protegida>'
$env:RESTORE_DATABASE_URL = '<banco-isolado-descartavel>'
pwsh -File infra/postgres/restore-check.ps1 `
  -BackupPath '<diretorio-seguro>/logistica-AAAAmmddTHHMMSSZ.dump'
```

Após a restauração, conecte-se ao destino isolado, confirme a migration atual e
execute uma consulta de leitura representativa. Registre horário, checksum,
resultado e responsável sem registrar URLs ou credenciais. Só então remova o
banco descartável. Nunca defina `RESTORE_DATABASE_URL` com a URL da origem; o
script rejeita URLs idênticas.

## Deploy e verificação

1. Confirme CI verde e backup restaurável quando aplicável.
2. Publique o commit aprovado. Netlify deve gerar o export estático e o Render
   deve construir a imagem do backend.
3. No Render, acompanhe `alembic upgrade head`; o Uvicorn só inicia depois que
   a migration termina com sucesso.
4. Verifique `GET <BACKEND_URL>/health` e anote o `X-Request-ID` da resposta.
5. Abra o frontend, autentique com uma conta de teste autorizada e confirme uma
   leitura da API. Não use dados pessoais ou financeiros reais em smoke tests.
6. Confirme que CORS aceita apenas a origem publicada e que logs não exibem
   `authorization`, `cookie`, `password`, `secret`, `token`, `database_url` ou
   `dsn`.

## Rollback

1. Suspenda novas publicações e registre o commit, horário, sintomas e
   `request_id` afetado.
2. Se somente o frontend falhou, restaure no Netlify o deploy anterior aprovado
   e repita a navegação e o health check da API.
3. Se a API falhou sem mudança incompatível de schema, faça redeploy no Render
   do commit anterior aprovado e repita `/health` e o smoke test.
4. Se houve migration incompatível, não execute downgrade ou restauração sobre
   a origem por impulso. Isole o tráfego, preserve o banco atual, restaure o
   último backup validado em um banco novo e verifique os dados antes de trocar
   a conexão. A troca de banco exige autorização explícita do responsável.
5. Depois do rollback, mantenha a versão defeituosa bloqueada até que CI e a
   simulação de recuperação passem novamente.

## Resposta a incidentes

1. Classifique o alcance: frontend, API, banco, OAuth, catálogo ou integração.
2. Consulte `/health`. Em cold start, aguarde a inicialização e repita uma vez.
3. Correlacione a falha pelos campos JSON `request_id`, `level`, `logger` e
   `message`; use Sentry apenas se estiver configurado.
4. Revogue e substitua imediatamente qualquer segredo que possa ter sido
   exposto. Não copie o valor para o ticket do incidente.
5. Para corrupção ou indisponibilidade do banco, preserve a origem e execute a
   restauração isolada. Para perda de dados confirmada, siga o rollback com
   banco novo e autorização explícita.
6. Registre causa, impacto, período, versão, evidência de recuperação e ação
   preventiva. Confirme novamente frontend, `/health`, autenticação e uma
   leitura autorizada antes de encerrar.

## Evidência mínima por operação

- commit ou versão publicada;
- resultado do CI;
- horário e resultado do health check;
- `request_id` de smoke test, sem token;
- nome do arquivo de backup, tamanho e checksum, quando aplicável;
- nome do banco descartável e resultado da restauração, sem URL;
- decisão de deploy, rollback ou recuperação e responsável.
