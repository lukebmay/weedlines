# -*- coding: utf-8 -*-
"""Mode lines clip to the inner piece border. No Inkscape."""
from __future__ import division

import math

import pytest

try:
    from weedlib.qt import QPainterPath, QRectF  # noqa: F401
except ImportError:
    pytest.skip('Qt cannot load', allow_module_level=True)

from weedlib import generate_weeds, piece_border, progress
from weedlib.solvers.geom import _iter_line_segs

_EPS = 1e-4


def _rect(x, y, width, height):
    path = QPainterPath()
    path.addRect(QRectF(x, y, width, height))
    return path


def _elements(path):
    items = []
    for index in range(path.elementCount()):
        element = path.elementAt(index)
        items.append((element.type, element.x, element.y))
    return items


def _segs(path):
    return [tuple(seg) for seg in _iter_line_segs(path)]


def _close_segs(got, expect):
    assert len(got) == len(expect)
    for left, right in zip(got, expect):
        assert len(left) == len(right)
        for a_value, b_value in zip(left, right):
            assert a_value == pytest.approx(b_value, abs=1e-9)


def _outside(x, y, rect):
    return (
        x < rect.left() - _EPS or x > rect.right() + _EPS
        or y < rect.top() - _EPS or y > rect.bottom() + _EPS)


def _on_boundary(x, y, rect):
    if x < rect.left() - _EPS or x > rect.right() + _EPS:
        return False
    if y < rect.top() - _EPS or y > rect.bottom() + _EPS:
        return False
    return (
        abs(x - rect.left()) <= _EPS or abs(x - rect.right()) <= _EPS
        or abs(y - rect.top()) <= _EPS or abs(y - rect.bottom()) <= _EPS)


def _strict_inside(x, y, rect):
    return (
        rect.left() + _EPS < x < rect.right() - _EPS
        and rect.top() + _EPS < y < rect.bottom() - _EPS)


def _samples(seg):
    return (
        (seg[0], seg[1]),
        (seg[2], seg[3]),
        (0.5 * (seg[0] + seg[2]), 0.5 * (seg[1] + seg[3])),
    )


def _assert_only_outer_outside(segs, inner, outer):
    inner_rect = inner.boundingRect()
    outer_rect = outer.boundingRect()
    for seg in segs:
        for x, y in _samples(seg):
            if _outside(x, y, inner_rect):
                assert _on_boundary(x, y, outer_rect), (x, y)


def _assert_path_pair(path, inner, outer):
    got = _elements(path)
    expect = _elements(inner) + _elements(outer)
    assert len(got) >= len(expect)
    for (got_type, got_x, got_y), (exp_type, exp_x, exp_y) in zip(
            got[-len(expect):], expect):
        assert got_type == exp_type
        assert got_x == pytest.approx(exp_x, abs=1e-9)
        assert got_y == pytest.approx(exp_y, abs=1e-9)


def _assert_published_pair(published, inner, outer):
    expect = _segs(inner) + _segs(outer)
    assert len(published) >= len(expect)
    _close_segs(published[-len(expect):], expect)


def _run(keep, **kwargs):
    published = []
    progress.install(geometry=lambda seg: published.append(tuple(seg)))
    try:
        weed = generate_weeds(keep, **kwargs)
    finally:
        progress.clear()
    return weed, published


def test_omitted_lengths_leave_todays_path():
    """No lengths, or only one, keeps the padded frame and its segments."""
    keep = _rect(0, 0, 40, 40)
    padding = [20, 20, 20, 20]
    plain, published = _run(keep, mode='frame', padding=padding)
    only_inner, inner_published = _run(
        keep, mode='frame', padding=padding, inner_distance=4)
    only_width, width_published = _run(
        keep, mode='frame', padding=padding, border_width=3)
    assert _elements(plain) == _elements(only_inner)
    assert _elements(plain) == _elements(only_width)
    assert published == _segs(plain)
    assert inner_published == published
    assert width_published == published
    # The full padded edge is published, not a shortened border clip.
    top = [
        seg for seg in published
        if abs(seg[1] + 20) < 1e-6 and abs(seg[3] + 20) < 1e-6]
    assert len(top) == 1
    assert abs(top[0][0] + 20) < 1e-6
    assert abs(top[0][2] - 60) < 1e-6


