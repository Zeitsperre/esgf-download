from __future__ import annotations

import click
import rich
from click.exceptions import Exit

from esgpull import Esgpull
from esgpull.cli.decorators import args, opts
from esgpull.cli.utils import load_facets, print_yaml, totable


@click.command()
@args.facets
@opts.date
@opts.data_node
@opts.distrib
@opts.dry_run
@opts.dump
@opts.file
@opts.latest
@opts.one
@opts.options
@opts.replica
@opts.selection_file
@opts.since
@opts.slice
@opts.zero
def search(
    facets: list[str],
    date: bool,
    data_node: bool,
    distrib: bool,
    dry_run: bool,
    dump: bool,
    file: bool,
    latest: bool | None,
    one: bool,
    options: list[str],
    replica: bool | None,
    selection_file: str | None,
    since: str | None,
    slice_: slice,
    zero: bool,
) -> None:
    """
    Search datasets/files on ESGF

    More info
    """

    esg = Esgpull()
    # TODO: bug with slice_:
    # -> numeric ids are not consistent due to sort by instance_id
    if zero:
        slice_ = slice(0, 0)
    elif one:
        slice_ = slice(0, 1)
    offset = slice_.start
    size = slice_.stop - slice_.start
    with esg.context() as ctx:
        ctx.distrib = distrib
        ctx.latest = latest
        ctx.since = since
        ctx.replica = replica
        load_facets(ctx.query, facets, selection_file)
        if file:
            hits = ctx.file_hits
        else:
            hits = ctx.hits
        if dry_run:
            queries = ctx._build_queries_search(
                hits, file=file, max_results=size, offset=offset
            )
            rich.print(queries)
            raise Exit(0)
        if options:
            ctx.query.facets = options
            results = ctx.options()
            rich.print(results)
            raise Exit(0)
        if dump:
            print_yaml(ctx.query.dump())
            raise Exit(0)
        results = ctx.search(
            file=file,
            max_results=size,
            offset=offset,
            hits=hits,
        )
        nb = sum(hits)
        item_type = "file" if file else "dataset"
        rich.print(f"Found {nb} {item_type}{'s' if nb > 1 else ''}.")
        if results:
            rich.print(totable(results, data_node, date, slice_))
