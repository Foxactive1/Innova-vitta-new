# Diagrama de Casos de Uso — Clínica Vida+

## Atores
1. **Secretária** — Responsável pelo cadastro e agendamentos
2. **Médico** — Realiza atendimentos e emite receitas
3. **Paciente** — Recebe atendimento (actor externo)
4. **Sistema** — Automatiza processos

## Casos de Uso

### Secretária
- UC01: Cadastrar Paciente
- UC02: Cadastrar Médico
- UC03: Agendar Consulta
- UC04: Confirmar Consulta
- UC05: Cancelar Consulta
- UC06: Agendar Exame
- UC07: Registrar Pagamento
- UC08: Buscar Paciente
- UC09: Listar Pacientes
- UC10: Gerar Relatório Mensal

### Médico
- UC11: Realizar Atendimento
- UC12: Registrar Diagnóstico
- UC13: Registrar Evolução
- UC14: Emitir Receita
- UC15: Cancelar Consulta (própria)
- UC16: Visualizar Histórico do Paciente

### Sistema (automático)
- UC17: Verificar Disponibilidade de Horário
- UC18: Gerar Receita Automaticamente (quando há prescrição)
- UC19: Verificar Controle de Acesso (expressões lógicas)
- UC20: Exportar Dados (JSON/CSV)

## Relacionamentos
- <<include>>: Agendar Consulta → Verificar Disponibilidade
- <<include>>: Realizar Atendimento → Gerar Receita (se prescrição)
- <<extend>>: Cancelar Consulta ← Notificar Paciente
