# InNova Vitta+ 🏥

[![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey?style=for-the-badge&logo=sqlite)](https://www.sqlite.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple?style=for-the-badge&logo=bootstrap)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-orange?style=for-the-badge)]()

> Sistema de gestão clínica modular desenvolvido com Python/Flask — do agendamento ao prontuário, tudo em um só lugar.

---

## 📑 Sumário

- [Visão Geral](#-visão-geral)
- [Funcionalidades Principais](#-funcionalidades-principais)
- [Tecnologias](#-tecnologias)
- [Arquitetura](#-arquitetura)
- [Guia de Instalação](#-guia-de-instalação)
- [Roadmap](#-roadmap)
- [Autor](#-autor)

---

## 🚀 Visão Geral

O **InNova Vitta+** foi projetado para digitalizar e otimizar processos em clínicas de saúde. Com uma arquitetura modular baseada em *Blueprints*, o sistema garante escalabilidade e facilidade de manutenção — da recepção ao consultório.

Desenvolvido pela **InNovaIdeia Assessoria em Tecnologia**, o projeto segue boas práticas de engenharia de software com foco em clareza de código, separação de responsabilidades e preparação para ambientes de produção.

---

## ✅ Funcionalidades Principais

| Módulo | Descrição |
|:---|:---|
| 📊 **Dashboard** | Indicadores em tempo real: total de pacientes, consultas e urgências |
| 👤 **Cadastro** | Gestão completa de Pacientes, Médicos e Serviços |
| 📅 **Agendamento** | Consultas e exames com verificação automática de conflitos de horário |
| 🩺 **Atendimento Clínico** | Prontuário eletrônico, evolução clínica e geração de receitas |
| 📈 **Relatórios** | Faturamento mensal e controle de acesso por perfil |

---

## 🛠 Tecnologias

| Camada | Tecnologia |
|:---|:---|
| **Backend** | Python 3.12 + Flask 3.0+ |
| **ORM** | SQLAlchemy 2.0+ |
| **Banco de Dados** | SQLite (preparado para migração a PostgreSQL) |
| **Frontend** | Bootstrap 5.3 + Jinja2 Templates |
| **Utilitários** | python-dotenv, Bootstrap Icons |

---

## 📂 Arquitetura

O projeto adota o padrão **Application Factory** com *Blueprints* para cada módulo clínico, garantindo isolamento de responsabilidades e facilidade de testes.

```text
innova-vitta-new/
├── app.py                  # Ponto de entrada — Application Factory
├── config.py               # Configurações por ambiente (dev/prod)
├── core/
│   ├── models.py           # Modelos SQLAlchemy
│   └── utils.py            # Utilitários compartilhados
├── routes/
│   ├── pacientes.py        # Blueprint: pacientes
│   ├── consultas.py        # Blueprint: agendamentos
│   ├── atendimento.py      # Blueprint: prontuário e receitas
│   └── relatorios.py       # Blueprint: relatórios gerenciais
├── templates/
│   ├── base.html           # Layout principal
│   └── ...                 # Views por módulo (Jinja2)
├── static/
│   ├── css/                # Estilos customizados
│   └── js/                 # Scripts de interação
└── instance/
    └── vitta.db            # Banco de dados SQLite
```

---

## ⚙️ Guia de Instalação

### Pré-requisitos

- Python 3.10+
- pip

### Passo a passo

**1. Clone o repositório:**

```bash
git clone <url-do-repositorio>
cd innova-vitta-new
```

**2. Instale as dependências:**

```bash
pip install -r requirements.txt
```

**3. Configure as variáveis de ambiente:**

Crie um arquivo `.env` na raiz do projeto:

```env
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
DATABASE_URL=sqlite:///instance/vitta.db
```

**4. Inicialize o banco de dados:**

```bash
flask shell
```

```python
>>> from app import db
>>> db.create_all()
>>> exit()
```

**5. Execute a aplicação:**

```bash
flask run
```

Acesse em: [http://localhost:5000](http://localhost:5000)

---

## 🗺️ Roadmap

- [ ] Autenticação e autorização com Flask-Login
- [ ] Proteção CSRF com Flask-WTF
- [ ] Sistema de notificações por SMS e E-mail
- [ ] Dashboard avançado com Chart.js
- [ ] Testes automatizados com pytest
- [ ] Migração para PostgreSQL em produção
- [ ] API REST para integração com apps mobile
- [ ] Exportação de prontuários em PDF

---

## 👤 Autor

**Dione Castro Alves**  
Fundador da InNovaIdeia Assessoria em Tecnologia — Franca/SP, Brasil

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Dione%20Castro%20Alves-0077B5?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/dione-castro-alves/)
[![GitHub](https://img.shields.io/badge/GitHub-Foxactive1-181717?style=flat-square&logo=github)](https://github.com/Foxactive1)
[![Portfolio](https://img.shields.io/badge/Portfólio-innovaideia-blueviolet?style=flat-square)](https://innovaideia-github-io.vercel.app)
[![Email](https://img.shields.io/badge/Email-innovaideia2023%40gmail.com-red?style=flat-square&logo=gmail)](mailto:innovaideia2023@gmail.com)

---

> **Versão:** 1.0.0 | **Última atualização:** Agosto de 2026  
> Desenvolvido com 💙 por [InNovaIdeia](https://innovaideia-github-io.vercel.app) — Transformando ideias em soluções tecnológicas.
