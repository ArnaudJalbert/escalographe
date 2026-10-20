"""Parse STM's server-rendered station equipment pages, not their index badges.

Source: https://www.stm.info/fr/infos/etat-du-service/ascenseur
The page has no equipment IDs or coordinates. Within one station, the ordinal
of an identical endpoint pair is the least misleading available identifier.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

BASE_URL = "https://www.stm.info/fr/infos/etat-du-service/ascenseur"


@dataclass
class Element:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list[Element | str] = field(default_factory=list)

    def descendants(self, *, tag: str | None = None, css_class: str | None = None):
        for child in self.children:
            if isinstance(child, Element):
                if (tag is None or child.tag == tag) and (
                    css_class is None or css_class in child.attrs.get("class", "").split()
                ):
                    yield child
                yield from child.descendants(tag=tag, css_class=css_class)

    def text(self) -> str:
        return " ".join(
            " ".join(
                child.text() if isinstance(child, Element) else child for child in self.children
            ).split()
        )


class _Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Element(tag, {key: value or "" for key, value in attrs})
        self.stack[-1].children.append(node)
        if tag not in {"img", "br", "meta", "input", "link", "hr", "source", "area", "wbr"}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Element(tag, {key: value or "" for key, value in attrs}))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _doc(html: str) -> Element:
    parser = _Document()
    parser.feed(html)
    return parser.root


def station_urls(html: str) -> list[str]:
    root = _doc(html)
    urls: list[str] = []
    for anchor in root.descendants(tag="a", css_class="escalator-resume"):
        url = urljoin(BASE_URL, anchor.attrs.get("href", ""))
        parsed = urlparse(url)
        if (
            parsed.scheme == "https"
            and parsed.netloc == "www.stm.info"
            and parsed.path.startswith("/fr/infos/etat-du-service/ascenseur/station-")
            and url not in urls
        ):
            urls.append(url)
    if not urls:
        raise ValueError("STM station index has no expected station links")
    return urls


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def _status(node: Element) -> tuple[str, str | None, str]:
    label = node.text()
    classes = " ".join(span.attrs.get("class", "") for span in node.descendants(tag="span"))
    if "icon-escalator-service-out" in classes or "hors service" in label.lower():
        return "out_of_service", None, label
    if "icon-escalator-service-up-in" in classes or "montant en service" in label.lower():
        return "operational", "up", label
    if "icon-escalator-service-down-in" in classes or "descendant en service" in label.lower():
        return "operational", "down", label
    if "vérification" in label.lower() or "verification" in label.lower():
        return "verification_needed", None, label
    return "unknown", None, label


def parse_station(html: str, url: str) -> list[dict]:
    """Return normalized equipment facts; never infer status from missing rows."""
    root = _doc(html)
    headings = [
        h
        for h in root.descendants(tag="h2", css_class="alert-title")
        if h.text().lower().startswith("station ")
    ]
    if not headings:
        raise ValueError(f"STM station page has no station heading: {url}")
    station = headings[0].text().removeprefix("Station ")
    path = urlparse(url).path
    if not path.startswith("/fr/infos/etat-du-service/ascenseur/station-"):
        raise ValueError(f"Unexpected STM station URL: {url}")
    station_id = path.rsplit("/", 1)[-1]
    sections = list(root.descendants(tag="section", css_class="details"))
    if not sections:
        # STM omits the entire section for stations without escalators.
        if "<!-- SECTION ESCALATORS -->" in html and "title-from-to" not in html:
            return []
        raise ValueError(f"STM station page has no escalator section: {url}")
    section = sections[0]
    results: list[dict] = []
    ordinals: dict[tuple[str, str], int] = {}
    siblings = section.children
    for i, node in enumerate(siblings):
        if (
            not isinstance(node, Element)
            or "title-from-to" not in node.attrs.get("class", "").split()
        ):
            continue
        labels = [
            span.text()
            for span in node.children
            if isinstance(span, Element)
            and span.tag == "span"
            and "icon" not in span.attrs.get("class", "").split()
        ]
        if len(labels) != 2 or not all(labels):
            continue
        following = next((s for s in siblings[i + 1 :] if isinstance(s, Element)), None)
        if following is None or not {"item-details", "escalators"}.issubset(
            following.attrs.get("class", "").split()
        ):
            continue
        origin, destination = labels
        key = (origin, destination)
        ordinals[key] = ordinals.get(key, 0) + 1
        columns = list(following.descendants(css_class="column-from-to"))
        for slot, column in enumerate(columns, 1):
            status, direction, raw_status = _status(column)
            # Omission of a status is not evidence of a working device.
            results.append(
                {
                    "external_id": (
                        f"{station_id}:{_slug(origin)}:{_slug(destination)}:{ordinals[key]}:{slot}"
                    ),
                    "station": station,
                    "station_id": station_id,
                    "location_description": f"{origin} → {destination}",
                    "from_level": origin,
                    "to_level": destination,
                    "direction": direction,
                    "status": status,
                    "source_status": raw_status,
                    "source_url": url,
                    "latitude": None,
                    "longitude": None,
                    "raw_data": {
                        "origin": origin,
                        "destination": destination,
                        "ordinal": ordinals[key],
                        "slot": slot,
                        "status_label": raw_status,
                    },
                }
            )
    return results
