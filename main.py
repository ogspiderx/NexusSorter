import os
import re
import shutil
import sys
import time
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional
from rich import print
from rich.console import Console
from rich.tree import Tree
from rich.progress import Progress, BarColumn, TimeRemainingColumn

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class NexusSorter:
    def __init__(self, directory: str, config_file: Optional[str] = None):
        self.directory = directory
        self.console = Console()
        self.default_categories: Dict[str, List[str]] = {
            'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff'],
            'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xlsx', '.csv'],
            'Audio': ['.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'],
            'Video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'],
            'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
            'Code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.php', '.sh'],
            'Executables': ['.exe', '.msi', '.apk', '.dmg'],
            'Books': ['.pdf', '.epub', '.mobi', '.azw3'],
            'Fonts': ['.ttf', '.otf', '.woff'],
            'Others': []
        }
        self.categories = self.load_categories(config_file)
        self.used_categories: Set[str] = set()

    def load_categories(self, config_file: Optional[str]) -> Dict[str, List[str]]:
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading config file: {e}. Using default categories.")
        return self.default_categories

    def get_file_hash(self, filepath: str) -> str:
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except IOError as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return ""

    def strip_emojis(self, text: str) -> str:
        emoji_pattern = re.compile("["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)

    def get_category(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        for category, extensions in self.categories.items():
            if ext in extensions:
                return category
        return "Others"

    def create_directory_map(self) -> Tree:
        tree = Tree(f"📁 {os.path.basename(self.directory)}")
        def add_to_tree(directory: str, tree_node: Tree) -> None:
            try:
                for item in os.listdir(directory):
                    full_path = os.path.join(directory, item)
                    if os.path.isdir(full_path):
                        subtree = tree_node.add(f"📁 {item}")
                        add_to_tree(full_path, subtree)
                    else:
                        tree_node.add(f"📄 {item}")
            except PermissionError:
                tree_node.add("[red]❌ Access Denied[/red]")
        add_to_tree(self.directory, tree)
        return tree

    def organize_files(self, sort_by_date: bool = False) -> Dict[str, int]:
        file_hashes = {}
        stats = {'total': 0, 'moved': 0, 'skipped': 0, 'errors': 0}

        all_files = [os.path.join(root, f) for root, _, files in os.walk(self.directory) for f in files]
        stats['total'] = len(all_files)

        with Progress(BarColumn(), TimeRemainingColumn(), console=self.console) as progress:
            task = progress.add_task("[cyan]Sorting files...", total=stats['total'])

            for file_path in all_files:
                try:
                    file_name = os.path.basename(file_path)
                    if file_path in file_hashes:
                        self.console.print(f"[yellow]📑 Skipped duplicate: {file_name}[/yellow]")
                        stats['skipped'] += 1
                        continue

                    category = self.get_category(file_name)
                    self.used_categories.add(category)
                    category_path = os.path.join(self.directory, self.strip_emojis(category))
                    os.makedirs(category_path, exist_ok=True)

                    if sort_by_date:
                        date_str = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m')
                        category_path = os.path.join(category_path, date_str)
                        os.makedirs(category_path, exist_ok=True)

                    new_file_path = os.path.join(category_path, file_name)
                    shutil.move(file_path, new_file_path)
                    self.console.print(f"[green]✔ Moved {file_name} to {category}[/green]")
                    stats['moved'] += 1

                except Exception as e:
                    self.console.print(f"[bold red]❌ Error processing {file_name}: {str(e)}[/bold red]")
                    stats['errors'] += 1
                progress.update(task, advance=1)

        return stats

def main() -> None:
    console = Console()
    console.print("[bold cyan]🌟 Welcome to NexusSorter - Advanced File Organizer[/bold cyan]")

    directory = input("📁 Enter the directory path to organize: ").strip()
    if not os.path.exists(directory):
        console.print("[bold red]❌ Error: Directory does not exist![/bold red]")
        return

    sort_by_date = input("📅 Sort into date-based folders? (y/n): ").strip().lower() == 'y'
    organizer = NexusSorter(directory)

    console.print("\n[bold cyan]📁 Initial Directory Structure:[/bold cyan]")
    console.print(organizer.create_directory_map())

    stats = organizer.organize_files(sort_by_date)

    console.print("\n[bold cyan]📁 Final Directory Structure:[/bold cyan]")
    console.print(organizer.create_directory_map())

    console.print("\n[bold green]✨ Organization completed![/bold green]")
    console.print(f"📊 Total files processed: {stats['total']}")
    console.print(f"✅ Files moved: {stats['moved']}")
    console.print(f"⏭️ Files skipped: {stats['skipped']}")
    console.print(f"❌ Errors encountered: {stats['errors']}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[bold red]🚫 Operation cancelled by user.[/bold red]")
        sys.exit(1)
    except Exception as e:
        print(f"\n[bold red]❌ An unexpected error occurred: {e}[/bold red]")
        sys.exit(1)
