# surround

- `__init__.py` re-exports `build_surrounds` and `_bridge_clears`.
- `build.py` dilates, clusters, bridges, and smooths, in today's order.
- `bridge.py` builds one inner bridge and tests its clearance.
- `union.py` unions surrounds that meet.
- `offset.py` dilates and returns the outer loops.
- `smooth.py` fillets out to the surround distance.