def test_one_length_does_not_call_piece_border(monkeypatch):
    calls = []
    real = piece_border

    def wrapped(subject, inner_distance, border_width):
        calls.append((inner_distance, border_width))
        return real(subject, inner_distance, border_width)

    monkeypatch.setattr(
        'weedlib.solvers.dispatch.piece_border', wrapped)
    keep = _rect(0, 0, 40, 40)
    generate_weeds(keep, mode='frame', padding=[2, 2, 2, 2])
    generate_weeds(
        keep, mode='grid', padding=[2, 2, 2, 2], spacing=10,
        inner_distance=4)
    generate_weeds(
        keep, mode='frame', padding=[2, 2, 2, 2], border_width=3)
    assert calls == []


def test_empty_keep_emits_nothing(monkeypatch):
    def wrapped(*args, **kwargs):
        raise AssertionError('piece_border was called')

    monkeypatch.setattr(
        'weedlib.solvers.dispatch.piece_border', wrapped)
    published = []
    progress.install(geometry=lambda seg: published.append(seg))
    try:
        empty = generate_weeds(
            QPainterPath(), mode='grid', padding=[4, 4, 4, 4],
            inner_distance=2, border_width=3)
        assert empty.isEmpty()
        assert generate_weeds(
            None, mode='frame', inner_distance=2, border_width=3).isEmpty()
    finally:
        progress.clear()
    assert published == []


def test_frame_and_grid_clip_and_emit_the_pair(monkeypatch):
    calls = []
    real = piece_border

    def wrapped(subject, inner_distance, border_width):
        calls.append((inner_distance, border_width))
        return real(subject, inner_distance, border_width)

    monkeypatch.setattr(
        'weedlib.solvers.dispatch.piece_border', wrapped)
    keep = _rect(0, 0, 40, 40)
    padding = [20, 20, 20, 20]
    inner, outer = piece_border(keep, 4, 3)
    for mode in ('frame', 'grid', 'region'):
        calls[:] = []
        plain, plain_published = _run(
            keep, mode=mode, padding=padding, spacing=10)
        weed, published = _run(
            keep, mode=mode, padding=padding, spacing=10,
            inner_distance=4, border_width=3)
        assert calls == [(4, 3)]
        assert plain.boundingRect().width() > outer.boundingRect().width() + 1
        assert weed.boundingRect().width() == pytest.approx(
            outer.boundingRect().width())
        assert weed.boundingRect().height() == pytest.approx(
            outer.boundingRect().height())
        _assert_path_pair(weed, inner, outer)
        _assert_published_pair(published, inner, outer)
        _assert_only_outer_outside(_segs(weed), inner, outer)
        _assert_only_outer_outside(published, inner, outer)
        # Plain still reaches the padded corner. The bordered run does not.
        assert any(
            abs(seg[0] + 20) < 1e-6 and abs(seg[1] + 20) < 1e-6
            for seg in plain_published)
        assert not any(
            abs(seg[0] + 20) < 1e-4 and abs(seg[1] + 20) < 1e-4
            for seg in published)
        border_n = len(_elements(inner)) + len(_elements(outer))
        if mode == 'frame':
            assert weed.elementCount() == border_n
        else:
            assert weed.elementCount() > border_n
            inner_rect = inner.boundingRect()
            mode_segs = _segs(weed)[:-(len(_segs(inner)) + len(_segs(outer)))]
            assert mode_segs
            assert any(
                (_on_boundary(seg[0], seg[1], inner_rect)
                 and _strict_inside(seg[2], seg[3], inner_rect))
                or (_on_boundary(seg[2], seg[3], inner_rect)
                    and _strict_inside(seg[0], seg[1], inner_rect))
                for seg in mode_segs)


