import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, NamedTuple, Tuple

from point import Point as P

logger = logging.getLogger(__name__)


class Align(str, Enum):
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"
    RIGHT = "right"
    LEFT = "left"


class Anchor(str, Enum):
    TOP_LEFT = "la"
    TOP_MIDDLE = "ma"
    TOP_RIGHT = "ra"

    MIDDLE_LEFT = "lm"
    MIDDLE_MIDDLE = "mm"
    MIDDLE_RIGHT = "rm"

    BOTTOM_LEFT = "ld"
    BOTTOM_MIDDLE = "md"
    BOTTOM_RIGHT = "rd"


class Style(NamedTuple):
    padding: int = 10
    font: str = 'Roboto-Regular.ttf'
    font_size: int = 32
    anchor: Anchor = Anchor.TOP_LEFT
    stroke_color: str = "black"
    fill_color: str = "white"
    font_color: str = "black"


default_style = Style()


def set_style(style):
    global default_style
    default_style = style
    logger.debug('Default style: %s', repr(style))


class Renderer(ABC):
    @abstractmethod
    def rectangle(self, p1, p2, style: Style):
        raise NotImplementedError()

    @abstractmethod
    def text(self, text: str, p, style: Style):
        raise NotImplementedError()

    @abstractmethod
    def text_bbox(self, text: str, style: Style) -> Tuple[int, int, int, int]:
        raise NotImplementedError()

    @abstractmethod
    def line(self, p1, p2, style: Style):
        raise NotImplementedError()

    @abstractmethod
    def set_dimensions(self, dim):
        raise NotImplementedError()


class Object:
    def __init__(self, width=None, height=None, style=None, **kwargs):
        if not style:
            style = default_style

        if kwargs:
            style = style._replace(**kwargs)
        self.style = style
        self._w = width
        self._h = height
        self.children: List[Tuple[Object, P]] = []
        self.parent = None

    @property
    def width(self) -> int:
        assert self._w is not None
        return self._w

    @width.setter
    def width(self, val):
        self._w = val

    @property
    def height(self) -> int:
        assert self._h is not None
        return self._h

    @height.setter
    def height(self, val):
        self._h = val

    def add(self, obj, pos=P(0, 0)):
        self.children.append((obj, pos))
        obj.parent = self

    def prepare(self, renderer: Renderer):
        for (obj, _) in self.children:
            obj.prepare(renderer)

    def render(self, renderer: Renderer, pos=(0, 0)):
        x, y = pos
        for (obj, offset) in self.children:
            logger.debug('%s %s', obj, offset)
            offx, offy = offset
            obj.render(renderer, P(x + offx, y + offy))

    def __str__(self):
        return f"{type(self).__name__}({self._w}, {self._h})"


