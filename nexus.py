#!/usr/bin/env python3
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
            '📸 Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff', '.ico', '.raw', '.heic', '.jfif', '.psd', '.ai'],
            '📄 Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xlsx', '.csv', '.ppt', '.pptx', '.pages', '.numbers', '.key', '.md', '.epub', '.mobi'],
            '🎵 Audio': ['.mp3', '.wav', '.flac', '.m4a', '.aac', '.wma', '.ogg', '.midi', '.aiff', '.alac', '.dsd', '.dsf'],
            '🎬 Video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.vob', '.ts'],
            '🗄️ Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.iso', '.cab', '.jar', '.war', '.ear'],
            '💻 Code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.php', '.rb', '.swift', '.go', '.rs', '.sql', '.sh', '.bat', '.ps1', '.tsx', '.jsx', '.vue'],
            '⚙️ Executables': ['.exe', '.msi', '.app', '.dmg', '.deb', '.rpm', '.apk', '.ipa', '.appx'],
            '🎨 Design': ['.psd', '.ai', '.xd', '.sketch', '.fig', '.indd', '.ae', '.afdesign', '.blend'],
            '📊 Data': ['.json', '.xml', '.yaml', '.csv', '.sql', '.db', '.sqlite', '.mdb', '.accdb'],
            '📝 Text': ['.txt', '.md', '.log', '.ini', '.cfg', '.conf', '.env'],
            '📚 Books': ['.pdf', '.epub', '.mobi', '.azw', '.azw3', '.fb2', '.djvu'],
            '📦 Software': ['.iso', '.img', '.vhd', '.vmdk', '.ova'],
            '🔒 Security': ['.key', '.pem', '.crt', '.cer', '.p12', '.pfx'],
            '🎮 Games': ['.sav', '.rom', '.nes', '.snes', '.gba', '.nds'],
            '📧 Email': ['.eml', '.msg', '.pst', '.ost', '.mbox'],
            '🔤 Fonts': ['.ttf', '.otf', '.woff', '.woff2', '.eot']
        }
        self.categories: Dict[str, List[str]] = self.load_categories(config_file)
        self.used_categories: Set[str] = set()

    def load_categories(self, config_file: Optional[str]) -> Dict[str, List[str]]:
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading config file: {e}. Using default categories.")
                return self.default_categories
        return self.default_categories

    def save_categories(self, config_file: str) -> None:
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, indent=4, ensure_ascii=False)
            logger.info(f"Categories saved to {config_file}.")
        except IOError as e:
            logger.error(f"Error saving config file: {e}.")

    @staticmethod
    def get_file_hash(filepath: str) -> str:
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except IOError as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return ""

    @staticmethod
    def get_file_size_category(size_bytes: int) -> str:
        if size_bytes < 1024 * 1024:
            return "small"
        elif size_bytes < 100 * 1024 * 1024:
            return "medium"
        else:
            return "large"

    @staticmethod
    def strip_emojis(text: str) -> str:
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"  # additional symbols
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)

    def get_category(self, filename: str) -> str:
        # Handle files without extensions
        ext = os.path.splitext(filename)[1].lower() if os.path.splitext(filename)[1] else ""
        for category, extensions in self.categories.items():
            if ext in extensions:
                return category
        return "❓ Others"

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

    def organize_files(self, sort_by_date: bool = False, sort_by_size: bool = False, age_limit: Optional[float] = None) -> Dict[str, int]:
        file_hashes = {}
        stats = {'total': 0, 'moved': 0, 'skipped': 0, 'errors': 0}

        all_files = []
        for root, _, files in os.walk(self.directory):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    all_files.append((file, file_path))

        stats['total'] = len(all_files)

        with self.console.status("[bold green]Organizing files...[/bold green]"):
            with Progress(BarColumn(), TimeRemainingColumn(), console=self.console) as progress:
                task = progress.add_task("[cyan]Sorting files...", total=stats['total'])
                for file, file_path in all_files:
                    try:
                        file_path_obj = Path(file_path).resolve()
                        if any(Path(self.directory, cat).resolve() in file_path_obj.parents for cat in self.categories.keys()):
                            continue

                        if age_limit is not None:
                            file_age = (time.time() - os.path.getmtime(file_path)) / (24 * 3600)
                            if file_age > age_limit:
                                stats['skipped'] += 1
                                continue

                        file_hash = self.get_file_hash(file_path)
                        if file_hash in file_hashes:
                            self.console.print(f"[yellow]📑 Duplicate found: {file} is identical to {file_hashes[file_hash]}[/yellow]")
                            stats['skipped'] += 1
                            continue

                        file_hashes[file_hash] = file

                        category = self.get_category(file)
                        self.used_categories.add(category)
                        folder_name = self.strip_emojis(category).strip() or "Uncategorized"
                        category_path = os.path.join(self.directory, folder_name)
                        os.makedirs(category_path, exist_ok=True)

                        if sort_by_size:
                            size_category = self.get_file_size_category(os.path.getsize(file_path))
                            category_path = os.path.join(category_path, size_category)
                            os.makedirs(category_path, exist_ok=True)

                        if sort_by_date:
                            date_str = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m')
                            category_path = os.path.join(category_path, date_str)
                            os.makedirs(category_path, exist_ok=True)

                        new_file_path = os.path.join(category_path, file)
                        if os.path.exists(new_file_path):
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
                            filename, extension = os.path.splitext(file)
                            new_file_path = os.path.join(category_path, f"{filename}_{timestamp}{extension}")

                        shutil.move(file_path, new_file_path)
                        self.console.print(f"[green]✨ Moved {file} to {folder_name}[/green]")
                        stats['moved'] += 1

                    except Exception as e:
                        self.console.print(f"[bold red]❌ Error processing {file}: {str(e)}[/bold red]")
                        stats['errors'] += 1
                    progress.update(task, advance=1)

        for root, dirs, _ in os.walk(self.directory, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        self.console.print(f"[yellow]🗑️ Removed empty directory: {dir_path}[/yellow]")
                except OSError:
                    continue

        return stats

def main() -> None:
    console = Console()
    console.print("[bold cyan]🌟 Welcome to NexusSorter - Advanced File Organization System[/bold cyan]")

    directory = input("📁 Enter the directory path to organize: ").strip()
    if not os.path.exists(directory):
        console.print("[bold red]❌ Error: Directory does not exist![/bold red]")
        return

    config_file = input("⚙️ Enter path to category config file (or press Enter for defaults): ").strip()
    sort_by_date = input("📅 Sort into date-based folders? (y/n): ").strip().lower() == 'y'
    sort_by_size = input("📊 Sort by file size? (y/n): ").strip().lower() == 'y'

    age_limit: Optional[float] = None
    if input("⏰ Apply age limit to files? (y/n): ").strip().lower() == 'y':
        try:
            age_limit = float(input("Enter maximum age in days: "))
        except ValueError:
            console.print("[yellow]⚠️ Invalid age limit. Processing all files.[/yellow]")

    organizer = NexusSorter(directory, config_file if config_file else None)

    if config_file and not os.path.exists(config_file):
        if input("💾 Save default categories to config file? (y/n): ").strip().lower() == 'y':
            organizer.save_categories(config_file)

    console.print("\n[bold cyan]📁 Initial Directory Structure:[/bold cyan]")
    console.print(organizer.create_directory_map())

    stats = organizer.organize_files(sort_by_date, sort_by_size, age_limit)

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