"""GPU vs CPU benchmark demo with live progress visualization.

Run with: uv run python projects/gpu-play/demo.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import torch
import torch.nn as nn
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table


console = Console()


@dataclass
class BenchResult:
    """Result of a single benchmark run."""

    name: str
    cpu_ms: float
    mps_ms: float

    @property
    def speedup(self) -> float:
        """Calculate MPS speedup over CPU."""
        return self.cpu_ms / self.mps_ms if self.mps_ms > 0 else 0.0


def choose_devices() -> tuple[torch.device, torch.device]:
    """Pick CPU and MPS devices."""
    cpu = torch.device("cpu")
    mps = torch.device("mps") if torch.backends.mps.is_available() else cpu
    return cpu, mps


def time_op_with_progress(
    fn: Callable[[], torch.Tensor],
    device: torch.device,
    progress: Progress,
    task_id: int,
    warmup: int = 3,
    iters: int = 10,
) -> float:
    """Time an operation with live progress updates.

    Args:
        fn: Zero-arg callable that executes the op.
        device: Target device (cpu or mps).
        progress: Rich Progress instance for live updates.
        task_id: Task ID for progress bar.
        warmup: Number of warmup iterations.
        iters: Number of timed iterations.

    Returns:
        Average time per iteration in milliseconds.
    """
    total_steps = warmup + iters
    progress.update(task_id, total=total_steps, completed=0)

    # Warmup phase
    for i in range(warmup):
        _ = fn()
        if device.type == "mps":
            torch.mps.synchronize()
        progress.update(task_id, completed=i + 1, description="[yellow]Warmup")

    # Timed phase
    times: list[float] = []
    for i in range(iters):
        t0 = time.perf_counter()
        _ = fn()
        if device.type == "mps":
            torch.mps.synchronize()
        dt = time.perf_counter() - t0
        times.append(dt * 1000.0)
        progress.update(task_id, completed=warmup + i + 1, description="[green]Timing")

    return sum(times) / len(times)


def run_benchmark(
    name: str,
    make_fn: Callable[[torch.device], Callable[[], torch.Tensor]],
    cpu: torch.device,
    mps: torch.device,
) -> BenchResult:
    """Run a single benchmark with visual progress for both devices."""
    console.print(f"\n[bold cyan]▶ {name}[/bold cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        # CPU benchmark
        cpu_task = progress.add_task("[blue]CPU", total=13)
        cpu_fn = make_fn(cpu)
        cpu_ms = time_op_with_progress(cpu_fn, cpu, progress, cpu_task)
        progress.update(cpu_task, description=f"[blue]CPU: {cpu_ms:.1f}ms")

        # MPS benchmark
        mps_task = progress.add_task("[magenta]MPS (GPU)", total=13)
        mps_fn = make_fn(mps)
        mps_ms = time_op_with_progress(mps_fn, mps, progress, mps_task)
        progress.update(mps_task, description=f"[magenta]MPS: {mps_ms:.1f}ms")

    return BenchResult(name=name, cpu_ms=cpu_ms, mps_ms=mps_ms)


# --- Benchmark definitions ---


def make_matmul(n: int = 2048) -> Callable[[torch.device], Callable[[], torch.Tensor]]:
    """Create matrix multiply benchmark."""

    def make(dev: torch.device) -> Callable[[], torch.Tensor]:
        a = torch.randn((n, n), device=dev, dtype=torch.float32)
        b = torch.randn((n, n), device=dev, dtype=torch.float32)

        @torch.no_grad()
        def fn() -> torch.Tensor:
            return a @ b

        return fn

    return make


def make_elementwise(n: int = 50_000_000) -> Callable[[torch.device], Callable[[], torch.Tensor]]:
    """Create elementwise ops benchmark."""

    def make(dev: torch.device) -> Callable[[], torch.Tensor]:
        x = torch.randn((n,), device=dev, dtype=torch.float32)
        y = torch.randn((n,), device=dev, dtype=torch.float32)

        @torch.no_grad()
        def fn() -> torch.Tensor:
            return torch.nn.functional.gelu(x + y)

        return fn

    return make


def make_conv2d(
    bs: int = 32, cin: int = 64, cout: int = 128, h: int = 56, w: int = 56, k: int = 3
) -> Callable[[torch.device], Callable[[], torch.Tensor]]:
    """Create Conv2d forward benchmark."""

    def make(dev: torch.device) -> Callable[[], torch.Tensor]:
        x = torch.randn((bs, cin, h, w), device=dev, dtype=torch.float32)
        layer = nn.Conv2d(cin, cout, kernel_size=k, padding=k // 2, bias=False).to(dev)
        layer.eval()

        @torch.no_grad()
        def fn() -> torch.Tensor:
            return layer(x)

        return fn

    return make


def make_mlp(
    bs: int = 64, seq: int = 256, d_model: int = 512, mult: int = 4
) -> Callable[[torch.device], Callable[[], torch.Tensor]]:
    """Create MLP forward benchmark (transformer FFN style)."""
    hidden = d_model * mult

    def make(dev: torch.device) -> Callable[[], torch.Tensor]:
        x = torch.randn((bs, seq, d_model), device=dev, dtype=torch.float32)
        mlp = nn.Sequential(
            nn.Linear(d_model, hidden, bias=False),
            nn.GELU(),
            nn.Linear(hidden, d_model, bias=False),
        ).to(dev)
        mlp.eval()

        @torch.no_grad()
        def fn() -> torch.Tensor:
            return mlp(x)

        return fn

    return make


def make_batched_matmul(
    bs: int = 128, m: int = 512, k: int = 512, n: int = 512
) -> Callable[[torch.device], Callable[[], torch.Tensor]]:
    """Create batched matrix multiply benchmark."""

    def make(dev: torch.device) -> Callable[[], torch.Tensor]:
        a = torch.randn((bs, m, k), device=dev, dtype=torch.float32)
        b = torch.randn((bs, k, n), device=dev, dtype=torch.float32)

        @torch.no_grad()
        def fn() -> torch.Tensor:
            return torch.bmm(a, b)

        return fn

    return make


def print_summary(results: list[BenchResult]) -> None:
    """Print a summary table of all benchmark results."""
    table = Table(title="[bold]Benchmark Summary[/bold]", show_header=True, header_style="bold")
    table.add_column("Benchmark", style="cyan")
    table.add_column("CPU (ms)", justify="right", style="blue")
    table.add_column("MPS (ms)", justify="right", style="magenta")
    table.add_column("Speedup", justify="right")

    for r in results:
        speedup_style = "green bold" if r.speedup > 1.5 else "yellow" if r.speedup > 1.0 else "red"
        table.add_row(
            r.name,
            f"{r.cpu_ms:.2f}",
            f"{r.mps_ms:.2f}",
            f"[{speedup_style}]{r.speedup:.2f}x[/{speedup_style}]",
        )

    console.print()
    console.print(table)


def main() -> None:
    """Run all benchmarks with visual progress."""
    torch.manual_seed(42)
    cpu, mps = choose_devices()

    # Header
    console.print(Panel.fit(
        f"[bold white]PyTorch CPU vs MPS (Metal GPU) Benchmark[/bold white]\n"
        f"[dim]CPU: {cpu} | MPS available: {mps.type == 'mps'}[/dim]",
        border_style="bright_blue",
    ))

    if mps.type != "mps":
        console.print("[bold red]⚠ MPS not available! Running CPU-only.[/bold red]")

    # Define benchmarks
    benchmarks = [
        ("MatMul 2048×2048", make_matmul(2048)),
        ("Elementwise 50M", make_elementwise(50_000_000)),
        ("Conv2d 32×64×56×56→128", make_conv2d()),
        ("MLP b64×256 d512", make_mlp()),
        ("Batched MatMul 128×512×512", make_batched_matmul()),
    ]

    results: list[BenchResult] = []
    for name, make_fn in benchmarks:
        result = run_benchmark(name, make_fn, cpu, mps)
        results.append(result)

    print_summary(results)

    # Footer
    console.print("\n[dim]Tip: Watch GPU usage in Activity Monitor → Window → GPU History[/dim]")


if __name__ == "__main__":
    main()
