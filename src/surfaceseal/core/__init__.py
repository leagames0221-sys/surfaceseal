"""Domain-agnostic core: contracts shared by every detection pack.

The core knows nothing about specific agent file formats or rules. Packs
(``surfaceseal.packs.*``) depend on the core; the core never imports a pack.
"""
