# Runbook de produção do LogiSync

Este runbook cobre a operação do frontend no Netlify ou, como contingência,
no GitHub Pages, da API no Render e do PostgreSQL gerenciado. Ele não contém credenciais. Valores sensíveis devem ser
fornecidos somente por variáveis protegidas nos provedores ou na sessão local.

## Topologia e sinais de saúde

| Componente | Contrato | Verificação |
| --- | --- | --- |
| Frontend | Netlify ou GitHub Pages publica `frontend/out` por HTTPS | abrir a URL pública e uma rota interna |
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
   Enquanto os deploys Netlify estiverem pausados, o workflow
   `.github/workflows/deploy-pages.yml` publica o mesmo diretório em
   `https://arthurdays.github.io/sistema-gestao-logistica/`, usando
   `GITHUB_PAGES=true` e `NEXT_PUBLIC_BASE_PATH=/sistema-gestao-logistica`.
3. No Render, crie o serviço web a partir de `backend/Dockerfile`, exponha a
   porta `8000` e configure o health check em `/health`.
4. Configure somente nos painéis protegidos:

   - `DATABASE_URL`;
   - `JWT_SECRET_KEY` com valor aleatório forte;
   - `CORS_ORIGINS` com as origens HTTPS exatas dos frontends ativos, separadas
     por vírgula e sem o subcaminho do GitHub Pages;
   - `FRONTEND_URL`;
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
     `SMTP_FROM_EMAIL`, `SMTP_TIMEOUT_SECONDS` e `SMTP_STARTTLS=true` para
     recuperação de senha;
   - `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` e
     `GOOGLE_OAUTH_REDIRECT_URI`, quando OAuth estiver habilitado;
   - `SENTRY_DSN` e `SENTRY_ENVIRONMENT`, quando Sentry estiver habilitado.

5. Não copie valores reais para `.env.example`, logs, issues, commits ou
   comandos compartilhados. O Sentry é opcional; sem DSN a API deve iniciar
   normalmente.

O runtime executa o Uvicorn com `--no-proxy-headers`: o bucket de origem do
login usa somente o peer de rede observado e não confia em cabeçalhos de origem encaminhados
pelo chamador. Um bloqueio do peer compartilhado nunca impede uma credencial
correta; o bloqueio por identidade continua sendo aplicado antes da autenticação.

### Recuperação de senha e SMTP

Use um servidor SMTP com STARTTLS na porta indicada pelo provedor e um
`SMTP_FROM_EMAIL` previamente autorizado. `SMTP_PASSWORD` é segredo e deve
existir somente no painel protegido do Render ou no `.env` local ignorado pelo
Git. `FRONTEND_URL` deve ser a origem HTTPS exata que receberá o parâmetro
efêmero `reset_token`. O timeout padrão é 1,5 segundo para preservar a resposta
rápida e neutra da API.

No ambiente local, copie os nomes de `.env.example`, preencha credenciais de
teste e execute `docker compose config` antes de iniciar os serviços. Confirme
que a seção `api.environment` contém os sete nomes SMTP, sem imprimir os
valores em logs ou anexá-los a evidências. Em produção, mantenha
`SMTP_STARTTLS=true`; desativá-lo só é aceitável em um transporte local isolado
que aplique TLS em outra camada documentada.

Para o smoke test, use uma conta sintética autorizada, solicite a recuperação
e confirme que chega exatamente um link HTTPS que permite uma única troca de
senha. A API retorna 202 e a mesma mensagem quando a conta não existe, o limite
foi atingido ou o transporte falhou. Se SMTP estiver ausente ou indisponível, o
token eventualmente criado é invalidado e o log registra apenas uma falha
sanitizada, sem e-mail, URL, token ou credencial.

Troubleshooting: valide resolução do host, porta, STARTTLS, autenticação e
autorização do remetente no painel do provedor. Depois, repita com conta
sintética e correlacione somente por `request_id`. Não aumente o timeout para
mascarar falhas e nunca copie a exceção completa para canais que possam expor
configuração sensível.

### Administração local de banco e BI

O Compose é exclusivamente um ambiente de desenvolvimento e administração
local. Antes de iniciá-lo, preencha `POSTGRES_PASSWORD`, `DOMAIN_APP_PASSWORD`,
`METABASE_APP_PASSWORD` e `METABASE_BI_PASSWORD` no `.env` com valores gerados
localmente; não há senha padrão. PostgreSQL e Metabase são publicados somente
em `127.0.0.1`, portanto DBeaver e o navegador local continuam funcionando sem
expor essas portas à rede.

A senha bootstrap do PostgreSQL é usada apenas pelo provisionador idempotente.
API, migrations e workers usam `DOMAIN_APP_USER`, papel separado sem
superusuário, criação de banco/roles ou replicação. Em uma base local já
existente, `database-init` também transfere a propriedade dos objetos do schema
`public` para esse papel antes de liberar a API.

O Metabase é uma ferramenta administrativa local e seu papel de leitura enxerga
o conjunto operacional completo. Ele não pode ser oferecido como dashboard
tenant-facing nem compartilhado com clientes. Uma interface BI tenant-facing
exige outra especificação, credenciais próprias por organização e isolamento
no banco (por exemplo, RLS), com testes de acesso cruzado antes da publicação.

## Gate antes de publicar

Uma versão só pode ser publicada quando o workflow `CI` estiver verde. O gate
executa contratos de produção, pytest, Ruff, mypy, lint, TypeScript e os builds
estáticos do Netlify e do GitHub Pages. Para reproduzir a parte declarativa localmente:

```powershell
pwsh -File infra/hosting/validate-production-config.ps1
docker compose --profile test run --rm api-tests
Set-Location frontend
npm ci
npm run lint
npm run test
$env:NETLIFY_STATIC_EXPORT = 'true'
npm run build
Remove-Item Env:NETLIFY_STATIC_EXPORT
$env:GITHUB_PAGES = 'true'
$env:NEXT_PUBLIC_BASE_PATH = '/sistema-gestao-logistica'
$env:NEXT_PUBLIC_API_URL = 'https://sistema-gestao-logistica.onrender.com'
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
2. Publique o commit aprovado. Netlify deve gerar o export estático quando os
   créditos estiverem disponíveis; o workflow `Deploy frontend to GitHub Pages`
   publica a contingência e o Render constrói a imagem do backend.
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
   ou execute novamente no GitHub Pages o artifact do commit anterior; depois,
   repita a navegação e o health check da API.
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
