"""AWS Cost Explorer — coleta e análise de custos por serviço, conta e tag.

Uso:
    poetry run python scripts/aws/cost_explorer.py --days 30 --group-by SERVICE
    poetry run python scripts/aws/cost_explorer.py --days 7 --group-by TAG --tag-key env
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class CostRecord:
    """Representa um registro de custo por dimensão."""

    dimension: str
    amount: float
    unit: str = "USD"
    period_start: str = ""
    period_end: str = ""


@dataclass
class CostReport:
    """Relatório consolidado de custos."""

    period_start: str
    period_end: str
    group_by: str
    records: list[CostRecord] = field(default_factory=list)

    @property
    def total(self) -> float:
        """Retorna o total consolidado do período."""
        return round(sum(r.amount for r in self.records), 2)

    def top_n(self, n: int = 5) -> list[CostRecord]:
        """Retorna os N maiores itens de custo."""
        return sorted(self.records, key=lambda r: r.amount, reverse=True)[:n]


def get_date_range(days: int) -> tuple[str, str]:
    """Calcula o intervalo de datas para consulta.

    Args:
        days: Número de dias retroativos.

    Returns:
        Tupla (start_date, end_date) no formato YYYY-MM-DD.
    """
    end = date.today()
    start = end - timedelta(days=days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def fetch_costs(
    days: int = 30,
    group_by: str = "SERVICE",
    tag_key: str | None = None,
) -> CostReport:
    """Coleta custos da AWS via Cost Explorer API.

    Args:
        days: Período de consulta em dias.
        group_by: Dimensão de agrupamento (SERVICE, LINKED_ACCOUNT, TAG).
        tag_key: Chave da tag (obrigatório quando group_by=TAG).

    Returns:
        CostReport com os registros do período.

    Raises:
        ValueError: Se group_by=TAG e tag_key não for fornecido.
        ClientError: Em caso de erro na API da AWS.
    """
    if group_by == "TAG" and not tag_key:
        raise ValueError("tag_key é obrigatório quando group_by='TAG'.")

    start_date, end_date = get_date_range(days)
    logger.info("Consultando custos de %s a %s agrupados por %s", start_date, end_date, group_by)

    client = boto3.client(
        "ce",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )

    group_by_config: list[dict[str, str]] = (
        [{"Type": "TAG", "Key": tag_key}]
        if group_by == "TAG"
        else [{"Type": "DIMENSION", "Key": group_by}]
    )

    try:
        response = client.get_cost_and_usage(
            TimePeriod={"Start": start_date, "End": end_date},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=group_by_config,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.error("Erro ao consultar Cost Explorer: %s", exc)
        raise

    report = CostReport(
        period_start=start_date,
        period_end=end_date,
        group_by=group_by,
    )

    for result in response.get("ResultsByTime", []):
        for group in result.get("Groups", []):
            key = group["Keys"][0] if group["Keys"] else "Unknown"
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            unit = group["Metrics"]["UnblendedCost"]["Unit"]

            if amount > 0:
                report.records.append(
                    CostRecord(
                        dimension=key,
                        amount=round(amount, 2),
                        unit=unit,
                        period_start=result["TimePeriod"]["Start"],
                        period_end=result["TimePeriod"]["End"],
                    )
                )

    logger.info("Total de registros coletados: %d | Total: $ %.2f", len(report.records), report.total)
    return report


def print_report(report: CostReport, top_n: int = 10) -> None:
    """Exibe o relatório formatado no terminal."""
    print(f"\n{'='*60}")
    print(f"  AWS Cost Explorer — Agrupado por: {report.group_by}")
    print(f"  Período: {report.period_start} → {report.period_end}")
    print(f"{'='*60}")
    print(f"{'Dimensão':<35} {'Custo (USD)':>12}")
    print(f"{'-'*35} {'-'*12}")

    for record in report.top_n(top_n):
        print(f"{record.dimension:<35} $ {record.amount:>10,.2f}")

    print(f"{'='*60}")
    print(f"{'TOTAL':.<35} $ {report.total:>10,.2f}")
    print(f"{'='*60}\n")


def save_json(report: CostReport, output_path: str) -> None:
    """Salva o relatório em formato JSON.

    Args:
        report: CostReport a ser serializado.
        output_path: Caminho do arquivo de saída.
    """
    data: dict[str, Any] = {
        "period_start": report.period_start,
        "period_end": report.period_end,
        "group_by": report.group_by,
        "total_usd": report.total,
        "records": [
            {
                "dimension": r.dimension,
                "amount_usd": r.amount,
                "period_start": r.period_start,
                "period_end": r.period_end,
            }
            for r in report.records
        ],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Relatório salvo em: %s", output_path)


def parse_args() -> argparse.Namespace:
    """Processa argumentos da linha de comando."""
    parser = argparse.ArgumentParser(description="AWS Cost Explorer Toolkit")
    parser.add_argument("--days", type=int, default=30, help="Período em dias (padrão: 30)")
    parser.add_argument(
        "--group-by",
        choices=["SERVICE", "LINKED_ACCOUNT", "TAG"],
        default="SERVICE",
        help="Dimensão de agrupamento (padrão: SERVICE)",
    )
    parser.add_argument("--tag-key", type=str, help="Chave da tag (necessário com --group-by TAG)")
    parser.add_argument("--top", type=int, default=10, help="Exibir top N itens (padrão: 10)")
    parser.add_argument("--output-json", type=str, help="Salvar resultado em JSON no caminho especificado")
    return parser.parse_args()


def main() -> None:
    """Ponto de entrada principal."""
    args = parse_args()

    report = fetch_costs(
        days=args.days,
        group_by=args.group_by,
        tag_key=args.tag_key,
    )

    print_report(report, top_n=args.top)

    if args.output_json:
        save_json(report, args.output_json)


if __name__ == "__main__":
    main()
