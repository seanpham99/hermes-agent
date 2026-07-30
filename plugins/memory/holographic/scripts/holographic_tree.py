#!/usr/bin/env python3
"""
Interactive Holographic Memory Tree Viewer
Navigate facts by category -> entity -> individual facts.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path.home() / ".hermes/hermes-agent"))

from plugins.memory.holographic import HolographicMemoryProvider, _load_plugin_config
from rich.console import Console
from rich.tree import Tree
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
from rich.prompt import Prompt


# ── Tree building functions (exported for testing) ──────────────────────────

def build_tree(facts):
    """Build a nested tree structure: Category -> Entity -> Facts."""
    tree_data = {}

    for fact in facts:
        category = fact.get("category", "uncategorized")
        tags = fact.get("tags", "").split(",") if fact.get("tags") else []

        # Extract entity from tags (look for entity: prefix)
        entity = None
        for tag in tags:
            tag = tag.strip()
            if tag.startswith("entity:"):
                entity = tag[7:]
                break

        # If no entity tag, try to infer from content or use "general"
        if not entity:
            entity = "general"

        # Build nested structure
        if category not in tree_data:
            tree_data[category] = {}
        if entity not in tree_data[category]:
            tree_data[category][entity] = []
        tree_data[category][entity].append(fact)

    return tree_data


def get_time_bucket(created_at_str, now=None):
    """Categorize facts by time."""
    try:
        dt = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
    except:
        return "Unknown"

    if now is None:
        now = datetime.now()
    diff = now - dt

    if diff.days == 0:
        return "Today"
    elif diff.days <= 7:
        return "This Week"
    elif diff.days <= 30:
        return "This Month"
    else:
        return "Older"


# ── Interactive tree viewer ────────────────────────────────────────────────

console = Console()


def build_rich_tree(tree_data, selected_path=None):
    ...

def load_facts():
    """Load all facts from the holographic memory store."""
    config = _load_plugin_config()
    provider = HolographicMemoryProvider(config=config)
    provider.initialize("tree-viewer-session")
    result = provider._handle_fact_store({
        "action": "list",
        "limit": 1000,
        "min_trust": 0.0
    })
    facts = json.loads(result)["facts"]
    return facts


def build_rich_tree(tree_data, selected_path=None):
    """Build a rich.tree.Tree from the nested data."""
    root = Tree("🧠 [bold cyan]Holographic Memory[/bold cyan]")
    
    # Sort categories
    for category in sorted(tree_data.keys()):
        cat_node = root.add(f"[bold yellow]📁 {category}[/bold yellow]")
        
        # Sort entities
        for entity in sorted(tree_data[category].keys()):
            facts = tree_data[category][entity]
            entity_label = f"[green]🏷️  {entity}[/green] ({len(facts)} facts)"
            entity_node = cat_node.add(entity_label)
            
            # Sort facts by date (newest first)
            facts_sorted = sorted(facts, key=lambda f: f.get("created_at", ""), reverse=True)
            
            # Group by time bucket
            time_buckets = {}
            for fact in facts_sorted:
                bucket = get_time_bucket(fact.get("created_at", ""))
                if bucket not in time_buckets:
                    time_buckets[bucket] = []
                time_buckets[bucket].append(fact)
            
            for bucket_name in ["Today", "This Week", "This Month", "Older", "Unknown"]:
                if bucket_name in time_buckets:
                    bucket_facts = time_buckets[bucket_name]
                    bucket_node = entity_node.add(f"[dim]📅 {bucket_name}[/dim] ({len(bucket_facts)})")
                    
                    for fact in bucket_facts:
                        fid = fact.get("fact_id", "?")
                        trust = fact.get("trust_score", 0.0)
                        trust_color = "green" if trust >= 0.7 else "yellow" if trust >= 0.4 else "red"
                        content_preview = fact.get("content", "")[:80] + ("..." if len(fact.get("content", "")) > 80 else "")
                        tags_str = fact.get("tags", "")
                        fact_label = f"[dim]#{fid}[/dim] [{trust_color}]{trust:.2f}[/{trust_color}] {content_preview}"
                        if tags_str:
                            fact_label += f" [dim]({tags_str[:40]})[/dim]"
                        bucket_node.add(fact_label)
    
    return root


def show_fact_detail(fact):
    """Display detailed view of a single fact."""
    fid = fact.get("fact_id", "?")
    trust = fact.get("trust_score", 0.0)
    trust_color = "green" if trust >= 0.7 else "yellow" if trust >= 0.4 else "red"
    content = fact.get("content", "")
    category = fact.get("category", "")
    tags = fact.get("tags", "")
    created = fact.get("created_at", "")
    updated = fact.get("updated_at", "")
    retrieval = fact.get("retrieval_count", 0)
    helpful = fact.get("helpful_count", 0)
    
    panel_content = f"""[bold]Fact ID:[/bold] {fid}
