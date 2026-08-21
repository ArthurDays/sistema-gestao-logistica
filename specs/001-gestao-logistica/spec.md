# Especificação Funcional: Gestão Logística e Controle Operacional

**Feature**: `001-gestao-logistica`  
**Status**: Aprovável para planejamento  
**Criada em**: 2026-08-17
**Nome do produto**: `LogiSync`

## Objetivo

Disponibilizar uma plataforma web para operadores e gestores controlarem veículos, operação, receitas, custos e manutenções. O resultado central é o **lucro líquido real** por veículo e período, incluindo o rateio do desgaste e manutenção por quilômetro rodado.

O produto deve servir desde um entregador com uma moto até frotas de caminhões, ônibus, carros e bicicletas.

## Fora do escopo do MVP

- Roteirização e despacho de entregas.
- Rastreamento GPS em tempo real.
- Emissão fiscal e conciliação bancária.
- Aplicativos móveis nativos.
- Previsão de falhas por aprendizado de máquina.

## Histórias de usuário

### US-001 — Registrar operação diária (P1)

Como operador, quero registrar a quilometragem e o faturamento de um veículo para acompanhar o resultado diário da operação.

**Teste independente**: registrar uma operação válida e consultar o resumo financeiro do dia.

**Cenários de aceite**:

1. Dado um veículo ativo com hodômetro em 10.000 km, quando o operador registra hodômetro final de 10.120 km e receita de R$ 350,00, então o sistema registra 120 km e recalcula os indicadores do veículo.
2. Dado o último hodômetro validado de 10.000 km, quando o operador informa 9.999 km, então o sistema rejeita o lançamento e explica a inconsistência.
3. Dado um lançamento já recebido com a mesma chave de idempotência, quando ele é reenviado, então nenhuma operação ou receita duplicada é criada.

### US-002 — Apurar lucro líquido real (P1)

Como gestor, quero consultar a rentabilidade de um veículo por período para tomar decisões com base no custo total, não apenas no combustível.

**Teste independente**: cadastrar receita, combustível e uma regra de manutenção; consultar o demonstrativo do período.

**Cenários de aceite**:

1. Dada uma receita de R$ 350,00, combustível de R$ 70,00 e custo de manutenção rateado de R$ 15,00, quando o período é calculado, então o lucro líquido real é R$ 265,00.
2. Dada uma despesa compartilhada pela frota, quando houver critério de rateio configurado, então sua parcela é incluída somente nos veículos e períodos aplicáveis.

### US-003 — Controlar manutenção e receber alertas (P1)

Como gestor, quero cadastrar regras de manutenção e receber alertas próximos ao vencimento para evitar indisponibilidade do veículo.

**Teste independente**: cadastrar uma regra por km, aproximar o hodômetro do limite e confirmar a criação do alerta.

**Cenários de aceite**:

1. Dada uma troca de óleo a cada 5.000 km com alerta de atenção a 500 km, quando faltarem 500 km, então o sistema gera um alerta de atenção.
2. Dada uma manutenção vencida, quando o alerta é criado ou torna-se crítico, então um evento idempotente é disponibilizado para o n8n.
3. Dada a manutenção registrada como executada, quando o histórico é salvo, então o próximo vencimento é recalculado e o alerta aberto é encerrado.

### US-004 — Administrar veículos e dados técnicos (P1)

Como administrador, quero cadastrar e manter as especificações dos veículos para que consumo e manutenção sejam calculados adequadamente.

### US-005 — Importar dados por automação (P2)

Como administrador, quero que o n8n envie dados técnicos e preços de combustível pela API para reduzir cadastro manual, mantendo origem e auditoria.

### US-006 — Visualizar indicadores gerenciais (P2)

Como gestor, quero filtros por veículo, categoria e período para analisar KM, receitas, custos, lucro e alertas.

**Cenários de aceite**:

1. Dado um dispositivo móvel com largura de 360 px, quando o gestor acessa o painel, então os indicadores, formulários e listas permanecem legíveis, sem rolagem horizontal, e as áreas principais ficam acessíveis pela navegação inferior.
2. Dado um tablet ou desktop, quando o gestor acessa o mesmo painel, então a navegação e os cartões aproveitam o espaço disponível sem ocultar funcionalidades.

### US-007 — Criar uma organização e acessar a plataforma (P1)

Como responsável por uma nova operação, quero cadastrar minha empresa e meu acesso para começar a usar o LogiSync como administrador.

**Teste independente**: cadastrar uma organização com e-mail ainda não utilizado, receber uma sessão autenticada e consultar os dados do novo tenant.

**Cenários de aceite**:

1. Dado um nome de organização, e-mail válido e senha com pelo menos 12 caracteres, quando o cadastro é concluído, então o sistema cria a organização, cria o primeiro usuário com papel administrador e devolve uma sessão autenticada desse tenant.
2. Dado um e-mail já cadastrado, quando um novo cadastro é enviado, então o sistema responde conflito e não deixa uma organização órfã no banco.
3. Dado um cadastro com senha abaixo do mínimo, quando a solicitação é enviada, então o sistema rejeita os dados sem criar organização ou usuário.

## Requisitos funcionais

