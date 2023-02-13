import logging
import logging.config
import logging.handlers
from pathlib import Path
from typing import Any
from .loader import load_metadata


METADATA_CONFIG = """
---
loader_config:
  spec_file: "trawl_spec.yml"

logging_config:
  version: 1
  formatters:
    simple:
      format: "%(levelname)s: %(message)s"
    detailed:
      format: "%(asctime)s: %(name)s: %(levelname)s: %(message)s"
  handlers:
    console:
      class: "logging.StreamHandler"
      level: "INFO"
      formatter: "simple"
  root:
    handlers:
      - "console"
    level: "DEBUG"
...
"""


def setup_logging(logging_config: dict[str, Any]) -> None:
    file_handler = logging_config.get("handlers", {}).get("file")
    if file_handler is not None:
        Path(file_handler["filename"]).parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(logging_config)


app_config = load_metadata(METADATA_CONFIG)
setup_logging(app_config.logging_config)
