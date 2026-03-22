# ☁️ finops-cloud-toolkit

> Toolkit de FinOps e otimização de custos para ambientes multicloud (AWS, OCI e GCP).

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![AWS](https://img.shields.io/badge/AWS-FF9900?style=flat-square&logo=amazonaws&logoColor=white)](https://aws.amazon.com)
[![OCI](https://img.shields.io/badge/OCI-F80000?style=flat-square&logo=oracle&logoColor=white)](https://oracle.com/cloud)
[![GCP](https://img.shields.io/badge/GCP-4285F4?style=flat-square&logo=googlecloud&logoColor=white)](https://cloud.google.com)
[![FinOps](https://img.shields.io/badge/FinOps-Certified_Practitioner-00A4EF?style=flat-square)](https://finops.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## 📋 Sobre o Projeto

Este toolkit reúne scripts e automações para **governança financeira de nuvem**, com foco em:

- 📊 Coleta e análise de custos por cloud, conta e tag
- 🏷️ Auditoria de conformidade de tagging (showback/chargeback)
- 💡 Identificação de recursos ociosos e subutilizados
- 📈 Geração de relatórios executivos de consumo

Baseado em experiências reais de otimização que resultaram em **-23% de custos na AWS** e **-10% de economia recorrente mensal na OCI**.

---

## 🗂️ Estrutura do Repositório

```
finops-cloud-toolkit/
├── scripts/
│   ├── aws/
│   │   ├── cost_explorer.py       # Coleta de custos via AWS Cost Explorer
│   │   └── idle_resources.py      # Detecção de recursos ociosos (EC2, RDS, EBS)
│   ├── oci/
│   │   └── usage_report.py        # Relatório de consumo OCI via Usage API
│   └── gcp/
│       └── billing_export.py      # Análise de billing export do BigQuery
├── reports/
│   └── report_generator.py        # Geração de relatórios consolidados (CSV/HTML)
├── tests/
│   ├── test_cost_explorer.py
│   ├── test_idle_resources.py
│   └── test_report_generator.py
├── docs/
│   └── tagging-policy.md          # Política de tagging recomendada
├── .env.example                   # Variáveis de ambiente necessárias
├── pyproject.toml                 # Dependências e configuração do projeto
└── README.md
```

---

## ⚡ Quick Start

### Pré-requisitos

- Python 3.11+
- Credenciais configuradas para AWS, OCI e/ou GCP
- [Poetry](https://python-poetry.org/) para gerenciamento de dependências

### Instalação

```bash
git clone https://github.com/ivonaldomdias/finops-cloud-toolkit.git
cd finops-cloud-toolkit

# Instalar dependências
poetry install

# Copiar e configurar variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais e configurações
```

### Uso

```bash
# Coletar custos AWS dos últimos 30 dias
poetry run python scripts/aws/cost_explorer.py --days 30 --group-by SERVICE

# Detectar recursos ociosos na AWS
poetry run python scripts/aws/idle_resources.py --region us-east-1

# Gerar relatório consolidado
poetry run python reports/report_generator.py --output reports/output/ --format html
```

---

## 📸 Exemplos de Output

### Custo por Serviço (AWS)
```
┌─────────────────────┬──────────────┬───────────┐
│ Serviço             │ Custo (USD)  │ Variação  │
├─────────────────────┼──────────────┼───────────┤
│ Amazon EC2          │ $ 4.320,00   │ -12,3%    │
│ Amazon RDS          │ $ 1.890,00   │ -8,1%     │
│ Amazon S3           │ $   340,00   │ +2,4%     │
│ AWS Lambda          │    $ 18,00   │ -45,0%    │
└─────────────────────┴──────────────┴───────────┘
Total mensal: $ 6.568,00 | Economia vs. mês anterior: -9,7%
```

---

## 🏷️ Política de Tagging

Veja [`docs/tagging-policy.md`](docs/tagging-policy.md) para a política completa de tagging recomendada para showback e chargeback eficientes.

Tags obrigatórias recomendadas:

| Tag | Descrição | Exemplo |
|---|---|---|
| `env` | Ambiente | `production`, `staging`, `dev` |
| `team` | Time responsável | `platform`, `data`, `backend` |
| `cost-center` | Centro de custo | `cc-1234` |
| `project` | Projeto associado | `ecommerce-v2` |

---

## 🧪 Testes

```bash
# Rodar todos os testes
poetry run pytest tests/ -v --cov=scripts --cov-report=term-missing

# Verificar tipos
poetry run mypy scripts/ --strict
```

---

## 📄 Licença

MIT License — veja [LICENSE](LICENSE) para detalhes.

---

<p align="center">
  Desenvolvido por <a href="https://www.linkedin.com/in/ivonaldo-micheluti-dias-61580470/">Ivonaldo Micheluti Dias</a> · Cloud & FinOps Engineer
</p>
