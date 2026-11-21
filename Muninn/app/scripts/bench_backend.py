"""Benchmark de performance e latência do núcleo local do Muninn (100% offline).

Mede sobre o `dados.db` real:
1. Cold-start do processo `desktop_server.py` até o evento `ready`.
2. Percentis de latência (min, p50, p95, p99, max) das RPCs críticas.
3. Consultas analíticas nas 6 views fato (`vfact_*_resolved`) via datastore read-only.
4. Rajada de requisições concorrentes no protocolo STDIO/RPC (throughput e 0% de erro).

Exporta relatório em JSON e Markdown pronto para registro na Issue #71.

Uso (a partir da raiz via Makefile):
    make test-perf
    make test-perf ARGS="--iterations 20 --concurrency 30"
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parents[1]
NUCLEO_DIR = APP_DIR / "backend" / "nucleo"
DEFAULT_BANCO = APP_DIR / "data" / "dados.db"
DEFAULT_CONTEXT_SRC = APP_DIR / "contexts" / "pesquisa-extensao-ifes"
DEFAULT_OUT_DIR = APP_DIR / "data" / "reports"

# SLOs realistas (em milissegundos) calibrados sobre o dados.db real para detectar regressões.
DEFAULT_SLOS_MS: dict[str, float] = {
    "cold_start_ms": 1500.0,
    "rpc_health_p95_ms": 10.0,
    "rpc_dashboard_p95_ms": 50.0,
    "rpc_admin_p95_ms": 50.0,
    "view_query_p95_ms": 50.0,
}

VIEW_BENCH_QUERIES: list[tuple[str, str]] = [
    (
        "vfact_extensao_acao_resolved",
        "SELECT tipo_acao, COUNT(DISTINCT id_acao) AS total "
        "FROM vfact_extensao_acao_resolved GROUP BY tipo_acao ORDER BY total DESC",
    ),
    (
        "vfact_extensao_participacao_resolved",
        "SELECT tipo_atividade, SUM(qtd_participacoes) AS total, ROUND(SUM(carga_horaria), 2) AS horas "
        "FROM vfact_extensao_participacao_resolved GROUP BY tipo_atividade ORDER BY total DESC LIMIT 10",
    ),
    (
        "vfact_projeto_pesquisa_resolved",
        "SELECT grande_area, COUNT(DISTINCT id_projeto) AS total "
        "FROM vfact_projeto_pesquisa_resolved GROUP BY grande_area ORDER BY total DESC",
    ),
    (
        "vfact_orientacao_bolsa_resolved",
        "SELECT ano, modalidade, COUNT(DISTINCT id_orientacao) AS total, "
        "ROUND(SUM(investimento_total_estimado), 2) AS investimento "
        "FROM vfact_orientacao_bolsa_resolved GROUP BY ano, modalidade ORDER BY ano DESC",
    ),
    (
        "vfact_producao_cientifica_resolved",
        "SELECT ano, tipo_macro_producao, COUNT(DISTINCT id_producao) AS total "
        "FROM vfact_producao_cientifica_resolved WHERE ano IS NOT NULL "
        "GROUP BY ano, tipo_macro_producao ORDER BY ano DESC LIMIT 20",
    ),
    (
        "vfact_grupo_pesquisa_membro_resolved",
        "SELECT grande_area, COUNT(DISTINCT id_grupo_pesquisa) AS grupos, SUM(flag_ativo) AS ativos "
        "FROM vfact_grupo_pesquisa_membro_resolved GROUP BY grande_area ORDER BY grupos DESC",
    ),
]


@dataclass
class LatencyStats:
    name: str
    samples: int
    min_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    slo_p95_ms: float
    passed: bool


def percentile(values: list[float], p: float) -> float:
    """Calcula percentil p (0..100) usando interpolação linear (método inclusivo)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (p / 100.0) * (len(ordered) - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return ordered[lo]
    weight = rank - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * weight


def summarize_samples(name: str, samples_ms: list[float], slo_p95_ms: float) -> LatencyStats:
    p95 = round(percentile(samples_ms, 95), 2)
    return LatencyStats(
        name=name,
        samples=len(samples_ms),
        min_ms=round(min(samples_ms), 2),
        p50_ms=round(percentile(samples_ms, 50), 2),
        p95_ms=p95,
        p99_ms=round(percentile(samples_ms, 99), 2),
        max_ms=round(max(samples_ms), 2),
        slo_p95_ms=slo_p95_ms,
        passed=p95 <= slo_p95_ms,
    )


class NucleoClient:
    """Cliente STDIO mínimo para benchmark do `desktop_server.py`."""

    def __init__(self, data_dir: Path) -> None:
        env = {**os.environ, "MUNINN_DATA_DIR": str(data_dir), "PYTHONUNBUFFERED": "1"}
        env["GEMINI_API_KEY"] = ""
        env["GOOGLE_API_KEY"] = ""
        self.log_file = open(data_dir / "bench_nucleo.log", "w", encoding="utf-8")
        self.t0 = time.perf_counter()
        self.proc = subprocess.Popen(
            [sys.executable, str(NUCLEO_DIR / "desktop_server.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log_file,
            env=env,
            text=True,
            encoding="utf-8",
        )
        self.next_id = 0

    def read(self) -> dict[str, Any]:
        assert self.proc.stdout is not None
        line = self.proc.stdout.readline()
        if not line:
            raise EOFError("stdout do núcleo fechado inesperadamente")
        return json.loads(line)

    def send(self, message: dict[str, Any]) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def request(self, method: str, params: dict[str, Any] | None = None) -> int:
        self.next_id += 1
        self.send({"id": self.next_id, "method": method, "params": params or {}})
        return self.next_id

    def call(self, method: str, params: dict[str, Any] | None = None) -> tuple[dict[str, Any], float]:
        t0 = time.perf_counter()
        rid = self.request(method, params)
        while True:
            msg = self.read()
            if msg.get("id") == rid and "ok" in msg:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return msg, elapsed_ms

    def close(self) -> None:
        try:
            if self.proc.stdin and not self.proc.stdin.closed:
                self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
        finally:
            self.log_file.close()


def prepare_isolated_data_dir(banco_path: Path) -> Path:
    """Cria MUNINN_DATA_DIR temporário com link/cópia do dados.db real e contexto IFES."""
    temp_dir = Path(tempfile.mkdtemp(prefix="muninn-bench-"))
    target_db = temp_dir / "dados.db"
    try:
        os.symlink(banco_path.resolve(), target_db)
    except OSError:
        shutil.copy2(banco_path, target_db)

    if DEFAULT_CONTEXT_SRC.is_dir():
        dest_ctx = temp_dir / "contexts" / DEFAULT_CONTEXT_SRC.name
        shutil.copytree(DEFAULT_CONTEXT_SRC, dest_ctx)
    return temp_dir


def benchmark_views(
    data_dir: Path,
    iterations: int,
    warmup: int,
    view_slo_ms: float = DEFAULT_SLOS_MS["view_query_p95_ms"],
) -> list[LatencyStats]:
    """Mede consultas analíticas nas 6 views fato via `core.datastore.connect_dados`."""
    if str(NUCLEO_DIR) not in sys.path:
        sys.path.insert(0, str(NUCLEO_DIR))
    os.environ["MUNINN_DATA_DIR"] = str(data_dir)
    from core.datastore import close_dados, connect_dados

    results: list[LatencyStats] = []
    try:
        for view_name, sql in VIEW_BENCH_QUERIES:
            for _ in range(warmup):
                with connect_dados() as conn:
                    conn.execute(sql).fetchall()

            samples: list[float] = []
            for _ in range(iterations):
                t0 = time.perf_counter()
                with connect_dados() as conn:
                    rows = conn.execute(sql).fetchall()
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                if rows is None:
                    raise RuntimeError(f"Consulta retornou None na view {view_name}")
                samples.append(elapsed_ms)

            results.append(summarize_samples(view_name, samples, view_slo_ms))
    finally:
        close_dados()
    return results


def benchmark_concurrency(client: NucleoClient, concurrency: int) -> dict[str, Any]:
    """Dispara rajada de requisições concorrentes no protocolo STDIO/RPC."""
    workload: list[tuple[str, dict[str, Any]]] = [
        ("health", {}),
        ("contextos.list", {}),
        ("dashboard.kpis", {}),
        ("dashboard.top_projects", {}),
        ("admin.contextos", {}),
    ]

    t0 = time.perf_counter()
    sent_ids: list[int] = []
    for idx in range(concurrency):
        method, params = workload[idx % len(workload)]
        sent_ids.append(client.request(method, params))

    responses: dict[int, dict[str, Any]] = {}
    while len(responses) < concurrency:
        msg = client.read()
        if "id" in msg and "ok" in msg:
            responses[msg["id"]] = msg
    total_ms = (time.perf_counter() - t0) * 1000.0

    errors = [r for r in responses.values() if not r.get("ok")]
    id_mismatch = sorted(responses.keys()) != sorted(sent_ids)
    throughput = concurrency / (total_ms / 1000.0) if total_ms > 0 else 0.0

    return {
        "requests": concurrency,
        "total_ms": round(total_ms, 2),
        "throughput_rps": round(throughput, 2),
        "errors": len(errors),
        "id_mismatch": id_mismatch,
        "passed": len(errors) == 0 and not id_mismatch,
    }


def render_markdown(report: dict[str, Any]) -> str:
    cold = report["cold_start"]
    conc = report["concurrency"]
    status_emoji = "✅ PASSOU" if report["overall_passed"] else "❌ REGRESSÃO DE SLO"

    lines = [
        "# ⚡ Relatório de Benchmark de Performance — Núcleo Local Muninn",
        "",
        f"- **Status Geral:** {status_emoji}",
        f"- **Gerado em (UTC):** `{report['timestamp_utc']}`",
        f"- **Banco:** `{report['database']['path']}` ({report['database']['size_mb']} MB)",
        f"- **Ambiente:** Python `{report['environment']['python']}` · {report['environment']['os']}",
        f"- **Configuração:** {report['config']['iterations']} iterações (warm-up: {report['config']['warmup']}) · rajada concorrente: {report['config']['concurrency']} reqs",
        "",
        "## 1. Cold-Start do Núcleo (`desktop_server.py`)",
        "",
        "| Métrica | Valor (ms) | SLO (ms) | Status |",
        "|---|---:|---:|:---:|",
        f"| Boot total até evento `ready` | {cold['wall_ms']} | ≤ {cold['slo_ms']} | {'✅' if cold['passed'] else '❌'} |",
        f"| Inicialização interna (`startup_ms`) | {cold['startup_ms']} | — | ℹ️ |",
        "",
        "## 2. Latência das RPCs Críticas (STDIO)",
        "",
        "| RPC | min (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | SLO p95 | Status |",
        "|---|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for item in report["rpcs"]:
        lines.append(
            f"| `{item['name']}` | {item['min_ms']} | {item['p50_ms']} | **{item['p95_ms']}** | "
            f"{item['p99_ms']} | {item['max_ms']} | ≤ {item['slo_p95_ms']} | {'✅' if item['passed'] else '❌'} |"
        )

    lines.extend([
        "",
        "## 3. Consultas Analíticas nas 6 Views Fato (`dados.db` read-only)",
        "",
        "| View Fato | min (ms) | p50 (ms) | p95 (ms) | max (ms) | SLO p95 | Status |",
        "|---|---:|---:|---:|---:|---:|:---:|",
    ])
    for item in report["views"]:
        lines.append(
            f"| `{item['name']}` | {item['min_ms']} | {item['p50_ms']} | **{item['p95_ms']}** | "
            f"{item['max_ms']} | ≤ {item['slo_p95_ms']} | {'✅' if item['passed'] else '❌'} |"
        )

    lines.extend([
        "",
        "## 4. Concorrência STDIO/RPC",
        "",
        "| Requisições Simultâneas | Tempo Total (ms) | Throughput (req/s) | Erros | IDs Correspondentes | Status |",
        "|---:|---:|---:|---:|:---:|:---:|",
        f"| {conc['requests']} | {conc['total_ms']} | **{conc['throughput_rps']}** | {conc['errors']} | "
        f"{'✅' if not conc['id_mismatch'] else '❌'} | {'✅' if conc['passed'] else '❌'} |",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark de performance do núcleo local Muninn.")
    parser.add_argument("--banco", type=Path, default=DEFAULT_BANCO, help="Caminho para dados.db")
    parser.add_argument("--iterations", type=int, default=15, help="Iterações medidas por RPC/view")
    parser.add_argument("--warmup", type=int, default=2, help="Iterações de warm-up descartadas")
    parser.add_argument("--concurrency", type=int, default=20, help="Requisições concorrentes na rajada STDIO")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Diretório de saída dos relatórios")
    parser.add_argument("--no-fail", action="store_true", help="Não retorna exit code 1 se algum SLO estourar")
    parser.add_argument("--slo-cold-start", type=float, default=DEFAULT_SLOS_MS["cold_start_ms"], help="SLO de cold-start em ms")
    parser.add_argument("--slo-health", type=float, default=DEFAULT_SLOS_MS["rpc_health_p95_ms"], help="SLO p95 de health/me em ms")
    parser.add_argument("--slo-dashboard", type=float, default=DEFAULT_SLOS_MS["rpc_dashboard_p95_ms"], help="SLO p95 do dashboard em ms")
    parser.add_argument("--slo-admin", type=float, default=DEFAULT_SLOS_MS["rpc_admin_p95_ms"], help="SLO p95 das RPCs admin em ms")
    parser.add_argument("--slo-view", type=float, default=DEFAULT_SLOS_MS["view_query_p95_ms"], help="SLO p95 das views fato em ms")
    args = parser.parse_args()

    slos_ms = {
        "cold_start_ms": args.slo_cold_start,
        "rpc_health_p95_ms": args.slo_health,
        "rpc_dashboard_p95_ms": args.slo_dashboard,
        "rpc_admin_p95_ms": args.slo_admin,
        "view_query_p95_ms": args.slo_view,
    }

    if not args.banco.is_file():
        print(f"❌ Erro: banco SQLite não encontrado em '{args.banco}'.", file=sys.stderr)
        print("Execute 'make db' primeiro para gerar o dados.db.", file=sys.stderr)
        return 2

    data_dir = prepare_isolated_data_dir(args.banco)
    client: NucleoClient | None = None
    try:
        print(f"→ Iniciando benchmark sobre '{args.banco}' ({args.iterations} iterações, concorrência={args.concurrency})...")

        # 1. Cold-start
        client = NucleoClient(data_dir)
        ready = client.read()
        cold_wall_ms = round((time.perf_counter() - client.t0) * 1000.0, 2)
        if ready.get("event") != "ready":
            raise RuntimeError(f"Evento inicial inesperado do núcleo: {ready}")
        cold_startup_ms = ready.get("data", {}).get("startup_ms", cold_wall_ms)
        cold_passed = cold_wall_ms <= slos_ms["cold_start_ms"]
        print(f"  [1/4] Cold-start: {cold_wall_ms} ms (interno: {cold_startup_ms} ms) {'✓' if cold_passed else '✗'}")

        # Identifica contexto real carregado
        ctxs_resp, _ = client.call("contextos.list")
        if not ctxs_resp.get("ok") or not ctxs_resp.get("result"):
            raise RuntimeError(f"Nenhum contexto disponível no benchmark: {ctxs_resp}")
        contexto_id = ctxs_resp["result"][0]["id"]

        # 2. RPCs críticas
        rpc_cases: list[tuple[str, str, dict[str, Any], float]] = [
            ("health", "health", {}, slos_ms["rpc_health_p95_ms"]),
            ("me", "me", {}, slos_ms["rpc_health_p95_ms"]),
            ("contextos.list", "contextos.list", {}, slos_ms["rpc_dashboard_p95_ms"]),
            ("dashboard.kpis", "dashboard.kpis", {}, slos_ms["rpc_dashboard_p95_ms"]),
            ("dashboard.kpis (filtrado ano=2024)", "dashboard.kpis", {"ano": "2024"}, slos_ms["rpc_dashboard_p95_ms"]),
            ("dashboard.charts", "dashboard.charts", {}, slos_ms["rpc_dashboard_p95_ms"]),
            ("dashboard.top_projects", "dashboard.top_projects", {}, slos_ms["rpc_dashboard_p95_ms"]),
            ("admin.contextos", "admin.contextos", {}, slos_ms["rpc_admin_p95_ms"]),
            ("admin.system_status", "admin.system_status", {}, slos_ms["rpc_admin_p95_ms"]),
        ]

        rpc_stats: list[LatencyStats] = []
        for label, method, params, slo_ms in rpc_cases:
            for _ in range(args.warmup):
                resp, _ = client.call(method, params)
                if not resp.get("ok"):
                    raise RuntimeError(f"RPC '{label}' falhou no warm-up: {resp}")

            samples: list[float] = []
            for _ in range(args.iterations):
                resp, elapsed_ms = client.call(method, params)
                if not resp.get("ok"):
                    raise RuntimeError(f"RPC '{label}' falhou na medição: {resp}")
                samples.append(elapsed_ms)
            rpc_stats.append(summarize_samples(label, samples, slo_ms))
        print(f"  [2/4] RPCs medidas: {len(rpc_stats)} endpoints (p95 máx: {max(r.p95_ms for r in rpc_stats)} ms)")

        # 3. Concorrência STDIO
        concurrency_result = benchmark_concurrency(client, args.concurrency)
        print(
            f"  [3/4] Concorrência ({args.concurrency} reqs): {concurrency_result['total_ms']} ms "
            f"({concurrency_result['throughput_rps']} req/s, erros={concurrency_result['errors']})"
        )

        client.close()
        client = None

        # 4. Consultas analíticas nas 6 views fato
        view_stats = benchmark_views(data_dir, args.iterations, args.warmup, slos_ms["view_query_p95_ms"])
        print(f"  [4/4] 6 Views fato medidas (p95 máx: {max(v.p95_ms for v in view_stats)} ms)")

        overall_passed = (
            cold_passed
            and all(r.passed for r in rpc_stats)
            and all(v.passed for v in view_stats)
            and concurrency_result["passed"]
        )

        report: dict[str, Any] = {
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "overall_passed": overall_passed,
            "database": {
                "path": str(args.banco.relative_to(APP_DIR.parent.parent)) if args.banco.is_relative_to(APP_DIR.parent.parent) else args.banco.name,
                "size_mb": round(args.banco.stat().st_size / (1024 * 1024), 2),
            },
            "environment": {
                "python": platform.python_version(),
                "os": f"{platform.system()} {platform.release()}",
            },
            "config": {
                "iterations": args.iterations,
                "warmup": args.warmup,
                "concurrency": args.concurrency,
            },
            "cold_start": {
                "wall_ms": cold_wall_ms,
                "startup_ms": cold_startup_ms,
                "slo_ms": slos_ms["cold_start_ms"],
                "passed": cold_passed,
            },
            "rpcs": [asdict(r) for r in rpc_stats],
            "views": [asdict(v) for v in view_stats],
            "concurrency": concurrency_result,
        }

        args.out_dir.mkdir(parents=True, exist_ok=True)
        json_path = args.out_dir / "bench_backend_report.json"
        md_path = args.out_dir / "bench_backend_report.md"
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        md_path.write_text(render_markdown(report), encoding="utf-8")

        print(f"\nRelatórios salvos em:\n  - {json_path}\n  - {md_path}")
        if overall_passed:
            print("✓ Todos os SLOs de performance do backend foram atendidos!")
            return 0
        print("✗ Um ou mais SLOs de performance foram excedidos (ver relatório).", file=sys.stderr)
        return 0 if args.no_fail else 1
    finally:
        if client is not None:
            client.close()
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
