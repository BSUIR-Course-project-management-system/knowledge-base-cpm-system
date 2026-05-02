def clear_logs(filename: str) -> None:
    with open(filename, "w") as f:
        f.truncate(0)