def test_lines_inside_the_inner_rectangle_stay():
    keep = _rect(0, 0, 40, 40)
    padding = [2, 2, 2, 2]
    plain, _published = _run(keep, mode='frame', padding=padding)
    inner, outer = piece_border(keep, 10, 4)
    weed, published = _run(
        keep, mode='frame', padding=padding,
        inner_distance=10, border_width=4)
    plain_segs = _segs(plain)
    weed_segs = _segs(weed)
    _close_segs(weed_segs[:len(plain_segs)], plain_segs)
    _close_segs(weed_segs[len(plain_segs):], _segs(inner) + _segs(outer))
    _assert_path_pair(weed, inner, outer)
    _assert_published_pair(published, inner, outer)
    _assert_only_outer_outside(weed_segs, inner, outer)
    _assert_only_outer_outside(published, inner, outer)
    assert any(
        abs(seg[0] + 2) < 1e-6 and abs(seg[1] + 2) < 1e-6
        for seg in weed_segs)


def test_island_hop_still_runs():
    pytest.importorskip('pyclipper')
    keep = _rect(0, 0, 50, 50)
    inner, outer = piece_border(keep, 3, 2)
    weed, published = _run(
        keep, mode='island-hop', padding=[12, 12, 12, 12], spacing=20,
        inner_distance=3, border_width=2)
    assert not weed.isEmpty()
    _assert_path_pair(weed, inner, outer)
    _assert_published_pair(published, inner, outer)
    _assert_only_outer_outside(_segs(weed), inner, outer)
    _assert_only_outer_outside(published, inner, outer)


def _line_samples(path, limit=None):
    count = path.elementCount() if limit is None else limit
    line = QPainterPath.LineToElement
    move = QPainterPath.MoveToElement
    current = None
    samples = []
    for index in range(count):
        element = path.elementAt(index)
        if element.type == move:
            current = (element.x, element.y)
            continue
        if element.type != line or current is None:
            current = (element.x, element.y)
            continue
        end = (element.x, element.y)
        samples.append(current)
        samples.append((
            0.5 * (current[0] + end[0]),
            0.5 * (current[1] + end[1]),
        ))
        samples.append(end)
        current = end
    return samples


def _round_outside(x_coord, y_coord, rect, radius, eps=0.05):
    if (
        x_coord < rect.left() - eps or x_coord > rect.right() + eps
        or y_coord < rect.top() - eps or y_coord > rect.bottom() + eps
    ):
        return True
    boxes = (
        (rect.left() + radius, rect.top() + radius,
         rect.left(), rect.left() + radius,
         rect.top(), rect.top() + radius),
        (rect.right() - radius, rect.top() + radius,
         rect.right() - radius, rect.right(),
         rect.top(), rect.top() + radius),
        (rect.right() - radius, rect.bottom() - radius,
         rect.right() - radius, rect.right(),
         rect.bottom() - radius, rect.bottom()),
        (rect.left() + radius, rect.bottom() - radius,
         rect.left(), rect.left() + radius,
         rect.bottom() - radius, rect.bottom()),
    )
    for center_x, center_y, x0, x1, y0, y1 in boxes:
        if (
            x0 - eps <= x_coord <= x1 + eps
            and y0 - eps <= y_coord <= y1 + eps
            and math.hypot(
                x_coord - center_x, y_coord - center_y) > radius + eps
        ):
            return True
    return False


