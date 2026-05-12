from typing import List


def snapshot_files(req: dict) -> List[str]:


    if not isinstance(req, dict):
        return []

    files = req.get("files")
    if not isinstance(files, list):
        return []

    file_names: List[str] = []

    for f in files:
        if isinstance(f, dict):
            name = f.get("file_name")
            if name:
                file_names.append(name)

    return file_names
