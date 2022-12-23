from __future__ import annotations

from typing import Any, Iterator, Literal

import sqlalchemy as sa
from rich.console import Console, ConsoleOptions
from rich.measure import Measurement, measure_renderables
from rich.padding import Padding
from rich.text import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing_extensions import NotRequired, TypedDict

from esgpull.models.base import Base, Sha
from esgpull.models.file import File
from esgpull.models.options import Options
from esgpull.models.selection import FacetValues, Selection
from esgpull.models.tag import Tag

query_file_proxy = sa.Table(
    "query_file",
    Base.metadata,
    sa.Column("query_sha", Sha, sa.ForeignKey("query.sha"), primary_key=True),
    sa.Column("file_sha", Sha, sa.ForeignKey("file.sha"), primary_key=True),
)
query_tag_proxy = sa.Table(
    "query_tag",
    Base.metadata,
    sa.Column("query_sha", Sha, sa.ForeignKey("query.sha"), primary_key=True),
    sa.Column("tag_sha", Sha, sa.ForeignKey("tag.sha"), primary_key=True),
)


class QueryDict(TypedDict):
    tags: NotRequired[str | list[str]]
    transient: NotRequired[Literal[True]]
    require: NotRequired[str]
    options: NotRequired[dict[str, bool | None]]
    selection: NotRequired[dict[str, FacetValues]]