- **FR-001**: O sistema deve isolar os dados por organização, mesmo que o MVP opere inicialmente com uma única organização.
- **FR-002**: O sistema deve cadastrar veículos com categoria, identificação, energia/combustível, capacidade, consumo, hodômetro e status.
- **FR-003**: O sistema deve suportar energia gasolina, etanol, diesel, GNV, elétrico, híbrido, humano e outro.
- **FR-004**: O sistema deve registrar operações, receitas e despesas com data, valor, veículo quando aplicável, origem e usuário responsável.
- **FR-005**: O sistema deve impedir regressão de hodômetro, exceto ajuste autorizado e auditado.
- **FR-006**: O sistema deve categorizar despesas como combustível/energia, manutenção preventiva, corretiva, pneus, óleo, peças, pedágio, seguro, impostos, lavagem, financiamento/aluguel e outras.
- **FR-007**: O sistema deve calcular faturamento, custos variáveis, custos fixos rateados, custo por km, receita por km, margem e lucro líquido real.
- **FR-008**: O custo de manutenção previsto deve ser apropriado proporcionalmente à quilometragem desde a última manutenção válida.
- **FR-009**: O sistema deve cadastrar regras preventivas por veículo ou categoria, acionadas por km, data ou ambos.
- **FR-010**: O sistema deve manter histórico de manutenções executadas e recalcular os próximos vencimentos.
- **FR-011**: O sistema deve gerar alertas informativo, atenção e crítico e publicar eventos de alerta para o n8n.
- **FR-012**: A API de integrações deve ser autenticada, idempotente e registrar fonte, payload e data de coleta.
- **FR-013**: O sistema deve armazenar preços de combustível/energia com localidade, vigência e fonte; períodos históricos não podem mudar por atualizações futuras.
- **FR-014**: O sistema deve disponibilizar agregados para os painéis React e Metabase.
- **FR-015**: O sistema deve registrar auditoria para alterações financeiras, de hodômetro e de manutenção.
- **FR-016**: O frontend LogiSync deve adaptar navegação, ícones, cartões, formulários, tabelas e painéis laterais para celular, tablet e desktop, preservando as mesmas operações e regras de autorização.
- **FR-017**: O sistema deve permitir o cadastro público de uma nova organização, criar atomicamente seu primeiro usuário administrador e autenticar esse usuário após o sucesso, sem permitir reutilização de e-mail.

## Entidades-chave

- **Organization**: empresa ou operação isolada.
- **User**: pessoa autenticada, com papel operacional, gestor ou administrador.
- **Vehicle**: ativo operacional e suas características técnicas.
- **OperationalRecord**: operação diária, com KM, receita e dados do lançamento.
- **Revenue / Expense**: lançamentos financeiros auditáveis.
- **MaintenanceRule / MaintenanceExecution**: política preventiva e sua execução.
- **MaintenanceAlert**: alerta de vencimento e respectivo estado.
- **FuelPrice**: preço externo com vigência e fonte.
- **OutboxEvent**: evento confiável para entrega ao n8n.

## Requisitos não funcionais

- Valores monetários usam precisão decimal; ponto flutuante é proibido no cálculo financeiro.
- Horários são armazenados em UTC; cada organização possui fuso configurável.
- As operações de escrita das integrações usam chave de idempotência.
- A API deve documentar seus contratos via OpenAPI.
- O dashboard mensal de até 100 veículos deve responder em até 3 segundos no ambiente de referência.
- Alterações de schema são feitas por migrations versionadas, nunca manualmente pelo DBeaver em produção.
- A interface web deve ser utilizável a partir de 360 px de largura, sem rolagem horizontal na página, com alvos de toque de pelo menos 44 px e navegação móvel fixa que respeite as áreas seguras do dispositivo.

## Métricas de sucesso

- Um operador consegue registrar uma operação diária em até 2 minutos.
- O lucro líquido real é disponível para qualquer veículo e período com dados cadastrados.
- Alertas críticos são publicados ao n8n em até 1 minuto após a condição ser identificada.
- Reenvios de eventos de integração não criam duplicidade de dados.

## Premissas a validar antes da implementação

1. Critério padrão de rateio para custos fixos: por km, por dia ou configurável por despesa.
2. **Decidido em 2026-08-20**: a fonte autorizada de preços de combustíveis é a ANP, com localidade inicial Brasília/DF.
3. **Decidido em 2026-08-20**: o n8n encaminhará alertas pelos canais e-mail e WhatsApp.
4. **Decidido em 2026-08-18**: e-mail/senha com JWT assinado por chave de ambiente; os papéis iniciais são operador, gestor e administrador.
5. Pendências de implantação a definir ao final: domínio/provedor de DNS e TLS, destino dos backups criptografados e DSN do Sentry.
6. **Decidido em 2026-08-20**: o nome do produto é LogiSync; a identidade usa azul-marinho, azul elétrico, cartões claros, ícones lineares e navegação inferior no web app móvel, mantendo sidebar no desktop.
7. **Decidido em 2026-08-20**: o cadastro inicial cria um tenant novo e seu primeiro administrador em uma única transação. Login Google será uma fatia posterior e somente será ativado após definição das credenciais OAuth, URLs de callback e política de vinculação de contas.
