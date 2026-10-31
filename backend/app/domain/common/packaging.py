import re
from typing import Dict, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Platform = Literal["x86", "692", "530", "3403svp", "3403nnn", "rk3588"]


class ProjectPackagingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_links: Dict[Platform, str] = Field(default_factory=dict)
    cfg_link: str = Field(default="", max_length=255)
    names_link: str = Field(default="", max_length=255)
    cfg_filename: str = "model.cfg"
    cfg_content: str = Field(default="", max_length=1048576)
    names_filename: str = "obj.names"
    names_content: str = Field(default="", max_length=1048576)

    @model_validator(mode="before")
    @classmethod
    def remove_legacy_package_key(cls, value):
        if isinstance(value, dict):
            value = dict(value)
            value.pop("package_key", None)
        return value

    @model_validator(mode="after")
    def validate_packaging(self):
        def filename(value, suffix=None, optional=False):
            value = value.strip()
            if not value and optional:
                return value
            if not value or value in {".", ".."} or re.search(r'[\\/:*?"<>|\s\x00-\x1f]', value) or len(value) > 255:
                raise ValueError("文件及链接名称必须是有效的单个文件名，不能包含路径或空白")
            if suffix and not value.endswith(suffix):
                raise ValueError("文件或链接名称须以 %s 结尾" % suffix)
            return value
        self.cfg_link = filename(self.cfg_link, ".cfg", True)
        self.names_link = filename(self.names_link, ".names", True)
        self.cfg_filename = filename(self.cfg_filename, ".cfg")
        self.names_filename = filename(self.names_filename, ".names")
        self.model_links = {platform: filename(value, optional=True) for platform, value in self.model_links.items()}
        self.model_links = {platform: value for platform, value in self.model_links.items() if value}
        stems = set()
        for platform, value in self.model_links.items():
            suffix = ".bin" if platform in {"692", "530"} else ".weights"
            if not value.endswith(suffix):
                raise ValueError("%s 模型软链接须以 %s 结尾" % (platform, suffix))
            stems.add(value[:-len(suffix)])
        if len(stems) > 1:
            raise ValueError("各平台模型软链接须使用相同主名称")
        if stems:
            stem = stems.pop()
            if not stem or stem.endswith((".bin", ".weights")):
                raise ValueError("模型软链接主名称不能为空或包含重复后缀")
            self.model_links = {platform: stem + (".bin" if platform in {"692", "530"} else ".weights")
                                for platform in ("x86", "692", "530", "3403svp", "3403nnn", "rk3588")}
        self.cfg_content = self.cfg_content.replace("\r\n", "\n").replace("\r", "\n")
        self.names_content = self.names_content.replace("\r\n", "\n").replace("\r", "\n")
        return self


