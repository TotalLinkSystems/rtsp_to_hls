import os
import shutil

def create_folder_if_not_exists(folder_path: str) -> None:
    """Create a folder if it does not exist."""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def delete_folder_if_exists(folder_path: str) -> None:
    """Delete a folder if it exists."""
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)

def update_folder(folder_path: str, new_name: str) -> None:
    """Rename a folder."""
    if os.path.exists(folder_path):
        new_path = os.path.join(os.path.dirname(folder_path), new_name)
        os.rename(folder_path, new_path)

        