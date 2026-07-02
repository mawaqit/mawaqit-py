"""Versioned API resources.

One subpackage per API version (``v2``, ``v3``), one module per resource, so a
new resource is just a new file. The version namespace classes (``AsyncV2`` /
``AsyncV3``) live in each subpackage's ``__init__``.
"""
