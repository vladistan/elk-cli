import typer


def confirm_deletion(index: str, doc_id: str) -> bool:
    return typer.confirm(f"Delete document {index}/{doc_id}?")


def confirm_cleanup(count: int) -> bool:
    return typer.confirm(f"Delete {count} test documents?")
