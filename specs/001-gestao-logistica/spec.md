# Especificação Funcional: Gestão Logística e Controle Operacional

**Feature**: `001-gestao-logistica`  
**Status**: Aprovável para planejamento  
**Criada em**: 2026-08-17

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

## Métricas de sucesso

- Um operador consegue registrar uma operação diária em até 2 minutos.
- O lucro líquido real é disponível para qualquer veículo e período com dados cadastrados.
- Alertas críticos são publicados ao n8n em até 1 minuto após a condição ser identificada.
- Reenvios de eventos de integração não criam duplicidade de dados.

## Premissas a validar antes da implementação

1. Critério padrão de rateio para custos fixos: por km, por dia ou configurável por despesa.
2. Fonte autorizada para preços de combustíveis e granularidade de localização.
3. Canal inicial de notificação do n8n: e-mail, WhatsApp ou Telegram.
4. Modelo de autenticação do MVP: e-mail/senha com JWT ou provedor de identidade externo.