class Query(Base):
    __tablename__ = "query"

    tags: Mapped[list[Tag]] = relationship(
        secondary=query_tag_proxy,
        default_factory=list,
    )
    transient: Mapped[bool] = mapped_column(default=False)
    require: Mapped[str | None] = mapped_column(Sha, default=None)
    options_sha: Mapped[str] = mapped_column(
        Sha,
        sa.ForeignKey("options.sha"),
        init=False,
    )
    options: Mapped[Options] = relationship(default_factory=Options)
    selection_sha: Mapped[int] = mapped_column(
        Sha,
        sa.ForeignKey("selection.sha"),
        init=False,
    )
    selection: Mapped[Selection] = relationship(default_factory=Selection)
    files: Mapped[list[File]] = relationship(
        secondary=query_file_proxy,
        default_factory=list,
    )

    # TODO: improve typing
    def __setattr__(self, name: str, value: Any) -> None:
        if name == "tags" and isinstance(value, (str, Tag)):
            value = [value]
        match name, value:
            case "tags", list() | tuple():
                tags: list[Tag] = []
                for tag in value:
                    if isinstance(tag, str):
                        tags.append(Tag(name=tag))
                    else:
                        tags.append(tag)
                value = tags
            case "options", dict():
                value = Options(**value)
            case "selection", dict():
                value = Selection(**value)
            case _, _:
                ...
        super().__setattr__(name, value)

    def _as_bytes(self) -> bytes:
        self_tuple = (self.require, self.options.sha, self.selection.sha)
        return str(self_tuple).encode()

    def compute_sha(self) -> None:
        for tag in self.tags:
            tag.compute_sha()
        self.options.compute_sha()
        self.selection.compute_sha()
        super().compute_sha()

    @staticmethod
    def format_name(sha: str) -> str:
        return f"#{sha[:6]}"

    @property
    def tag_name(self) -> str | None:
        if len(self.tags) == 1:
            return self.tags[0].name
        else:
            return None

    @property
    def short_require(self) -> str:
        if self.require is not None:
            if len(self.require) == 40:
                return self.format_name(self.require)
            else:
                return self.require
        else:
            raise ValueError

    @property
    def name(self) -> str:
        # TODO: make these 2 lines useless
        if self.sha is None:
            self.compute_sha()
        return self.format_name(self.sha)

    def items(
        self,
        include_name: bool = False,
        short_require: bool = False,
    ) -> Iterator[tuple[str, Any]]:
        if include_name:
            yield "name", self.name
        if self.tags:
            yield "tags", [tag.name for tag in self.tags]
        if self.transient:
            yield "transient", self.transient
        if self.require is not None:
            if short_require:
                require = self.short_require
            else:
                require = self.require
            yield "require", require
        if self.options:
            yield "options", self.options
        if self.selection:
            yield "selection", self.selection

    def asdict(self) -> QueryDict:
        result: QueryDict = {}
        if len(self.tags) > 1:
            result["tags"] = [tag.name for tag in self.tags]
        elif len(self.tags) == 1:
            result["tags"] = self.tags[0].name
        if self.transient:
            result["transient"] = self.transient
        if self.require is not None:
            result["require"] = self.require
        if self.options:
            result["options"] = self.options.asdict()
        if self.selection:
            result["selection"] = self.selection.asdict()
        return result

    def clone(self, compute_sha: bool = True) -> Query:
        instance = Query(**self.asdict())
        if compute_sha:
            instance.compute_sha()
        return instance

    def no_require(self) -> Query:
        cl = self.clone(compute_sha=True)
        cl._rich_no_require = True
        return cl

    def __lshift__(self, other: Query) -> Query:
        result = self.clone(compute_sha=False)
        # if self.name != other.require:
        #     raise ValueError(f"{self.name} is not required by {other.name}")
        for tag in other.tags:
            if tag not in self.tags:
                result.tags.append(tag)
        for name, option in other.options.items():
            setattr(self.options, name, option)
        for name, values in other.selection.items():
            result.selection[name] = values
        result.transient = other.transient
        result.compute_sha()
        return result

    def __rich_repr__(self) -> Iterator:
        yield from self.items(include_name=True, short_require=True)

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        items = [
            f"{k}={v}"
            for k, v in self.items(include_name=True, short_require=True)
        ]
        return f"{cls_name}(" + ", ".join(items) + ")"

    def __guide(self, text: Text, size: int = 2) -> Text:
        return text.with_indent_guides(size, style="dim default")

    def __wrap_values(
        self,
        text: Text,
        values: list[str],
        maxlen: int = 40,
    ) -> Text:
        text.append("[")  # ]
        textlen = len(text)
        maxlen = 40 - textlen
        padding = " " * textlen
        lines: list[str] = []
        curline: list[str] = []
        for value in values:
            newline = curline + [value]
            strline = ", ".join(newline)
            if len(strline) < maxlen:
                curline = newline
            else:
                curline = []
                lines.append(strline)
        if not lines:
            lines = [", ".join(curline)]
        text.append(lines[0])
        for line in lines[1:]:
            text.append(f",\n{padding}{line}")
            text = self.__guide(text, textlen)
        text.append("]")
        return text

    def __rich_console__(
        self,
        console: Console,
        options: ConsoleOptions,
    ) -> Iterator[Text | Padding]:
        text = Text()
        text.append(self.name, style="b green")
        if self.transient:
            text.append(" <transient>", style="i red")
        if not hasattr(self, "_rich_no_require") and self.require is not None:
            text.append(" [require: ")
            text.append(self.short_require, style="green")
            text.append("]")
        yield text
        if self.tags:
            text = Text("  ")
            text.append("tags", style="magenta")
            text.append(": ")
            text = self.__wrap_values(text, [tag.name for tag in self.tags])
            yield self.__guide(text)
        for name, option in self.options.items():
            text = Text("  ")
            text.append(name, style="yellow")
            text.append(f": {option.value}")
            yield self.__guide(text)
        query_term: list[str] | None = None
        for name, values in self.selection.items():
            if name == "query":
                query_term = values
                continue
            item = Text("  ")
            item.append(name, style="blue")
            if len(values) == 1:
                item.append(f": {values[0]}")
            else:
                item.append(": ")
                item = self.__wrap_values(item, values)
            yield self.__guide(item)
        if query_term is not None:
            item = Text("  ", style="blue")
            if len(query_term) == 1:
                item.append(query_term[0])
            else:
                item = self.__wrap_values(item, query_term)
            yield self.__guide(item)

    def __rich_measure__(
        self,
        console: Console,
        options: ConsoleOptions,
    ) -> Measurement:
        renderables = list(self.__rich_console__(console, options))
        return measure_renderables(console, options, renderables)
