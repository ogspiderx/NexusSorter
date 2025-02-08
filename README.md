# NexusSorter - Smart File Organizer

## 📌 Overview
NexusSorter is an intelligent file organization tool that automatically categorizes files into well-structured folders. Whether you need to sort documents, images, videos, or even software, NexusSorter simplifies your file management experience with advanced sorting options.

## ✨ Features
- **Automatic Categorization**: Sorts files into predefined categories like Images, Documents, Audio, Video, etc.
- **Date & Size-Based Sorting**: Organizes files into subfolders based on modification date and file size.
- **Duplicate Detection**: Identifies duplicate files using MD5 hashing and skips them.
- **Custom Configurations**: Modify category mappings using a JSON config file.
- **Visual Directory Tree**: Displays a structured tree view of your organized files.
- **No Emojis in Folder Names**: Ensures compatibility across operating systems.

## 🚀 How to Use

### **Running from Source Code (Python)**

1. **Clone the Repository**
   ```sh
   git clone https://github.com/ogspiderx/NexusSorter.git
   cd NexusSorter
   ```

2. **Create a Virtual Environment (Recommended)**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```sh
   pip install -r requirements.txt
   ```

4. **Run NexusSorter**
   ```sh
   python nexus_sorter.py
   ```

5. **Provide Input**
   - Enter the directory path where your files need organization.
   - Choose additional sorting preferences like date-based or size-based organization.

6. **Organized Files!**
   - Your files will be neatly categorized into structured folders.
   - A directory tree view will be displayed at the end.


Enjoy a cleaner, more organized file system with NexusSorter! 🚀

