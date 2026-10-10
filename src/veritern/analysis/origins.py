from veritern.schemas import Source


def cluster_origins(sources: list[Source]) -> None:
    """Exact normalized copies form one origin. Other independence remains unknown."""
    groups = {}
    for source in sources:
        if source.text:
            source.origin_group = groups.setdefault(source.content_hash, source.id)
