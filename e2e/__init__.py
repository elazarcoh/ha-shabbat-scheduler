"""Makes `e2e` a package, which is load-bearing for collection.

`pyproject.toml` now has `testpaths = ["tests", "e2e"]`, so both
directories are collected in one run. Under pytest's default `prepend`
import mode, a test directory WITHOUT an `__init__.py` gets inserted onto
`sys.path` itself and its `conftest.py` becomes importable as the
top-level module `conftest`. Two such directories both offering a
`conftest` is a collision, and `tests/test_websocket.py` does
`from conftest import ZMANIM` - which silently resolved to
`e2e/conftest.py` and failed collection for the whole run with
`ImportError: cannot import name 'ZMANIM'`.

With this file present, pytest walks up past it, puts the ROOT on
`sys.path` instead, and imports these modules as `e2e.conftest` /
`e2e.test_card_e2e`. `tests/` keeps no `__init__.py`, so `conftest` still
means `tests/conftest.py` for the module that asks for it by that name.

Do not delete this to tidy up. Deleting it breaks the whole Python suite,
not just e2e.
"""
