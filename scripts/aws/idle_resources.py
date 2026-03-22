"""Detecção de recursos ociosos na AWS — EC2, RDS e volumes EBS.

Identifica recursos subutilizados ou parados que geram custo sem valor,
gerando recomendações de rightsizing ou descomissionamento.

Uso:
    poetry run python scripts/aws/idle_resources.py --region us-east-1
    poetry run python scripts/aws/idle_resources.py --region us-east-1 --output-json reports/idle.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Thresholds de ociosidade
CPU_IDLE_THRESHOLD = float(os.getenv("CPU_IDLE_THRESHOLD", "5.0"))   # % médio nos últimos 14 dias
EBS_UNATTACHED_STATES = {"available"}


@dataclass
class IdleResource:
    """Representa um recurso ocioso identificado."""

    resource_id: str
    resource_type: str
    region: str
    reason: str
    estimated_monthly_cost_usd: float = 0.0
    tags: dict[str, str] = field(default_factory=dict)
    recommendation: str = ""


@dataclass
class IdleReport:
    """Relatório consolidado de recursos ociosos."""

    region: str
    resources: list[IdleResource] = field(default_factory=list)

    @property
    def total_estimated_waste_usd(self) -> float:
        """Custo estimado total desperdiçado por mês."""
        return round(sum(r.estimated_monthly_cost_usd for r in self.resources), 2)

    def by_type(self, resource_type: str) -> list[IdleResource]:
        """Filtra recursos por tipo."""
        return [r for r in self.resources if r.resource_type == resource_type]


def get_tags(tag_list: list[dict[str, str]]) -> dict[str, str]:
    """Converte lista de tags AWS para dicionário.

    Args:
        tag_list: Lista de dicts com Key/Value da API AWS.

    Returns:
        Dicionário {chave: valor}.
    """
    return {t["Key"]: t["Value"] for t in tag_list}


def find_idle_ec2(region: str) -> list[IdleResource]:
    """Detecta instâncias EC2 paradas ou com CPU média abaixo do threshold.

    Args:
        region: Região AWS a ser analisada.

    Returns:
        Lista de IdleResource com instâncias ociosas.
    """
    logger.info("Verificando instâncias EC2 ociosas em %s...", region)
    ec2 = boto3.client("ec2", region_name=region)
    cw = boto3.client("cloudwatch", region_name=region)
    idle: list[IdleResource] = []

    try:
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped", "running"]}]
        ):
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    iid = instance["InstanceId"]
                    state = instance["State"]["Name"]
                    tags = get_tags(instance.get("Tags", []))
                    itype = instance.get("InstanceType", "unknown")

                    if state == "stopped":
                        idle.append(
                            IdleResource(
                                resource_id=iid,
                                resource_type="EC2",
                                region=region,
                                reason="Instância parada (stopped) — gerando custo de EBS associado",
                                estimated_monthly_cost_usd=5.0,
                                tags=tags,
                                recommendation=f"Avaliar descomissionamento ou snapshot+terminate de {iid} ({itype})",
                            )
                        )
                        continue

                    # Verificar CPU média via CloudWatch (últimos 14 dias)
                    metrics = cw.get_metric_statistics(
                        Namespace="AWS/EC2",
                        MetricName="CPUUtilization",
                        Dimensions=[{"Name": "InstanceId", "Value": iid}],
                        StartTime=__import__("datetime").datetime.utcnow() - __import__("datetime").timedelta(days=14),
                        EndTime=__import__("datetime").datetime.utcnow(),
                        Period=86400,
                        Statistics=["Average"],
                    )
                    datapoints = metrics.get("Datapoints", [])
                    if datapoints:
                        avg_cpu = sum(d["Average"] for d in datapoints) / len(datapoints)
                        if avg_cpu < CPU_IDLE_THRESHOLD:
                            idle.append(
                                IdleResource(
                                    resource_id=iid,
                                    resource_type="EC2",
                                    region=region,
                                    reason=f"CPU média de {avg_cpu:.1f}% nos últimos 14 dias (threshold: {CPU_IDLE_THRESHOLD}%)",
                                    tags=tags,
                                    recommendation=f"Avaliar rightsizing ou descomissionamento de {iid} ({itype})",
                                )
                            )

    except (BotoCoreError, ClientError) as exc:
        logger.error("Erro ao consultar EC2: %s", exc)

    logger.info("EC2 ociosos encontrados: %d", len(idle))
    return idle


def find_unattached_ebs(region: str) -> list[IdleResource]:
    """Detecta volumes EBS não attachados a nenhuma instância.

    Args:
        region: Região AWS a ser analisada.

    Returns:
        Lista de IdleResource com volumes ociosos.
    """
    logger.info("Verificando volumes EBS não utilizados em %s...", region)
    ec2 = boto3.client("ec2", region_name=region)
    idle: list[IdleResource] = []

    try:
        paginator = ec2.get_paginator("describe_volumes")
        for page in paginator.paginate(
            Filters=[{"Name": "status", "Values": list(EBS_UNATTACHED_STATES)}]
        ):
            for volume in page["Volumes"]:
                vid = volume["VolumeId"]
                size_gb = volume["Size"]
                vtype = volume["VolumeType"]
                tags = get_tags(volume.get("Tags", []))

                # Estimativa simplificada: gp3 ~$0.08/GB/mês
                estimated_cost = round(size_gb * 0.08, 2)

                idle.append(
                    IdleResource(
                        resource_id=vid,
                        resource_type="EBS",
                        region=region,
                        reason=f"Volume {vtype} de {size_gb}GB não attachado a nenhuma instância",
                        estimated_monthly_cost_usd=estimated_cost,
                        tags=tags,
                        recommendation=f"Criar snapshot e deletar volume {vid} — economia estimada: $ {estimated_cost}/mês",
                    )
                )

    except (BotoCoreError, ClientError) as exc:
        logger.error("Erro ao consultar EBS: %s", exc)

    logger.info("Volumes EBS ociosos encontrados: %d", len(idle))
    return idle


def print_report(report: IdleReport) -> None:
    """Exibe relatório de recursos ociosos no terminal."""
    print(f"\n{'='*70}")
    print(f"  Recursos Ociosos — Região: {report.region}")
    print(f"  Total de recursos: {len(report.resources)}")
    print(f"  Desperdício estimado: $ {report.total_estimated_waste_usd:,.2f} / mês")
    print(f"{'='*70}")

    for rtype in ["EC2", "EBS"]:
        resources = report.by_type(rtype)
        if not resources:
            continue
        print(f"\n  🔍 {rtype} ({len(resources)} recursos)")
        print(f"  {'-'*65}")
        for r in resources:
            print(f"  ID:             {r.resource_id}")
            print(f"  Motivo:         {r.reason}")
            print(f"  Recomendação:   {r.recommendation}")
            if r.estimated_monthly_cost_usd:
                print(f"  Custo estimado: $ {r.estimated_monthly_cost_usd:,.2f} / mês")
            env_tag = r.tags.get("env", r.tags.get("Environment", "sem tag"))
            print(f"  Ambiente:       {env_tag}")
            print()

    print(f"{'='*70}\n")


def save_json(report: IdleReport, output_path: str) -> None:
    """Salva relatório em JSON."""
    data: dict[str, Any] = {
        "region": report.region,
        "total_resources": len(report.resources),
        "total_estimated_waste_usd": report.total_estimated_waste_usd,
        "resources": [
            {
                "id": r.resource_id,
                "type": r.resource_type,
                "reason": r.reason,
                "recommendation": r.recommendation,
                "estimated_monthly_cost_usd": r.estimated_monthly_cost_usd,
                "tags": r.tags,
            }
            for r in report.resources
        ],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Relatório salvo em: %s", output_path)


def main() -> None:
    """Ponto de entrada principal."""
    parser = argparse.ArgumentParser(description="AWS Idle Resources Detector")
    parser.add_argument("--region", default="us-east-1", help="Região AWS (padrão: us-east-1)")
    parser.add_argument("--output-json", type=str, help="Salvar resultado em JSON")
    args = parser.parse_args()

    report = IdleReport(region=args.region)
    report.resources.extend(find_idle_ec2(args.region))
    report.resources.extend(find_unattached_ebs(args.region))

    print_report(report)

    if args.output_json:
        save_json(report, args.output_json)


if __name__ == "__main__":
    main()
