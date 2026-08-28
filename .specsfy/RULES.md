# Regras do sistema

Estas regras complementam as instruções dos agentes sem substituir specs ou
critérios de aceite. Modelo inicial sugerido para **stack ainda não identificado**.

Confirme os manifests e as fronteiras principais antes de completar o modelo genérico.

## Arquitetura

## Código e qualidade

## Testes

## Segurança e privacidade

- Responder solicitações de recuperação sempre com HTTP 202 e mensagem neutra, independentemente de conta existente, limite atingido ou falha SMTP.

- Nunca persistir, registrar em log ou renderizar o token bruto de recuperação; persistir somente SHA-256 e remover reset_token da URL assim que capturado.

- Tokens de recuperação expiram em 30 minutos, são de uso único e devem ser invalidados por nova solicitação ou troca de senha.

- Limitar recuperação a três solicitações por hora por identidade e origem usando somente chaves HMAC persistidas.

## Operação

## Regras específicas do projeto
