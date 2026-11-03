"""Render and composite Nikke trading cards.

One TOML per expansion (``cards/<set>.toml``) is the pipeline's single
input: its characters (the ``cards`` list of viewer ids, in order —
the card's number is its position, its stem its zero-padded number
plus the compact name from the game's data), its pack's featured
characters (``pack``), its backgrounds (the ``background`` table) and
its logo (``logo.path`` and ``logo.placement``, relative to the
expansion's folder).

Every character renders the expansion's ``rarities`` subset of the
fixed set of presentations (:data:`nikke_reborn.expansion.PRESENTATION_SPECS`
describes the tiers, their masks and their viewer terms), each
composited in memory over its background and stamped with the NIKKE
logo and the copyright line; the standard and profile cards carry the
card name over the art (:mod:`nikke_reborn.lettering`). The expansion's
pack and box get their artwork images, built from the templates in
``assets/images/`` (:mod:`nikke_reborn.pack`, :mod:`nikke_reborn.box`);
the materials' items are rendered by ``unity-viewer`` from the
finished materials, so they are generated after them.

The finished results are written under ``output/<set>/`` (half
resolution by default — the ``--ultra`` preset renders at the native
resolution into the ``<set> (Ultra)`` set folders; ``--draft`` runs the
whole pipeline at half resolution into ``draft/``), with the SHA-256 of
their inputs embedded as metadata: a result whose stored hash matches
the current inputs is skipped instead of re-rendered. ``--force``
skips the up-to-date check; ``--no-video`` skips the MP4 generation
(see :mod:`nikke_reborn.video`); ``--no-standard``, ``--no-profile``
and ``--no-full-art`` disable the three generation passes.

The pipeline streams the viewer's raw frames in memory — nothing
intermediate ever touches the disk; only the finished card is written
(atomically). Cards are independent of each other, so they are
processed by a pool of worker processes (:mod:`nikke_reborn.generate`);
within an animated card, the frames are composited in parallel threads.

By default every expansion under ``cards/`` is generated; one or more
expansion paths may be passed on the command line to generate only the
selected expansions, and ``--ids`` restricts a run to the named
characters of the selected expansions.
"""