def _outline_dist(x_coord, y_coord, path):
    """Distance to lines and cubics, not to curve handles."""
    best = None
    move = QPainterPath.MoveToElement
    line = QPainterPath.LineToElement
    curve = QPainterPath.CurveToElement
    current = None
    index = 0
    count = path.elementCount()
    while index < count:
        element = path.elementAt(index)
        if element.type == move or element.type == line:
            end = (element.x, element.y)
            if element.type == line and current is not None:
                dist = _point_seg_dist(x_coord, y_coord, current, end)
                if best is None or dist < best:
                    best = dist
            current = end
            index += 1
            continue
        if element.type != curve or current is None:
            index += 1
            continue
        first = (element.x, element.y)
        second = (
            path.elementAt(index + 1).x, path.elementAt(index + 1).y)
        end = (path.elementAt(index + 2).x, path.elementAt(index + 2).y)
        previous = current
        for step in range(1, 17):
            t = step / 16.0
            point = _cubic_at(current, first, second, end, t)
            dist = _point_seg_dist(x_coord, y_coord, previous, point)
            if best is None or dist < best:
                best = dist
            previous = point
        current = end
        index += 3
    if best is None:
        return 1e9
    return best


def _cubic_at(start, first, second, end, t):
    u = 1.0 - t
    return (
        u * u * u * start[0] + 3 * u * u * t * first[0]
        + 3 * u * t * t * second[0] + t * t * t * end[0],
        u * u * u * start[1] + 3 * u * u * t * first[1]
        + 3 * u * t * t * second[1] + t * t * t * end[1],
    )


def _point_seg_dist(px, py, start, end):
    ax, ay = start
    bx, by = end
    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-18:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _poly_dist(x_coord, y_coord, path):
    best = None
    for polygon in path.toSubpathPolygons():
        points = [(point.x(), point.y()) for point in polygon]
        for index in range(len(points) - 1):
            ax, ay = points[index]
            bx, by = points[index + 1]
            dx = bx - ax
            dy = by - ay
            length_sq = dx * dx + dy * dy
            if length_sq <= 1e-18:
                dist = math.hypot(x_coord - ax, y_coord - ay)
            else:
                t = ((x_coord - ax) * dx + (y_coord - ay) * dy) / length_sq
                if t < 0.0:
                    t = 0.0
                elif t > 1.0:
                    t = 1.0
                dist = math.hypot(
                    x_coord - (ax + t * dx), y_coord - (ay + t * dy))
            if best is None or dist < best:
                best = dist
    if best is None:
        return 1e9
    return best


def _seg_dist(x_coord, y_coord, segments):
    best = None
    for seg in segments:
        ax, ay, bx, by = seg
        dx = bx - ax
        dy = by - ay
        length_sq = dx * dx + dy * dy
        if length_sq <= 1e-18:
            dist = math.hypot(x_coord - ax, y_coord - ay)
        else:
            t = ((x_coord - ax) * dx + (y_coord - ay) * dy) / length_sq
            if t < 0.0:
                t = 0.0
            elif t > 1.0:
                t = 1.0
            dist = math.hypot(
                x_coord - (ax + t * dx), y_coord - (ay + t * dy))
        if best is None or dist < best:
            best = dist
    if best is None:
        return 1e9
    return best


def _curve_mids(path):
    curve = QPainterPath.CurveToElement
    current = None
    mids = []
    index = 0
    count = path.elementCount()
    while index < count:
        element = path.elementAt(index)
        if element.isMoveTo() or element.type == QPainterPath.LineToElement:
            current = (element.x, element.y)
            index += 1
            continue
        if element.type != curve or current is None:
            index += 1
            continue
        first = (element.x, element.y)
        second = (
            path.elementAt(index + 1).x, path.elementAt(index + 1).y)
        end = (path.elementAt(index + 2).x, path.elementAt(index + 2).y)
        u = 0.5
        t = 0.5
        mids.append((
            u * u * u * current[0] + 3 * u * u * t * first[0]
            + 3 * u * t * t * second[0] + t * t * t * end[0],
            u * u * u * current[1] + 3 * u * u * t * first[1]
            + 3 * u * t * t * second[1] + t * t * t * end[1],
        ))
        current = end
        index += 3
    return mids


