"""Render and composite Nikke trading cards.

Walks :mod:`cards` for card definitions (``*.json``), renders each one with
the ``nikke-viewer`` executable, composites every rendered frame on top of
the card's ``background``, stamps the matching logo from ``assets/images/``
at the bottom right and the copyright line at the bottom left, and overlays
the card name on top of the art, per frame: the title (uppercase, in a
dark rectangle at three-quarters of the height, with a small slanted bar
and three slanted squares of the same fill above it) and the subtitle
above the title (uppercase, in a background-tinted rectangle). The
``Goddess`` and ``Classified`` variants are generated without any card
name. Packs (``cards/`` subdirectories carrying an
``Expansion.json``) additionally get their two artwork images, built from
the templates in ``assets/images/``. The pack's front and back are composed
on the fly (by :mod:`nikke_reborn.pack`) from the expansion's metadata —
the front is its ``background`` with its featured NIKKES (``pack``) drawn
over it and its ``logo`` when the expansion names one; the back is the
same ``background`` resized and left-cropped — and neither is stored. The
material (``CardPack_Material.png``) has two pure-blue mask rectangles
holding the composed back (left) and front (right); the item
(``CardPack_Item.png``) is the pack's mesh
(``assets/meshes/CardPackStatic_Mesh.obj``) textured with the finished
material and rendered by the ``unity-viewer`` executable with the
model rotation and camera zoom/pan from
``assets/meshes/CardPackStatic_Mesh.json`` — so it is generated after the
material, which it reads from disk. The box (``CardBox_Material.png``)
holds the same composed front in the blue rectangle of its three mask
rectangles (blue front, red top, green side), the top (a center-cropped
background with the expansion's logo and the white NIKKE logo) in the red
one and the side (the background with the expansion's logo and the white
NIKKE logo) in the green one; the box's item (``CardBox_Item.png``) is the
box's mesh (``assets/meshes/CardBox_Mesh.obj``) textured with the finished
material and rendered by the ``unity-viewer`` executable with the model
rotation and camera zoom/pan from ``assets/meshes/CardBox_Mesh.json``, so it
is generated after the box's material, which it reads from disk. The
finished results are written under ``output/``, with
the SHA-256 of their inputs embedded as metadata (a PNG text chunk, an
MP4 tag); a result whose stored hash matches the current inputs is
skipped instead of re-rendered.

* single-frame cards -> ``output/<set>/<card>_<variant>.png``
* animated cards     -> ``output/<set>/<card>_<variant>.mp4`` alongside
                       its first frame, ``output/<set>/<card>_<variant>.png``
                       (with ``--no-video``: the first frame alone)

(the card's directory is folded into the filename, so a set's cards
sit flat in ``output/<set>/``)

``--draft`` runs the same pipeline for quick iteration: ultrafast x264
preset, half-resolution MP4s (downscaled inside ffmpeg), and results
written to ``draft/`` instead of ``output/`` so draft runs never clobber
the final cards.

``--no-video`` skips the MP4 generation altogether: an animated card is
written out as its first frame alone (the same PNG an animation keeps
alongside its MP4), the viewer stream is abandoned after that frame and
the viewer reaped, and the run never invokes ffmpeg or ffprobe — the
fastest pass through the pipeline, for iterating on the frames themselves.
The up-to-date check then covers the first frame alone; a run without the
flag generates the MP4 as usual whenever it is missing or stale.

``--no-profile``, ``--no-standard`` and ``--no-full-art`` disable the
three generation passes outright — the ``Profile`` presentation (the
``<variant>Profile`` cards), the ``Standard`` presentation (the
``<variant>Standard`` cards) and the full-art cards with the pack's
artwork (the pack's and the box's materials and items) — so a run renders
only the presentations it is not told to skip. The metadata bundle is
written either way, and a later run without the flag renders the skipped
outputs whenever they are missing or stale.

``--force`` skips the up-to-date (hash) check and re-renders every selected
card, profile card, standard card and pack image, even when the finished
result on disk is already current.

``nikke-viewer --stdout`` streams its frames as raw RGBA pixels (no
intermediate files), so each card is rendered straight into the pipeline:
the raw frames are piped out of the viewer's stdout, composited in memory,
and — for animations — fed to the ffmpeg encode through a pipe. Nothing
intermediate ever touches the disk; only the finished card is written
(atomically).

Cards are independent of each other, so they are processed by a pool of
worker processes (see ``--jobs``); within an animated card, the frames are
composited in parallel threads, and the cores are split between that stage
and the ffmpeg encode so the parallel work stays within the core count.

The full-art card keeps the definition's own pan/zoom, except the ``fb``
variant, which the viewer frames with the ``--half-body`` flag (the upper
body, head to waist).

Beyond the full-art card, two derived presentations are rendered from a
definition: the ``Profile`` presentation (the ``Classic``, ``Idle``,
``Cover`` and ``Aim`` variants, written out with a ``Profile`` suffix; see
the profile presentation section below) and the ``Standard`` presentation
(the ``Classic``, ``Rare``, ``Special`` and ``Exotic`` variants, written out
with a ``Standard`` suffix; the standard card keeps the definition's
``background`` (faded a bit toward its dominant color), composites the
standard card mask over it, and frames the character's upper body with the
viewer's ``--half-body`` flag).

By default every ``*.json`` under ``cards/`` is generated; one or more card
paths (a set, a card, or a definition file, relative to the repo root or to
``cards/``) may be passed on the command line to generate only the selected
definitions — the full-art, the ``Profile`` and the ``Standard``
presentations alike.
"""
