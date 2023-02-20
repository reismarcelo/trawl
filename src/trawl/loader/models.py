from typing import List, Dict, Pattern, Optional, Set
from enum import Enum
from ipaddress import IPv4Address
from pydantic import BaseModel, constr, Extra, validator, Field


_available_devices: Set[str] = set()


class DeviceTypeOptions(str, Enum):
    cisco_xr_telnet = 'cisco_xr_telnet'
    cisco_xr = 'cisco_xr'


class DeviceConfigModel(BaseModel, extra=Extra.forbid, use_enum_values=True):
    address: IPv4Address
    device_type: DeviceTypeOptions = DeviceTypeOptions.cisco_xr


class CommandModel(BaseModel, extra=Extra.forbid):
    send: constr(strip_whitespace=True, min_length=1)
    prompt_pattern: Optional[Pattern] = None
    find: Optional[Pattern] = None
    timeout: float = 30


class DownloadModel(BaseModel, extra=Extra.forbid):
    devices: Optional[List[str]] = None
    directory: Optional[str] = None
    file_pattern: Optional[Pattern] = None
    timeout: float = 30

    @validator('devices')
    def devices_validator(cls, v: List[str]) -> List[str]:
        diff = set(v) - _available_devices
        if diff:
            raise ValueError(f"These devices are not defined: {', '.join(diff)}")

        return v


#
# Top-level ConfigModel
#

class ConfigModel(BaseModel, extra=Extra.forbid):
    devices: Dict[str, DeviceConfigModel]
    commands: List[CommandModel]
    downloads: List[DownloadModel] = Field(default_factory=list)

    @validator('devices')
    def devices_cache(cls, v: Dict[str, DeviceConfigModel]) -> Dict[str, DeviceConfigModel]:
        _available_devices.update(v)
        return v
