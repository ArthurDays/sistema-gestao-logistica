# Fluxos operacionais

## Cadastro pelo catálogo

```mermaid
sequenceDiagram
    actor O as Operador
    participant W as Next.js
    participant A as FastAPI
    participant D as PostgreSQL
    participant S as Google Sheets
    S->>A: CSV técnico
    A->>D: Upsert do catálogo
    O->>W: Seleciona modelo, placa e KM
    W->>A: POST /vehicle-catalog/{id}/register
    A->>D: Cria veículo e regras preventivas
    A-->>W: Veículo cadastrado
    W-->>O: Abre primeiro fechamento
```

## Fechamento diário

1. O frontend seleciona um veículo ativo e exibe o hodômetro inicial somente para leitura.
2. O operador informa hodômetro final, receita e opcionalmente combustível.
3. A API bloqueia o veículo, valida progressão e calcula distância/custos.
4. Operação e novo hodômetro são persistidos na mesma transação.
5. O dashboard recarrega os agregados.

## Manutenção preventiva

```mermaid
stateDiagram-v2
    [*] --> Programada
    Programada --> Atenção: entra na janela de aviso
    Atenção --> Crítica: prazo ou KM vencido
    Programada --> Executada: serviço antecipado
    Atenção --> Executada: serviço registrado
    Crítica --> Executada: serviço registrado
    Executada --> Programada: próximo vencimento
```

Alertas a menos de 500 km são urgentes. Registrar uma execução encerra o ciclo atual e estabelece a nova referência.

## Páginas

| Página | Decisão suportada |
|---|---|
| Dashboard | Resultado e saúde da operação |
| Financeiro | Composição dos custos por período |
| Frota | Veículo, hodômetro e manutenção |
| Catálogo | Referência técnica e cadastro |
