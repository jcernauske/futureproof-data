"""Surface adapters. Each adapter knows how to replay one Gemma surface with
golden inputs. Adapters import production code directly and call it the same
way the running app would, so we measure the real prompt + the real client
path, not a stub."""

from eval.adapters.base import AdapterResult, SurfaceAdapter

__all__ = ["AdapterResult", "SurfaceAdapter"]
