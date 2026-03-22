# 🏷️ Política de Tagging Multicloud

Política de tagging recomendada para showback, chargeback e governança financeira eficiente em ambientes AWS, OCI e GCP.

---

## Por que Tagging é Crítico para FinOps?

Sem tagging consistente, é impossível:
- Atribuir custos a times, projetos ou centros de custo (showback/chargeback)
- Identificar recursos órfãos ou sem responsável
- Automatizar políticas de otimização e descomissionamento
- Gerar relatórios executivos confiáveis

---

## Tags Obrigatórias

| Tag | Descrição | Valores Aceitos | Exemplo |
|---|---|---|---|
| `env` | Ambiente de execução | `production`, `staging`, `development`, `sandbox` | `production` |
| `team` | Time responsável pelo recurso | Nome do time em lowercase | `platform`, `data`, `backend` |
| `cost-center` | Centro de custo financeiro | Código do CC no formato `cc-XXXX` | `cc-1042` |
| `project` | Projeto ou produto associado | Slug do projeto | `ecommerce-v2`, `data-lake` |
| `managed-by` | Ferramenta de provisionamento | `terraform`, `ansible`, `manual`, `console` | `terraform` |

---

## Tags Recomendadas (Opcionais)

| Tag | Descrição | Exemplo |
|---|---|---|
| `owner` | E-mail do responsável técnico | `engenheiro@empresa.com` |
| `expiration-date` | Data de expiração (sandboxes) | `2024-12-31` |
| `criticality` | Criticidade do recurso | `high`, `medium`, `low` |
| `backup` | Se o recurso possui backup | `enabled`, `disabled` |
| `compliance` | Regulação aplicável | `hipaa`, `lgpd`, `gdpr` |

---

## Implementação por Cloud

### AWS
```hcl
# Terraform — aws_instance
resource "aws_instance" "web" {
  # ...
  tags = {
    env         = "production"
    team        = "platform"
    cost-center = "cc-1042"
    project     = "ecommerce-v2"
    managed-by  = "terraform"
  }
}
```

### GCP
```hcl
# Terraform — google_compute_instance
resource "google_compute_instance" "web" {
  # ...
  labels = {
    env         = "production"
    team        = "platform"
    cost-center = "cc-1042"
    project     = "ecommerce-v2"
    managed-by  = "terraform"
  }
}
```

### OCI
```hcl
# Terraform — oci_core_instance
resource "oci_core_instance" "web" {
  # ...
  freeform_tags = {
    env         = "production"
    team        = "platform"
    cost-center = "cc-1042"
    project     = "ecommerce-v2"
    managed-by  = "terraform"
  }
}
```

---

## Auditoria de Conformidade

Use o script `scripts/aws/cost_explorer.py --group-by TAG --tag-key team` para identificar recursos sem a tag `team` e priorizar a remediação.

Recursos sem as tags obrigatórias devem ser tratados como **não conformes** e adicionados ao backlog de governança com SLA de remediação de **30 dias**.

---

## Referências

- [AWS Tagging Best Practices](https://docs.aws.amazon.com/tag-editor/latest/userguide/tagging.html)
- [GCP Resource Labels](https://cloud.google.com/resource-manager/docs/creating-managing-labels)
- [OCI Tagging Overview](https://docs.oracle.com/en-us/iaas/Content/Tagging/Concepts/taggingoverview.htm)
- [FinOps Foundation — Tagging](https://www.finops.org/framework/capabilities/tagging/)
