# InNova Vitta+ — hardening e preparação para produção

## Alterações desta branch

- Datas e horários digitados na clínica são interpretados em `America/Sao_Paulo` e normalizados para UTC.
- Consultas diárias usam limites locais convertidos para UTC, com intervalo semiaberto [início, fim).
- Verificação de sobreposição deixa de usar aritmética de datetime específica do SQL e funciona nos dois dialetos suportados.
- Autocomplete de pacientes retorna somente identificador, nome e idade.
- Login usa usuários persistidos com hash de senha Werkzeug e vínculo explícito à clínica.
- RBAC centralizado com negação por padrão para endpoints não mapeados.
- Consultas ORM de entidades clínicas são filtradas pelo tenant ativo; novos registros recebem o tenant da sessão.
- Acesso e alteração a prontuários/consultas/receitas/exames geram eventos de auditoria sem conteúdo clínico.
- Login limitado a 5 tentativas por minuto e 20 por hora por combinação IP/identificador, além de 30 por hora por IP.
- Erros internos de persistência são registrados no log, sem exibir detalhes SQL ao usuário.
- Flask-Migrate está integrado para versionamento do schema.
- Testes unitários e workflow de CI foram adicionados.

## Variáveis obrigatórias

Configure no provedor de hospedagem, nunca no Git:

- `SECRET_KEY`: segredo aleatório forte (mínimo recomendado de 32 bytes).
- `RATELIMIT_STORAGE_URI`: Redis gerenciado em produção (compartilhado entre workers).
- `DEFAULT_TENANT_SLUG`: slug da clínica padrão usada no provisionamento inicial.
- `DATABASE_URL`: PostgreSQL gerenciado para produção.
- `DEBUG=False`.
- `SESSION_COOKIE_SECURE=True` quando servido exclusivamente por HTTPS.

Gere uma chave e um hash com:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('SENHA-FORTE-AQUI'))"
flask --app app create-user --username admin --email admin@seudominio.com --role admin --password-hash 'COLE_O_HASH_GERADO'
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

1. Revisar o mapa RBAC com a direção clínica e aplicar testes de autorização por rota, inclusive APIs e exportações.
2. Configurar Redis para que o rate limit seja distribuído entre todos os workers; memory:// serve apenas para desenvolvimento.
3. Estender a trilha de auditoria a exportações, downloads, relatórios e ações administrativas. A tabela é append-only na camada da aplicação, mas não substitui controles de imutabilidade no banco/backup.
4. Revisar chaves estrangeiras compostas por tenant para impedir referências cruzadas mesmo em operações SQL diretas.
5. Executar testes de integração PostgreSQL/Neon e concorrência real de agendamento; o bloqueio de linha do médico é aplicado no fluxo de criação, mas precisa ser validado sob carga.
6. Criar usuários/membros com processo de convite, recuperação de senha, MFA e desativação auditada.
7. Definir backup automatizado, retenção, restauração testada, monitoramento e resposta a incidentes.
8. Fazer avaliação LGPD com base legal, finalidade, minimização, retenção, direitos dos titulares e contratos com operadores.
9. Homologar staging com dados sintéticos, revisar migration e executar smoke tests antes de produção.

## Segunda etapa — identidade, RBAC e isolamento

A revisão `20261118_security_tenant` cria a clínica padrão, usuários, memberships e auditoria, adicionando `tenant_id` às nove tabelas clínicas existentes e atribuindo os registros legados à clínica padrão (id 1). Ela pressupõe que o schema legado já existe. Em banco vazio, crie/revise uma baseline antes de executar upgrade.

Após backup e homologação, execute `flask --app app db upgrade` e provisione o primeiro administrador com `flask --app app create-user --username ... --email ... --role admin --password-hash ...`. Não habilite autenticação persistente antes da migration e do provisionamento.

A sessão autenticada define o tenant ativo; o ORM aplica filtro global às entidades clínicas e atribui o tenant em novos registros. Dados sem tenant não são retornados em sessões autenticadas. A política RBAC nega endpoints desconhecidos a perfis não administrativos. O log registra metadados de acesso, nunca conteúdo de prontuário.

O rate limit usa memória por padrão apenas em desenvolvimento. Em produção configure `RATELIMIT_STORAGE_URI` com Redis compartilhado. Não há ainda interface de administração de usuários, MFA, fluxo de convite/recuperação, nem garantias de isolamento por constraints compostas para SQL direto.

## Critério de aceite

Esta branch é uma etapa de hardening, não uma certificação de conformidade nem uma declaração de prontidão para produção. Só promover após CI verde, revisão de migrations, testes de integração, validação de segurança e homologação clínica.
