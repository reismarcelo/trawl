import os
import sys
import yaml
from typing import Any, TypeVar, Type, Union
from pydantic import BaseModel, ValidationError
from .models import ConfigModel, StateModel


class LoaderException(Exception):
    """ Exception indicating loader errors """
    pass


M = TypeVar('M', bound=BaseModel)


def load_yaml(model_cls: Type[M], description: str, filename: Union[os.PathLike, str]) -> M:
    try:
        with open(filename) as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)

        return model_cls(**yaml_dict)

    except FileNotFoundError as ex:
        raise LoaderException(f"Could not open {description} file: {ex}") from None
    except yaml.YAMLError as ex:
        raise LoaderException(f'YAML syntax error in {description} file: {ex}') from None
    except ValidationError as ex:
        raise LoaderException(f"Invalid {description} file: {ex}") from None


class LoaderConfigModel(BaseModel):
    spec_file: str
    state_file: str


class MetadataModel(BaseModel):
    loader_config: LoaderConfigModel
    logging_config: dict[str, Any]


def load_metadata(metadata: str) -> MetadataModel:
    try:
        yaml_dict = yaml.safe_load(metadata)
        return MetadataModel(**yaml_dict)
    except (yaml.YAMLError, ValidationError) as ex:
        print(ex)

    sys.exit(1)
