from __future__ import annotations

from collections.abc import Callable
import sys
from typing import Any

def _identity_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
    return func


def _get_streamlit_module():
    return sys.modules.get("streamlit")


def cache_data(*args: Any, **kwargs: Any):
    st = _get_streamlit_module()
    if st is None:
        return _identity_decorator
    return st.cache_data(*args, **kwargs)


def cache_resource(*args: Any, **kwargs: Any):
    st = _get_streamlit_module()
    if st is None:
        return _identity_decorator
    return st.cache_resource(*args, **kwargs)
