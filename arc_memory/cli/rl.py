"""
Command-line interface for the reinforcement learning pipeline.
"""

import enum
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from arc_memory.sdk.core import Arc
from arc_memory.rl.run import (
    train_pipeline,
    evaluate_pipeline,
    collect_and_train_offline,
    demo_pipeline,
    initialize_pipeline,
)

app = typer.Typer(
    name="rl",
    help="Reinforcement learning pipeline for Arc Memory.",
    add_completion=False,
)

console = Console()


class AgentType(str, enum.Enum):
    """Agent types for the RL pipeline."""

    RANDOM = "random"
    QTABLE = "qtable"


class Mode(str, enum.Enum):
    """Modes for the RL pipeline."""

    TRAIN = "train"
    EVALUATE = "evaluate"
    COLLECT = "collect"
    DEMO = "demo"


@app.command()
def run(
    mode: Mode = typer.Option(Mode.TRAIN, help="Mode to run the pipeline in"),
    agent_type: AgentType = typer.Option(AgentType.QTABLE, help="Type of agent to use"),
    num_episodes: int = typer.Option(10, help="Number of episodes for training or evaluation"),
    num_steps: int = typer.Option(10, help="Number of steps for demo mode"),
    save_dir: str = typer.Option("models", help="Directory to save models"),
    plot_dir: str = typer.Option("plots", help="Directory to save plots"),
    agent_path: Optional[str] = typer.Option(None, help="Path to the agent (for evaluate or demo mode)"),
    buffer_path: Optional[str] = typer.Option(None, help="Path to the buffer (for collect mode)"),
    num_training_epochs: int = typer.Option(10, help="Number of epochs for offline training"),
):
    """
    Run the reinforcement learning pipeline.
    
    This command provides access to the various modes of the RL pipeline:
    - train: Train an agent from scratch
    - evaluate: Evaluate a trained agent
    - collect: Collect experiences and train offline
    - demo: Demonstrate a trained agent
    """
    try:
        # Initialize the SDK
        sdk = Arc("./")  # Initialize with current directory
        
        # Create the save directories if they don't exist
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs(plot_dir, exist_ok=True)
        
        if mode == Mode.TRAIN:
            console.print(f"[bold]Training agent for {num_episodes} episodes...[/bold]")
            metrics = train_pipeline(
                sdk,
                num_episodes=num_episodes,
                agent_type=agent_type.value,
                save_dir=save_dir,
                plot_dir=plot_dir,
            )
            
            # Display the results
            console.print("\n[bold]Training completed![/bold]")
            console.print(f"Agent saved to {save_dir}")
            console.print(f"Plots saved to {plot_dir}")
            
            # Create a table of the final metrics
            table = Table(title="Training Metrics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Episodes", str(num_episodes))
            table.add_row("Final Episode Reward", f"{metrics['episode_rewards'][-1]:.2f}")
            table.add_row("Average Reward (last 10)", f"{sum(metrics['episode_rewards'][-10:]) / min(10, len(metrics['episode_rewards'])):.2f}")
            table.add_row("Final Episode Length", str(metrics['episode_lengths'][-1]))
            
            console.print(table)
        
        elif mode == Mode.EVALUATE:
            if not agent_path:
                console.print("[bold red]Error: agent_path is required for evaluate mode[/bold red]")
                raise typer.Exit(1)
            
            console.print(f"[bold]Evaluating agent for {num_episodes} episodes...[/bold]")
            metrics = evaluate_pipeline(
                sdk,
                agent_path=agent_path,
                agent_type=agent_type.value,
                num_episodes=num_episodes,
            )
            
            # Display the results
            console.print("\n[bold]Evaluation completed![/bold]")
            
            # Create a table of the evaluation metrics
            table = Table(title="Evaluation Metrics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Number of Episodes", str(num_episodes))
            table.add_row("Average Reward", f"{metrics['avg_reward']:.2f}")
            table.add_row("Average Episode Length", f"{metrics['avg_length']:.2f}")
            
            console.print(table)
        
        elif mode == Mode.COLLECT:
            console.print(f"[bold]Collecting experiences for {num_episodes} episodes and training for {num_training_epochs} epochs...[/bold]")
            collect_and_train_offline(
                sdk,
                num_collection_episodes=num_episodes,
                num_training_epochs=num_training_epochs,
                agent_type=agent_type.value,
                save_dir=save_dir,
                buffer_path=buffer_path,
            )
            
            # Display the results
            console.print("\n[bold]Collection and training completed![/bold]")
            console.print(f"Agent saved to {save_dir}")
            if buffer_path:
                console.print(f"Experiences saved to {buffer_path}")
        
        elif mode == Mode.DEMO:
            if not agent_path:
                console.print("[bold red]Error: agent_path is required for demo mode[/bold red]")
                raise typer.Exit(1)
            
            console.print(f"[bold]Running demo for {num_steps} steps...[/bold]")
            demo_pipeline(
                sdk,
                agent_path=agent_path,
                agent_type=agent_type.value,
                num_steps=num_steps,
            )
            
            console.print("\n[bold]Demo completed![/bold]")
    
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        raise typer.Exit(1)