class VLayout(Object):
    def __init__(self, align=Align.CENTER, **kwargs):
        super().__init__(**kwargs)
        self.align = align

    @property
    def width(self) -> int:
        self._w = 0
        for (obj, offset) in self.children:
            offx, _ = offset
            self._w = max(self._w, obj.width + offx)

        return self._w

    @width.setter
    def width(self, val):
        self._w = val

    @property
    def height(self) -> int:
        self._h = 0
        for (obj, offset) in self.children:
            _, offy = offset
            self._h += obj.height + offy

        return self._h

    @height.setter
    def height(self, val):
        self._h = val

    def render(self, renderer: Renderer, pos=(0, 0)):
        logger.debug('%s %s', self, pos)
        x, y = pos
        # TODO: implement the centering logic better
        # TODO: if align == Align.CENTER:
        centerx = x + (self.width // 2)
        logger.debug('center: %s', centerx)
        for (obj, offset) in self.children:
            logger.debug('%s %s', obj, offset)
            offx, offy = offset

            obj_posx = x + offx
            obj_centerx = obj_posx + (obj.width // 2)
            obj.render(renderer, P(obj_posx + centerx - obj_centerx, y + offy))
            y += obj.height + offy


class HLayout(Object):
    def __init__(self, align=Align.CENTER, **kwargs):
        super().__init__(**kwargs)
        self.align = align

    @property
    def width(self) -> int:

        self._w = 0
        for (obj, offset) in self.children:
            offx, _ = offset
            self._w += obj.width + offx

        return self._w

    @width.setter
    def width(self, val):
        self._w = val

    @property
    def height(self) -> int:
        self._h = 0
        for (obj, offset) in self.children:
            _, offy = offset
            self._h = max(self._h, obj.height + offy)

        return self._h

    @height.setter
    def height(self, val):
        self._h = val

    def render(self, renderer: Renderer, pos=P(0, 0)):
        x, y = pos
        for (obj, offset) in self.children:
            logger.debug('%s %s', obj, offset)
            offx, offy = offset
            obj.render(renderer, P(x + offx, y + offy))
            x += obj.width + offx


# TODO: width and height are actually one pixel larger than requested
class Rectangle(Object):
    def render(self, renderer: Renderer, pos=P(0, 0)):
        x, y = pos
        renderer.rectangle((x, y), (x + self._w, y + self._h), self.style)
        super().render(renderer, pos)


class Line(Object):
    # TODO: Support polar coordinates
    def __init__(self, *, end, start=P(0, 0), **kwargs):
        width = max(start.x, end.x)
        height = max(start.y, end.y)
        super().__init__(width=width, height=height, **kwargs)

        self.start = start
        self.end = end

    def render(self, renderer: Renderer, pos=(0, 0)):
        renderer.line(self.start + pos, self.end + pos, self.style)


# class Grid(Object):
#     def prepare(self, renderer: Renderer):
#         self._w = self._w or renderer._w
#         self._h = self._h or renderer._h

#     def render(self, renderer: Renderer, pos=P(0, 0)):
#         pos = P(pos)
#         for i in range(0, renderer._w, 100):
#             renderer.line((i + pos.x, pos.y), (i + pos.x, self._h), self.style)


class TextBox(Rectangle):
    def __init__(self, text, align=Anchor.MIDDLE_MIDDLE, **kwargs):
        super().__init__(**kwargs)

        pos = (0, 0)
        style = self.style
        if align == Anchor.MIDDLE_MIDDLE:
            style = self.style._replace(anchor=Anchor.MIDDLE_MIDDLE)
            pos = (self.width // 2, self.height // 2)

        self.add(
            Text(text, style=style, width=self.width, height=self.height), pos
        )

    @property
    def width(self) -> int:
        assert self._w is not None
        return self._w

    @width.setter
    def width(self, val):
        self._w = val

    @property
    def height(self) -> int:
        assert self._h is not None
        return self._h

    @height.setter
    def height(self, val):
        self._h = val

        # Recenter text
        t, _ = self.children[0]
        self.children[0] = (t, P(self.width // 2, self.height // 2))

    # def prepare(self, renderer: Renderer):
    #     super().prepare(renderer)
    # if self.fit_height:
    #     t, _ = self.children[0]
    #     self.height = t.height

    def render(self, renderer: Renderer, pos=P(0, 0)):
        super().render(renderer, pos)


class Table(HLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def prepare(self, renderer: Renderer):
        super().prepare(renderer)
        self._h = 0
        for (obj, _) in self.children:
            self._h = max(self._h, obj.height)

        # Set all cells to the same height
        for (obj, _) in self.children:
            obj.height = self._h


class DottedLine(Line):
    def __init__(self, dash_len=10, **kwargs):
        super().__init__(**kwargs)
        self.dash_len = dash_len

    def render(self, renderer: Renderer, pos=P(0, 0)):
        length = (
            (self.end.x - self.start.x)**2 + (self.end.y - self.start.y)**2
        )**0.5

        if self.end.x != self.start.x:
            u = (self.end - self.start) / length
        else:
            u = P(0, 1)

        xy1 = self.start + pos
        for _ in range(0, int(length), self.dash_len):
            xy2 = xy1 + (u * (self.dash_len // 2))
            renderer.line(xy1, xy2, self.style)
            xy1 = xy1 + u * self.dash_len


class Arrow(Line):
    def __init__(self, double_sided=False, arrow_length=10, **kwargs):
        super().__init__(**kwargs)
        self.double_sided = double_sided
        self.alen = arrow_length

    def render(self, renderer: Renderer, pos=P(0, 0)):
        renderer.line(self.start + pos, self.end + pos, self.style)

        renderer.line(pos + self.end, pos + self.end - self.alen, self.style)
        renderer.line(
            pos + self.end, pos + self.end + P(-self.alen, self.alen),
            self.style
        )

        if self.double_sided:
            renderer.line(
                pos + self.start, pos + self.start + P(self.alen, -self.alen),
                self.style
            )
            renderer.line(
                pos + self.start, pos + self.start + self.alen, self.style
            )


class Spacer(Object):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.width = self._w or self.style.padding
        self.height = self._h or self.style.padding


class Text(Object):
    def __init__(self, text: str, align=Align.LEFT, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.align = align

    # TODO: the width and height may be misleading if the text is anchored in the center
    def prepare(self, renderer: Renderer):
        super().prepare(renderer)

        if not self._w or not self._h:
            _, _, right, bottom = renderer.text_bbox(self.text, self.style)
            self.width = self._w or right
            self.height = self._h or bottom

    def render(self, renderer: Renderer, pos=(0, 0)):
        if self.align == "right":
            pos = pos + P(self.width, 0)
            renderer.text(
                self.text, pos, self.style._replace(anchor=Anchor.TOP_RIGHT)
            )
        else:
            renderer.text(self.text, pos, self.style)

    def __str__(self):
        return f"{type(self).__name__}({repr(self.text)}, {self._w}, {self._h})"


class Canvas(Object):
    def render(self, renderer: Renderer, pos=P(0, 0)):
        self.width = self.style.padding
        self.height = self.style.padding
        pos = pos + self.style.padding
        for (obj, offset) in self.children:
            logger.debug('%s %s', obj, offset)
            obj.prepare(renderer)
            obj.render(renderer, pos + offset)

            # TODO: This only works for one object
            x, y = offset + pos
            self.width = max(self.width, obj.width + x)
            self.height = max(self.height, obj.height + y)

        self.width += self.style.padding
        self.height += self.style.padding

        # TODO: Should we set the renderer dimensions before we call render?
        renderer.set_dimensions((self.width, self.height))
