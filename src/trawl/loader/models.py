from typing import List, Dict, Pattern, Optional
from enum import Enum
from ipaddress import IPv4Address
from pydantic import BaseModel, constr


class DeviceTypeOptions(str, Enum):
    cisco_xr_telnet = 'cisco_xr_telnet'
    cisco_xr = 'cisco_xr'


class DeviceConfigModel(BaseModel):
    address: IPv4Address
    device_type: DeviceTypeOptions = DeviceTypeOptions.cisco_xr

    class Config:
        use_enum_values = True


class CommandModel(BaseModel):
    cmd: constr(strip_whitespace=True, min_length=2)
    find: Optional[Pattern] = None


#
# Top-level ConfigModel
#

class ConfigModel(BaseModel):
    devices: Dict[str, DeviceConfigModel]
    commands: List[CommandModel]
