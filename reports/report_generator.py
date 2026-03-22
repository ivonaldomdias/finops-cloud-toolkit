"""Gerador de relatórios consolidados de FinOps em HTML e CSV.

Combina dados de múltiplas clouds em um relatório executivo unificado.

Uso:
    poetry run python reports/report_generator.py --input reports/data/ --format html
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class CloudCostEntry:
    """Entrada de custo de uma cloud."""

    cloud: str
    dimension: str
    amount_usd: float
    period: str


@dataclass
class ConsolidatedReport:
    """Relatório consolidado multicloud."""

    generated_at: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    entries: list[CloudCostEntry] = field(default_factory=list)

    @property
    def total_usd(self) -> float:
        return round(sum(e.amount_usd for e in self.entries), 2)

    def by_cloud(self) -> dict[str, float]:
        """Agrupa total por cloud."""
        result: dict[str, float] = {}
        for e in self.entries:
            result[e.cloud] = round(result.get(e.cloud, 0.0) + e.amount_usd, 2)
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


def load_json_reports(input_dir: Path) -> ConsolidatedReport:
    """Carrega todos os relatórios JSON de um diretório.

    Args:
        input_dir: Diretório com arquivos JSON de custo.

    Returns:
        ConsolidatedReport com todas as entradas.
    """
    report = ConsolidatedReport()
    json_files = list(input_dir.glob("*.json"))

    if not json_files:
        logger.warning("Nenhum arquivo JSON encontrado em %s", input_dir)
        return report

    for json_file in json_files:
        cloud = json_file.stem.split("_")[0].upper()
        logger.info("Carregando: %s (cloud: %s)", json_file.name, cloud)

        with json_file.open(encoding="utf-8") as f:
            data = json.load(f)

        for record in data.get("records", []):
            report.entries.append(
                CloudCostEntry(
                    cloud=cloud,
                    dimension=record.get("dimension", "Unknown"),
                    amount_usd=float(record.get("amount_usd", 0)),
                    period=record.get("period_start", ""),
                )
            )

    logger.info("Total de entradas carregadas: %d", len(report.entries))
    return report


def export_csv(report: ConsolidatedReport, output_path: Path) -> None:
    """Exporta relatório consolidado para CSV.

    Args:
        report: ConsolidatedReport a ser exportado.
        output_path: Caminho do arquivo CSV de saída.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["cloud", "dimension", "amount_usd", "period"])
        writer.writeheader()
        for entry in sorted(report.entries, key=lambda e: e.amount_usd, reverse=True):
            writer.writerow({
                "cloud": entry.cloud,
                "dimension": entry.dimension,
                "amount_usd": entry.amount_usd,
                "period": entry.period,
            })
    logger.info("CSV exportado: %s", output_path)


def export_html(report: ConsolidatedReport, output_path: Path) -> None:
    """Exporta relatório consolidado para HTML executivo.

    Args:
        report: ConsolidatedReport a ser exportado.
        output_path: Caminho do arquivo HTML de saída.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    by_cloud = report.by_cloud()

    rows = "".join(
        f"<tr><td>{e.cloud}</td><td>{e.dimension}</td>"
        f"<td style='text-align:right'>$ {e.amount_usd:,.2f}</td>"
        f"<td>{e.period}</td></tr>"
        for e in sorted(report.entries, key=lambda x: x.amount_usd, reverse=True)
    )

    cloud_summary = "".join(
        f"<div class='card'><h3>{cloud}</h3><p>$ {total:,.2f}</p></div>"
        for cloud, total in by_cloud.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>FinOps Report — {report.generated_at}</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f4f6f9; color: #333; margin: 0; padding: 24px; }}
    h1 {{ color: #1a3a5c; }} h2 {{ color: #2e75b6; border-bottom: 2px solid #2e75b6; padding-bottom: 6px; }}
    .summary {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 24px 0; }}
    .card {{ background: white; border-radius: 8px; padding: 16px 24px; box-shadow: 0 2px 8px rgba(0,0,0,.1); min-width: 160px; }}
    .card h3 {{ margin: 0 0 8px; font-size: 13px; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
    .card p {{ margin: 0; font-size: 24px; font-weight: bold; color: #1a3a5c; }}
    .total-card p {{ color: #10b981; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,.1); }}
    th {{ background: #1a3a5c; color: white; padding: 12px 16px; text-align: left; font-size: 13px; }}
    td {{ padding: 10px 16px; border-bottom: 1px solid #eee; font-size: 13px; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: #f0f7ff; }}
    .footer {{ margin-top: 24px; font-size: 12px; color: #999; text-align: center; }}
  </style>
</head>
<body>
  <h1>☁️ FinOps Cloud Report</h1>
  <p>Gerado em: <strong>{report.generated_at}</strong> | Total de registros: {len(report.entries)}</p>

  <h2>Resumo por Cloud</h2>
  <div class="summary">
    {cloud_summary}
    <div class="card total-card"><h3>Total Consolidado</h3><p>$ {report.total_usd:,.2f}</p></div>
  </div>

  <h2>Detalhamento por Serviço</h2>
  <table>
    <thead><tr><th>Cloud</th><th>Dimensão / Serviço</th><th>Custo (USD)</th><th>Período</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <div class="footer">
    Desenvolvido por Ivonaldo Micheluti Dias · Cloud & FinOps Engineer ·
    <a href="https://github.com/ivonaldomdias/finops-cloud-toolkit">github.com/ivonaldomdias/finops-cloud-toolkit</a>
  </div>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    logger.info("HTML exportado: %s", output_path)


def main() -> None:
    """Ponto de entrada principal."""
    parser = argparse.ArgumentParser(description="FinOps Report Generator")
    parser.add_argument("--input", type=Path, default=Path("reports/data"), help="Diretório com JSONs de custo")
    parser.add_argument("--output", type=Path, default=Path("reports/output"), help="Diretório de saída")
    parser.add_argument("--format", choices=["html", "csv", "both"], default="both", help="Formato de saída")
    args = parser.parse_args()

    report = load_json_reports(args.input)

    if args.format in ("csv", "both"):
        export_csv(report, args.output / "finops_report.csv")
    if args.format in ("html", "both"):
        export_html(report, args.output / "finops_report.html")

    logger.info("Relatório gerado com sucesso! Total: $ %.2f", report.total_usd)


if __name__ == "__main__":
    main()
