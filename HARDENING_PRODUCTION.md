# InNova Vitta+ — hardening e preparação para produção

## Alterações desta branch

- Datas e horários digitados na clínica são interpretados em `America/Sao_Paulo` e normalizados para UTC.
- Consultas diárias usam limites locais convertidos para UTC, com intervalo semiaberto [início, fim).
- Verificação de sobreposição deixa de usar aritmética de datetime específica do SQL e funciona nos dois dialetos suportados.
- Autocomplete de pacientes retorna somente identificador, nome e idade.
- Login administrativo exige `ADMIN_PASSWORD_HASH`; senha em texto puro não é aceita.
- Erros internos de persistência são registrados no log, sem exibir detalhes SQL ao usuário.
- Flask-Migrate está integrado para versionamento do schema.
- Testes unitários e workflow de CI foram adicionados.

## Variáveis obrigatórias

Configure no provedor de hospedagem, nunca no Git:

- `SECRET_KEY`: segredo aleatório forte (mínimo recomendado de 32 bytes).
- `ADMIN_USERNAME`: usuário administrativo.
- `ADMIN_PASSWORD_HASH`: hash Werkzeug gerado localmente.
- `DATABASE_URL`: PostgreSQL gerenciado para produção.
- `DEBUG=False`.
- `SESSION_COOKIE_SECURE=True` quando servido exclusivamente por HTTPS.

Gere uma chave e um hash com:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('SENHA-FORTE-AQUI'))"
```

Não coloque a senha original no repositório, em logs ou em tickets. Se a senha já foi configurada em texto puro no provedor, substitua-a pelo hash e remova a variável antiga.

## Migrações do banco

Flask-Migrate foi registrado, mas nenhuma migração inicial foi gerada automaticamente nesta branch. Isso é intencional: a criação de uma baseline precisa ser feita contra uma cópia do banco real e revisada antes de produção.

Em ambiente de desenvolvimento com banco descartável:

```bash
flask --app app db init
flask --app app db migrate -m "initial schema"
flask --app app db upgrade
```

Revise e versione o diretório `migrations/`. Em banco que já contém tabelas, não execute uma migração inicial sem comparar o schema e fazer backup. A equipe deve decidir se a baseline será aplicada ou se o banco existente será marcado com `flask db stamp` após validação.

Não execute `db.create_all()` como substituto de migrations em produção.

## Atenção: registros de consulta já existentes

Versões anteriores interpretavam a hora digitada como UTC, embora a recepção trabalhe no horário de São Paulo. Os novos registros passam a ser armazenados corretamente em UTC. Registros históricos podem estar deslocados em três horas. Não aplique um UPDATE global: identifique origem, período e amostra de registros, faça backup e prepare uma migração de dados auditável antes de corrigir o histórico.

## Testes

Instale dependências de desenvolvimento e execute:

```bash
pip install -r requirements-dev.txt
pytest -q
```

O workflow GitHub Actions executa os testes unitários em Python 3.12. Os testes atuais cobrem conversão de fuso e limites de dia; ainda é necessário acrescentar testes de integração com PostgreSQL/SQLite, autenticação, CSRF, permissões e fluxos completos de agendamento.

## Pendências obrigatórias antes de produção

1. Implementar usuários persistidos e RBAC real por clínica/profissional; hoje a autenticação ainda usa um único usuário administrativo de ambiente.
2. Adicionar rate limiting de login distribuído (Redis ou serviço equivalente) e política de bloqueio/alerta.
3. Revisar todos os endpoints JSON e serializers para privilégio mínimo; prontuário e dados de saúde são dados pessoais sensíveis.
4. Adicionar trilha de auditoria imutável para leitura/alteração de prontuários, exportações e ações administrativas.
5. Validar isolamento multi-clínica (tenant_id) antes de oferecer SaaS multi-tenant.
6. Adicionar testes de integração e concorrência para evitar dupla reserva em requisições simultâneas; considerar restrição/lock transacional por médico e janela.
7. Definir backup automatizado, retenção, restauração testada, monitoramento e plano de resposta a incidentes.
8. Fazer avaliação LGPD com base legal, finalidade, minimização, retenção, direitos dos titulares e contratos com operadores.
9. Validar deploy real em staging com PostgreSQL, HTTPS, variáveis e smoke tests.

## Critério de aceite

Esta branch é uma etapa de hardening, não uma certificação de conformidade nem uma declaração de prontidão para produção. Só promover após CI verde, revisão de migrations, testes de integração, validação de segurança e homologação clínica.
