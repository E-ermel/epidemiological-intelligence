import fsspec


def clear_path(path: str) -> None:
    fs, root = fsspec.core.url_to_fs(path)

    if fs.exists(root):
        fs.rm(root, recursive=True)
