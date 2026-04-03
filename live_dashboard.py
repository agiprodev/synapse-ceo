import time
import httpx
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.console import Console

console = Console()

def get_stats():
    try:
        # بنكلم السيرفر اللي شغال على 5555
        with httpx.Client() as client:
            res = client.get("http://127.0.0.1:5555/v1/analytics/dashboard/cust_001")
            return res.json()["hero_kpis"]
    except Exception:
        return {"money_saved": 0, "hours_saved": 0}

def generate_layout(stats):
    table = Table(title="[bold green]🚀 Synapse Beast v4 - Live ROI Hub[/bold green]", border_style="bright_blue")
    table.add_column("Metric", style="cyan", justify="right")
    table.add_column("Value", style="bold yellow", justify="left")
    
    table.add_row("Total Money Saved", f"${stats.get('money_saved', 0)}")
    table.add_row("Total Time Saved", f"{stats.get('hours_saved', 0)} Hours")
    table.add_row("System Status", "[bold green]● PROTECTED[/bold green]")
    table.add_row("AI Thinking Mode", "[italic white]Active RAG-Gemini[/italic white]")
    
    return Panel(
        table, 
        title="[bold white]Real-Time Executive Summary[/bold white]",
        subtitle="[blink yellow]Updating Live...[/blink yellow]",
        border_style="green"
    )

# تشغيل الـ Live Update
try:
    stats = get_stats()
    with Live(generate_layout(stats), refresh_per_second=1) as live:
        while True:
            time.sleep(2)
            current_stats = get_stats()
            live.update(generate_layout(current_stats))
except KeyboardInterrupt:
    console.print("\n[bold red]Dashboard Closed.[/bold red]")
