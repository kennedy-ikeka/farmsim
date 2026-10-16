from typing import Any
import numpy as np

def get_param(params: dict[int, Any], value: float) -> Any:
    keys = sorted(params.keys(), reverse=True)

    for k in keys:
        if k < value:
            return params[k]

    return params[keys[0]]