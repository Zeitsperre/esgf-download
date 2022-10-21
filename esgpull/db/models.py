from __future__ import annotations

from datetime import datetime
from enum import Enum, unique
from typing import Annotated, Sequence

import sqlalchemy as sa
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    # registry,
)

from esgpull.utils import find_int, find_str

int_pk = Annotated[int, mapped_column(primary_key=True)]
str_pk = Annotated[str, mapped_column(primary_key=True)]


class Table(MappedAsDataclass, DeclarativeBase):
    # registry = registry()
    ...


@unique
class FileStatus(str, Enum):
    new = "new"
    queued = "queued"
    starting = "starting"
    started = "started"
    pausing = "pausing"
    paused = "paused"
    error = "error"
    cancelled = "cancelled"
    done = "done"

    @classmethod
    def retryable(cls) -> Sequence[FileStatus]:
        return [
            cls.new,
            cls.starting,
            cls.started,
            cls.pausing,
            cls.paused,
            cls.error,
            cls.cancelled,
        ]


class File(Table):
    __tablename__ = "file"

    id: Mapped[int_pk] = mapped_column(init=False)
    file_id: Mapped[str] = mapped_column(unique=True)
    dataset_id: Mapped[str]
    master_id: Mapped[str]
    url: Mapped[str]
    version: Mapped[str] = mapped_column(sa.String(16))
    filename: Mapped[str] = mapped_column(sa.String(255))
    local_path: Mapped[str] = mapped_column(sa.String(255))
    data_node: Mapped[str] = mapped_column(sa.String(40))
    checksum: Mapped[str] = mapped_column(sa.String(64))
    checksum_type: Mapped[str] = mapped_column(sa.String(16))
    size: Mapped[int]
    status: Mapped[FileStatus] = mapped_column(
        sa.Enum(FileStatus), default=FileStatus.new
    )
    raw: Mapped[dict] = mapped_column(
        sa.JSON, default_factory=dict, repr=False
    )
    last_updated: Mapped[datetime] = mapped_column(
        init=False,
        repr=False,
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    # duration: int
    # rate: int
    # start_date: str
    # end_date: str
    # crea_date: str
    # status: int
    # error_msg: str
    # sdget_status: str
    # sdget_error_msg: str
    # priority: int
    # tracking_id: str
    # last_access_date: str

    @staticmethod
    def get_local_path(raw: dict, version: str) -> str:
        flat_raw = {}
        for k, v in raw.items():
            if isinstance(v, list) and len(v) == 1:
                flat_raw[k] = v[0]
            else:
                flat_raw[k] = v
        template = find_str(flat_raw["directory_format_template_"])
        # format: "%(a)/%(b)/%(c)/..."
        template = template.removeprefix("%(root)s/")
        template = template.replace("%(", "{")
        template = template.replace(")s", "}")
        flat_raw.pop("version", None)
        if "rcm_name" in flat_raw:  # cordex special case
            institute = flat_raw["institute"]
            rcm_name = flat_raw["rcm_name"]
            rcm_model = institute + "-" + rcm_name
            flat_raw["rcm_model"] = rcm_model
        return template.format(version=version, **flat_raw)

    @classmethod
    def from_dict(cls, raw: dict) -> "File":
        dataset_id = find_str(raw["dataset_id"]).partition("|")[0]
        filename = find_str(raw["title"])
        url = find_str(raw["url"]).partition("|")[0]
        data_node = find_str(raw["data_node"])
        checksum = find_str(raw["checksum"])
        checksum_type = find_str(raw["checksum_type"])
        size = find_int(raw["size"])
        file_id = ".".join([dataset_id, filename])
        dataset_master = dataset_id.rsplit(".", 1)[0]  # remove version
        master_id = ".".join([dataset_master, filename])
        version = dataset_id.rsplit(".", 1)[1]
        local_path = cls.get_local_path(raw, version)

        return cls(
            file_id=file_id,
            url=url,
            filename=filename,
            dataset_id=dataset_id,
            master_id=master_id,
            version=version,
            local_path=local_path,
            data_node=data_node,
            checksum=checksum,
            checksum_type=checksum_type,
            size=size,
            raw=raw,
        )

    def clone(self) -> File:
        return File(
            file_id=self.file_id,
            dataset_id=self.dataset_id,
            master_id=self.master_id,
            url=self.url,
            version=self.version,
            filename=self.filename,
            local_path=self.local_path,
            data_node=self.data_node,
            checksum=self.checksum,
            checksum_type=self.checksum_type,
            size=self.size,
        )


class Param(Table):
    __tablename__ = "param"

    id: Mapped[int_pk] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(50))
    value: Mapped[str] = mapped_column(sa.String(255))
    last_updated: Mapped[datetime] = mapped_column(
        init=False,
        repr=False,
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


class Version(Table):
    __tablename__ = "version"

    version_num: Mapped[str_pk] = mapped_column(init=False)


__all__ = ["Table", "FileStatus", "File", "Param", "Version"]