def _assert_round_cuts(weed, published, inner, outer, radius):
    rect = inner.boundingRect()
    _assert_path_pair(weed, inner, outer)
    border_n = inner.elementCount() + outer.elementCount()
    for x_coord, y_coord in _line_samples(
            weed, weed.elementCount() - border_n):
        assert not _round_outside(x_coord, y_coord, rect, radius), (
            x_coord, y_coord)
    for seg in published:
        for t in (0.0, 0.5, 1.0):
            x_coord = seg[0] + t * (seg[2] - seg[0])
            y_coord = seg[1] + t * (seg[3] - seg[1])
            on_border = (
                _outline_dist(x_coord, y_coord, inner) <= 0.05
                or _outline_dist(x_coord, y_coord, outer) <= 0.05
            )
            assert on_border or not _round_outside(
                x_coord, y_coord, rect, radius), (x_coord, y_coord)
    for x_coord, y_coord in _curve_mids(outer):
        assert _seg_dist(x_coord, y_coord, published) <= 0.05


def test_zero_corner_radius_leaves_the_square_clip():
    keep = _rect(0, 0, 40, 40)
    padding = [20, 20, 20, 20]
    plain, plain_published = _run(
        keep, mode='frame', padding=padding,
        inner_distance=4, border_width=3)
    zero, zero_published = _run(
        keep, mode='frame', padding=padding,
        inner_distance=4, border_width=3, corner_radius=0)
    assert _elements(plain) == _elements(zero)
    assert plain_published == zero_published


def test_rounded_frame_clips_the_corner_not_the_box():
    """The frame corner is inside the box and outside the arc."""
    keep = _rect(0, 0, 40, 40)
    padding = [2, 2, 2, 2]
    radius = 16
    plain, _plain_published = _run(
        keep, mode='frame', padding=padding,
        inner_distance=6, border_width=3)
    weed, published = _run(
        keep, mode='frame', padding=padding,
        inner_distance=6, border_width=3, corner_radius=radius)
    inner, outer = piece_border(keep, 6, 3, radius)
    assert _poly_dist(-2, -2, plain) < 1e-6
    assert _poly_dist(-2, -2, weed) > 0.5
    assert _poly_dist(20, -2, weed) < 1e-6
    _assert_round_cuts(weed, published, inner, outer, radius)


def test_grid_stays_inside_the_rounded_border():
    keep = _rect(0, 0, 40, 40)
    radius = 16
    inner, outer = piece_border(keep, 6, 3, radius)
    weed, published = _run(
        keep, mode='grid', padding=[2, 2, 2, 2], spacing=10,
        inner_distance=6, border_width=3, corner_radius=radius)
    assert weed.elementCount() > inner.elementCount() + outer.elementCount()
    _assert_round_cuts(weed, published, inner, outer, radius)


def test_island_hop_stays_inside_the_rounded_border():
    pytest.importorskip('pyclipper')
    keep = _rect(0, 0, 50, 50)
    radius = 8
    inner, outer = piece_border(keep, 3, 2, radius)
    weed, published = _run(
        keep, mode='island-hop', padding=[12, 12, 12, 12], spacing=20,
        inner_distance=3, border_width=2, corner_radius=radius)
    assert weed.elementCount() > inner.elementCount() + outer.elementCount()
    _assert_round_cuts(weed, published, inner, outer, radius)


def test_border_clip_does_not_stick():
    keep = _rect(0, 0, 40, 40)
    padding = [20, 20, 20, 20]
    _run(
        keep, mode='frame', padding=padding,
        inner_distance=4, border_width=3)
    _plain, published = _run(keep, mode='frame', padding=padding)
    top = [
        seg for seg in published
        if abs(seg[1] + 20) < 1e-6 and abs(seg[3] + 20) < 1e-6]
    assert len(top) == 1
    assert abs(top[0][0] + 20) < 1e-6
    assert abs(top[0][2] - 60) < 1e-6