@app.command()
def info():
    """
    Show information about the RL pipeline.
    
    This command displays information about the available agent types,
    reward components, and other RL pipeline settings.
    """
    console.print("[bold]Arc Memory RL Pipeline[/bold]")
    console.print("\nThis module implements a reinforcement learning (RL) system for predicting and evaluating code changes, blast radius, and other properties based on the Arc Memory knowledge graph.")
    
    # Agent types
    console.print("\n[bold]Agent Types:[/bold]")
    table = Table(title="Available Agent Types")
    table.add_column("Type", style="cyan")
    table.add_column("Description", style="green")
    
    table.add_row("random", "A simple agent that takes random actions")
    table.add_row("qtable", "A Q-table based agent that uses an epsilon-greedy policy")
    
    console.print(table)
    
    # Reward components
    console.print("\n[bold]Reward Components:[/bold]")
    table = Table(title="Multi-Component Reward Function")
    table.add_column("Component", style="cyan")
    table.add_column("Description", style="green")
    
    table.add_row("Correctness (Rcorr)", "Rewards for code changes passing tests and static analysis")
    table.add_row("Completion (Rcomp)", "Progress toward overall goal (e.g., % of services migrated)")
    table.add_row("Reasoning (Rreas)", "Quality of intermediate reasoning or planning steps")
    table.add_row("Tool Use (Rtool)", "Efficiency in selecting and using appropriate tools")
    table.add_row("KG Enrichment (Rkg)", "Adding valuable provenance to the knowledge graph")
    table.add_row("Coordination (Rcausal)", "Successfully unblocking other agents' operations")
    
    console.print(table)
    
    # Example commands
    console.print("\n[bold]Example Commands:[/bold]")
    console.print("Train an agent:")
    console.print("  arc rl run --mode train --num-episodes 100 --agent-type qtable")
    console.print("\nEvaluate an agent:")
    console.print("  arc rl run --mode evaluate --agent-path models/agent_episode_100.json --num-episodes 10")
    console.print("\nCollect experiences and train offline:")
    console.print("  arc rl run --mode collect --num-episodes 10 --num-training-epochs 20 --buffer-path experiences.pkl")
    console.print("\nRun a demo:")
    console.print("  arc rl run --mode demo --agent-path models/agent_episode_100.json --num-steps 10")


@app.command()
def test():
    """
    Run a simple test of the RL pipeline.
    
    This command runs a short training session with a random agent
    to verify that the RL pipeline is working correctly.
    """
    console.print("[bold]Running RL pipeline test...[/bold]")
    
    try:
        # Initialize the SDK
        sdk = Arc("./")
        
        # Create a temporary directory for test outputs
        test_dir = Path("test_rl")
        test_dir.mkdir(exist_ok=True)
        
        # Train for a few episodes
        console.print("Training a random agent for 3 episodes...")
        metrics = train_pipeline(
            sdk,
            num_episodes=3,
            agent_type="random",
            save_dir=str(test_dir / "models"),
            plot_dir=str(test_dir / "plots"),
        )
        
        # Check if the agent was saved
        agent_path = test_dir / "models" / "agent_episode_3.json"
        if agent_path.exists():
            console.print(f"Agent saved to {agent_path}")
        else:
            console.print("[bold red]Warning: Agent file was not created[/bold red]")
        
        # Check if plots were created
        plots_dir = test_dir / "plots"
        if plots_dir.exists() and any(plots_dir.iterdir()):
            console.print(f"Plots saved to {plots_dir}")
        else:
            console.print("[bold red]Warning: Plot files were not created[/bold red]")
        
        # Check if the metrics were recorded
        if metrics and "episode_rewards" in metrics and len(metrics["episode_rewards"]) == 3:
            console.print("Metrics were recorded correctly")
        else:
            console.print("[bold red]Warning: Metrics were not recorded correctly[/bold red]")
        
        console.print("\n[bold green]Test completed successfully![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Test failed: {str(e)}[/bold red]")
        raise typer.Exit(1) 
