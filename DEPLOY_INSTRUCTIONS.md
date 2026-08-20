# InNova Vitta+ — Instruções de Deploy

## Passo 1 — Substituir arquivos no repositório

Copie os arquivos desta pasta para a raiz do projeto:

```
requirements.txt   ← substitui o atual
runtime.txt        ← novo
.gitignore         ← novo
.env.example       ← novo
railway.toml       ← novo
render.yaml        ← novo
config.py          ← substitui o atual (SECRET_KEY segura)
```

## Passo 2 — Commitar a pasta routes/ (CRÍTICO)

```bash
git add routes/
git add requirements.txt runtime.txt .gitignore .env.example
git add railway.toml render.yaml config.py
git commit -m "fix: adiciona routes/, gunicorn e configs de deploy"
git push origin main
```

## Passo 3 — Variáveis de ambiente na plataforma

### Railway
No painel do projeto → Variables → adicionar:
```
SECRET_KEY=<gere com: python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=<gerado automaticamente ao adicionar PostgreSQL plugin>
DEBUG=False
```

### Render
O render.yaml já configura automaticamente. Apenas confirme o deploy.

## Passo 4 — Verificar SQLite → PostgreSQL

O `config.py` agora aceita `DATABASE_URL` do ambiente.
Em produção, **não use SQLite** — dados são perdidos a cada redeploy.

## Checklist final

- [ ] `routes/` commitada e visível no GitHub
- [ ] `gunicorn` em requirements.txt
- [ ] `SECRET_KEY` via variável de ambiente (nunca hardcoded)
- [ ] `DATABASE_URL` apontando para PostgreSQL
- [ ] `DEBUG=False` em produção
- [ ] `.env` no `.gitignore`
