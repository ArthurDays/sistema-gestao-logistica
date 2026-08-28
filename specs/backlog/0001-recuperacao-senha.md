# Backlog: Recuperação e redefinição segura de senha

| Metainformação | Valor |
| --- | --- |
| ID | BACKLOG-0001 |
| Status | Promoted |
| Produto | LogiSync |
| Épico | Autenticação e acesso |
| Funcionalidade | Recuperação de senha |
| Tipo | Funcionalidade de segurança |
| Prioridade | Alta — necessária antes do cadastro público |
| Milestones | Produção segura |
| Criado em | 2026-08-26 |
| Spec promovida | `specs/completed/0003-recuperacao-senha/spec.md` |

## Ideia original

Permitir que usuários recuperem o acesso sem intervenção administrativa quando esquecerem a senha.

## Problema percebido

Usuários autenticados por senha ficam sem acesso ao esquecer a credencial e dependem de suporte manual.

## Pessoa afetada ou beneficiada

Usuário ativo do LogiSync cadastrado com e-mail e senha.

## Resultado ou valor esperado

Solicitar um link seguro, definir uma nova senha e voltar a entrar sem revelar se a conta existe.

## Contexto

Complementa o login existente do frontend Netlify e a API FastAPI no Render, preservando Google OAuth e isolamento por organização.

## Referências relacionadas

- `specs/inbox/2026-08-26-173953-recuperacao-e-redefinicao-segura-de-senha.md` — captura de origem.
- `specs/completed/0001-gestao-logistica/spec.md` — cadastro, login e isolamento por organização já entregues.
- `specs/completed/0002-operacao-producao-gerenciada/spec.md` — tokens opacos, limitação de abuso e proteção de segredos que devem ser preservados.
- `frontend/components/operations-dashboard.tsx` — formulário atual de autenticação a ser ampliado.
- `backend/app/api.py`, `backend/app/auth.py` e `backend/app/core/security.py` — contratos atuais de autenticação.

## Comportamento esperado

1. Na tela de login, a pessoa escolhe `Esqueci minha senha` e informa o e-mail.
2. A API responde sempre com a mesma mensagem de aceite, exista ou não uma conta ativa.
3. Para conta ativa, a API cria um token aleatório de uso único, persiste somente seu hash e solicita o envio de um link HTTPS ao e-mail cadastrado.
4. O link abre a tela de nova senha, que exige no mínimo 12 caracteres e confirmação idêntica.
5. A API aceita somente token válido, não expirado e ainda não utilizado; após a troca, invalida todos os tokens pendentes do usuário.
6. A pessoa volta ao login e entra com a nova senha; Google OAuth permanece inalterado.

## Regras de negócio

- Tokens expiram em 30 minutos, são aleatórios, de uso único e nunca são armazenados ou registrados em texto claro.
- A resposta da solicitação não revela se o e-mail existe, está ativo ou usa Google OAuth.
- Solicitações são limitadas por identidade e origem, reutilizando o padrão hash-only do login; no máximo três solicitações por hora para cada escopo.
- Uma nova solicitação invalida tokens anteriores ainda pendentes do mesmo usuário.
- A senha nova exige de 12 a 128 caracteres e não pode coincidir com a senha atual.
- A redefinição bem-sucedida invalida todos os tokens de recuperação ainda pendentes.
- O transporte de e-mail é configurável por SMTP com TLS; credenciais ficam somente no ambiente e o provedor pode ser trocado sem mudar o contrato da API.
- Em ambiente sem transporte configurado, a API mantém resposta uniforme e não registra nem devolve o token.

## Critérios de aceitação

```gherkin
Scenario: solicitar recuperação de uma conta ativa
  Given uma conta ativa cadastrada por e-mail e senha
  When a pessoa solicita recuperação
  Then recebe uma resposta neutra e o sistema envia um link HTTPS com token temporário
```

```gherkin
Scenario: não revelar uma conta inexistente
  Given um e-mail não cadastrado
  When a pessoa solicita recuperação
  Then recebe a mesma resposta e latência equivalente sem criação de token
```

```gherkin
Scenario: redefinir a senha uma única vez
  Given um token válido ainda não utilizado
  When a pessoa informa uma senha nova válida e sua confirmação
  Then a senha é alterada, o token é invalidado e uma segunda tentativa é rejeitada
```

```gherkin
Scenario: rejeitar token expirado ou excesso de solicitações
  Given um token expirado ou o limite de solicitações atingido
  When a pessoa tenta continuar a recuperação
  Then o sistema rejeita a operação com mensagem segura e não altera a senha
```

## Qualidades e operação

- Segurança: token com entropia criptográfica, hash SHA-256, expiração, consumo transacional e limitação de abuso.
- Privacidade: resposta uniforme e ausência de e-mail, token ou segredo nos logs.
- Desempenho e volume: solicitação responde em até dois segundos sem aguardar indefinidamente o provedor; timeout SMTP limitado.
- Auditoria e observabilidade: registrar somente evento, resultado genérico, request ID e falha técnica sanitizada.

## Dependências

- Migration Alembic para a tabela de tokens de recuperação.
- Transporte SMTP TLS configurado no Render para envio real em produção.
- URL pública do frontend para formar o link de redefinição.

## Situações de erro

- E-mail inexistente ou usuário inativo: resposta neutra sem token.
- Provedor indisponível: resposta neutra, falha sanitizada e token não utilizável.
- Token inválido, expirado ou consumido: mensagem genérica e senha inalterada.
- Senhas divergentes, fracas ou iguais à atual: validação rejeita sem consumir o token.
- Concorrência no consumo: somente uma transação pode concluir a troca.

## Escopo

- Dentro: solicitação, envio, tela de nova senha, redefinição, limitação de abuso, migration, testes e documentação operacional.
- Fora: troca de e-mail, autenticação multifator, recuperação por telefone, painel administrativo para alterar senha e encerramento global de JWT já emitido.

## Dúvidas, decisões e riscos

- Decisão reversível: usar contrato SMTP TLS, evitando acoplamento do domínio a um provedor comercial específico.
- Risco: credenciais SMTP e domínio remetente ainda precisam ser configurados no Render antes do envio real em produção.
- Nenhuma lacuna aplicável impede a especificação; o provedor concreto é decisão operacional externa ao comportamento.

## Pronto para desenvolvimento

- [x] O problema e a pessoa beneficiada estão claros.
- [x] O evento inicial e o resultado esperado estão claros.
- [x] Permissões, regras e exceções relevantes estão claras.
- [x] O resultado pode ser verificado objetivamente.
- [x] Segurança, privacidade e desempenho foram avaliados conforme o risco.
- [x] Fora de escopo, dependências e decisões pendentes estão registrados.

## Próximo passo

Ciclo concluído na `SPEC-0003`; nenhuma ação normativa pendente para este backlog.