[bold]Trust:[/bold] [{trust_color}]{trust:.2f}[/{trust_color}]
[bold]Category:[/bold] {category}
[bold]Tags:[/bold] {tags or "(none)"}
[bold]Created:[/bold] {created}
[bold]Updated:[/bold] {updated}
[bold]Retrievals:[/bold] {retrieval} | [bold]Helpful:[/bold] {helpful}

[bold]Content:[/bold]
{content}"""
    
    console.print(Panel(panel_content, title=f"📄 Fact #{fid}", border_style="cyan"))


def interactive_tree():
    """Main interactive loop."""
    facts = load_facts()
    tree_data = build_tree(facts)
    
    console.clear()
    console.print("[bold cyan]Holographic Memory Tree Viewer[/bold cyan]")
    console.print("[dim]Controls: ↑/↓ navigate, Enter = expand/fact detail, q = quit, / = search[/dim]\n")
    
    # Since rich.tree doesn't have built-in keyboard navigation,
    # we'll use a simple prompt-based approach
    while True:
        # Build and show tree
        tree = build_rich_tree(tree_data)
        console.print(tree)
        console.print()
        
        console.print("[dim]Options:[/dim]")
        console.print("  [1] View fact by ID")
        console.print("  [2] Search facts")
        console.print("  [3] Filter by category")
        console.print("  [4] Filter by entity")
        console.print("  [q] Quit")
        
        choice = Prompt.ask("\nSelect", choices=["1", "2", "3", "4", "q"], default="q")
        
        if choice == "q":
            break
        elif choice == "1":
            fid = Prompt.ask("Enter Fact ID")
            try:
                fid = int(fid)
                fact = next((f for f in facts if f.get("fact_id") == fid), None)
                if fact:
                    console.clear()
                    show_fact_detail(fact)
                    Prompt.ask("\n[dim]Press Enter to continue[/dim]")
                else:
                    console.print(f"[red]Fact #{fid} not found[/red]")
            except ValueError:
                console.print("[red]Invalid ID[/red]")
        elif choice == "2":
            query = Prompt.ask("Search query").lower()
            matches = [f for f in facts if query in f.get("content", "").lower() or query in f.get("tags", "").lower()]
            console.print(f"\n[bold]Found {len(matches)} matches:[/bold]")
            for f in matches[:20]:
                fid = f.get("fact_id", "?")
                trust = f.get("trust_score", 0.0)
                preview = f.get("content", "")[:60]
                console.print(f"  #{fid} [cyan]{trust:.2f}[/cyan] {preview}...")
            if len(matches) > 20:
                console.print(f"  ... and {len(matches) - 20} more")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]")
        elif choice == "3":
            categories = sorted(set(f.get("category", "") for f in facts))
            console.print("Categories:", ", ".join(categories))
            cat = Prompt.ask("Filter by category (empty = all)")
            # Just show filtered - would need tree rebuild for full filter
            if cat:
                filtered = [f for f in facts if f.get("category") == cat]
                console.print(f"\n[bold]{len(filtered)} facts in '{cat}':[/bold]")
                for f in filtered[:30]:
                    fid = f.get("fact_id", "?")
                    trust = f.get("trust_score", 0.0)
                    preview = f.get("content", "")[:60]
                    console.print(f"  #{fid} [cyan]{trust:.2f}[/cyan] {preview}...")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]")
        elif choice == "4":
            entities = sorted(set(
                next((t[7:] for t in f.get("tags", "").split(",") if t.strip().startswith("entity:")), "general")
                for f in facts
            ))
            console.print("Entities:", ", ".join(entities))
            ent = Prompt.ask("Filter by entity (empty = all)")
            if ent:
                filtered = [f for f in facts if any(t.strip() == f"entity:{ent}" for t in f.get("tags", "").split(","))]
                console.print(f"\n[bold]{len(filtered)} facts for entity '{ent}':[/bold]")
                for f in filtered[:30]:
                    fid = f.get("fact_id", "?")
                    trust = f.get("trust_score", 0.0)
                    preview = f.get("content", "")[:60]
                    console.print(f"  #{fid} [cyan]{trust:.2f}[/cyan] {preview}...")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]")
        
        console.clear()


def main():
    try:
        interactive_tree()
    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting...[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()