"""Render and composite Nikke trading cards.

One TOML per expansion (``cards/<set>.toml``) is the pipeline's single
input: its characters (the ``cards`` list of viewer ids, in order — the
card's number is its position, its stem its zero-padded number plus the
compact name from the game's data, ``characters.json`` and
``models.json``), its pack's featured characters (``pack``), its
backgrounds (the ``background`` table: the ``base``, the ``special`` and
the ``battle``) and its logo (``logo.path`` and ``logo.placement``,
relative to the expansion's folder).

Every character renders the same fixed set of presentations (the tiers
below). Each is composited in memory over its background — fitted to the
card's viewport and masked by its tier's mask (the standard's or the
profile's; the full-art presentations unmasked). The standard's background
is autocontrasted and faded a bit toward its dominant color; the full-art's
is left as-is (no contrast adjustment, no fade); the profile's is
flattened to a monochrome of its dominant tint. Every
card is stamped with the NIKKE logo (the white one on the full-art cards,
the black one on the standard and profile cards) and the copyright line at
the bottom left. The standard and profile cards additionally carry the card
name over the art — the title (uppercase, in a dark rectangle at
three-quarters of the height, with a small slanted bar and three slanted
squares of the same fill above it) and the subtitle above the title
(uppercase, in a background-tinted rectangle) — and the character's
manufacturer's logo above the name's bar; the full-art cards carry no name.
The ``Goddess`` presentation is rendered without any card name and is
skipped for the characters that carry no ``sc`` variant, and the two
``Special`` presentations are skipped for the characters that carry no reel
animation:

* the standard tier — the ``ClassicStandard`` (the classic pose),
  ``SpecialStandard`` (the character's special animation, the reel's pick)
  and ``ExoticStandard`` (the ``action`` animation, looped) presentations,
  half-body frames on the standard's mask, on the ``base`` and ``special``
  backgrounds;
* the profile tier — the ``ClassicProfile`` (the classic pose),
  ``IdleProfile`` (the ``idle`` animation, looped), ``CoverProfile`` and
  ``AimProfile`` (the ``cover`` and ``aim`` variants) presentations: the
  character's full body on the profile's mask, rendered in two
  locked-together streams (the face's stream at the viewer's ``--face``
  framing plus the body's at the default framing), on the ``base`` and
  ``battle`` backgrounds;
* the full-art tier — the ``Classic``, ``Idle``, ``Cover``, ``Aim``,
  ``Special`` and ``Exotic`` presentations (the classic pose, the
  ``idle`` loop, the ``cover`` and ``aim`` variants, the special animation
  and the ``action`` loop) and the ``Goddess`` presentation (the ``sc``
  variant, its ``main`` animation): the classic, idle, special and exotic
  are half-body frames and
  the cover, aim and goddess are full-body, no mask, each on its own
  background (the ``base``, ``battle`` or ``special`` — a solid black for
  the goddess) fitted to the card's own aspect and left as-is (no fade, no
  contrast adjustment).

The profile's presentations are rendered in two locked-together streams —
the face's stream (the viewer's ``--face`` framing, shifted aside from the
body) and the body's stream (the viewer's default framing) — and every
profile card carries a photo reel down its right edge: the first
`PROFILE_REEL_COUNT` (three) of the character's animations in the order of
`PROFILE_REEL_ANIMATIONS`, each rendered as a face still (the viewer's
`--portrait` framing at `--time 0`, on a white background, framed by a
border of the card's dominant tint).

The expansion's pack and box get their artwork images, built from the
templates in ``assets/images/``. The pack's front and back are composed on
the fly (by :mod:`nikke_reborn.pack`) from the expansion's data — the
front is its ``base`` background with its featured NIKKES (``pack``) drawn
over it (the hero centered on top, the rest in tiers behind) and its
expansion's logo (its ``logo.path``, with a glow tinted by the scene) at
its ``logo.placement``; the back is the same background resized and
left-cropped — and neither is stored. The material
(``CardPack_Material.png``) has two pure-blue mask rectangles holding the
composed back (left) and front (right); the item (``CardPack_Item.png``) is
the pack's mesh (``assets/meshes/CardPackStatic_Mesh.obj``) textured with
the finished material and rendered by the ``unity-viewer`` executable with
the model rotation and camera zoom/pan from
``assets/meshes/CardPackStatic_Mesh.json`` — so it is generated after the
material, which it reads from disk. The box (``CardBox_Material.png``)
holds the same composed front (its background fit, logo sizing and
character sizing are the box's own) in the blue rectangle of its three
mask rectangles (blue front, red top, green side), the top (a
center-cropped background with the expansion's logo and the white NIKKE
logo) in the red one and the side (the background with the expansion's
logo and the white NIKKE logo) in the green one; the box's item
(``CardBox_Item.png``) is the box's mesh
(``assets/meshes/CardBox_Mesh.obj``) textured with the finished material
and rendered by the ``unity-viewer`` executable with the model rotation
and camera zoom/pan from ``assets/meshes/CardBox_Mesh.json``, so it is
generated after the box's material, which it reads from disk.

The finished results are written under ``output/<set>/`` (half resolution
by default — the ``--ultra`` preset renders at the native resolution into
the ``<set> (Ultra)`` set folders), with the SHA-256 of their inputs
embedded as metadata (a PNG text chunk, an MP4 tag); a result whose stored
hash matches the current inputs is skipped instead of re-rendered:

* still cards -> ``output/<set>/<card>_<presentation>.png``
* animated cards -> ``output/<set>/<card>_<presentation>.mp4`` alongside
                       its first frame, ``output/<set>/<card>_<presentation>.png``
                       (with ``--no-video``: the first frame alone)

(the card's stem is folded into the filename, so a set's cards sit flat in
``output/<set>/``)

``--draft`` runs the same pipeline for quick iteration at the default's
half resolution (the whole pipeline — the viewer, the compositing and the
encode — runs at that size) with an ultrafast x264 preset, and results
written to ``draft/`` instead of ``output/`` so draft runs never clobber
the final cards.

``--no-video`` skips the MP4 generation altogether: an animated card is
written out as its first frame alone (the same PNG an animation keeps
alongside its MP4), the viewer stream is abandoned after that frame and
the viewer reaped, and the run never invokes ffmpeg or ffprobe — the
fastest pass through the pipeline, for iterating on the frames themselves.
The up-to-date check then covers the first frame alone; a run without the
flag generates the MP4 as usual whenever it is missing or stale.

``--no-standard``, ``--no-profile`` and ``--no-full-art`` disable the
three generation passes outright — the standard's, the profile's and the
full-art's presentations, with the pack's and the box's artwork (the pack's
and the box's materials and items) — so a run renders only the tiers it is
not told to skip. The metadata bundle is written either way, and a later
run without the flag renders the skipped outputs whenever they are missing
or stale.

``--force`` skips the up-to-date (hash) check and re-renders every
selected presentation, tier and pack image, even when the finished result
on disk is already current.

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

The half-body presentations (the standard's, and the full-art's classic,
idle, special and exotic) are framed with the viewer's ``--half-body`` flag
(the upper body, head to waist); the profile's, and the full-art's cover,
aim and goddess presentations, keep the character's full body.

By default every expansion under ``cards/`` is generated; one or more
expansion paths (a ``cards/<set>.toml``, ``<set>.toml`` or ``<set>``) may
be passed on the command line to generate only the selected expansions,
and ``--ids`` restricts a run to the named characters (their viewer ids)
of the selected expansions.
"""
