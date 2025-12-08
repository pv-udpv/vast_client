"""VAST XML parser for processing ad responses."""

from typing import Any

from lxml import etree

from ..events import VastEvents
from ..log_config import get_context_logger


class VastParser:
    """Parser for VAST XML responses."""

    def __init__(self, config=None):
        # Use contextual logger that automatically picks up context variables
        self.logger = get_context_logger("vast_parser")

        # Initialize config
        if config is None:
            from .config import VastParserConfig
            self.config = VastParserConfig()
        else:
            self.config = config

    def parse_vast(self, xml_string: str) -> dict[str, Any]:
        """Parse VAST XML string into structured data.

        Args:
            xml_string: Raw VAST XML string

        Returns:
            Parsed VAST data as dictionary

        Raises:
            etree.XMLSyntaxError: If XML parsing fails
        """
        self.logger.debug(VastEvents.PARSE_STARTED, xml_length=len(xml_string))

        try:
            # lxml parsing with configurable encoding and recovery
            if isinstance(xml_string, str):
                parser = etree.XMLParser(
                    recover=self.config.recover_on_error,
                    encoding=self.config.encoding
                )
                root = etree.fromstring(xml_string.encode(self.config.encoding), parser=parser)  # ruff: noqa: S320
            else:
                root = etree.fromstring(xml_string)  # ruff: noqa: S320
            self.logger.debug("XML parsed successfully", root_tag=root.tag)
        except etree.XMLSyntaxError as e:
            self.logger.error(
                VastEvents.PARSE_FAILED, error=str(e), xml_preview=xml_string[:200]
            )
            raise

        # Parse main elements using configurable XPath
        vast_version = root.get("version")
        ad_system_elem = root.find(self.config.xpath_ad_system)
        ad_title_elem = root.find(self.config.xpath_ad_title)
        impression_elems = root.findall(self.config.xpath_impression)
        error_elems = root.findall(self.config.xpath_error)
        creative_elem = root.find(self.config.xpath_creative)
        media_files = root.findall(self.config.xpath_media_files)
        tracking_events = root.findall(self.config.xpath_tracking_events)

        self.logger.debug(
            "VAST elements found",
            ad_system=ad_system_elem is not None,
            ad_title=ad_title_elem is not None,
            impressions_count=len(impression_elems),
            errors_count=len(error_elems),
            creative=creative_elem is not None,
            media_files_count=len(media_files),
            tracking_events_count=len(tracking_events),
        )

        vast_data = {
            "vast_version": vast_version,
            "ad_system": ad_system_elem.text if ad_system_elem is not None else None,
            "ad_title": ad_title_elem.text if ad_title_elem is not None else None,
            "impression": [imp.text for imp in impression_elems if imp.text],
            "error": [err.text for err in error_elems if err.text],
            "creative": (
                {
                    "id": (
                        creative_elem.get("id") if creative_elem is not None else None
                    ),
                    "ad_id": (
                        creative_elem.get("adId") if creative_elem is not None else None
                    ),
                }
                if creative_elem is not None
                else {}
            ),
            "media_files": [
                {
                    "url": media.text,
                    "delivery": media.get("delivery"),
                    "type": media.get("type"),
                    "width": media.get("width"),
                    "height": media.get("height"),
                    "bitrate": media.get("bitrate"),
                }
                for media in media_files
                if media.text
            ],
            "media_url": (
                media_files[0].text if media_files and media_files[0].text else None
            ),
            "tracking_events": {
                event.get("event"): [event.text]
                for event in tracking_events
                if event.get("event") and event.text
            },
            "extensions": self.parse_extensions(root),
            "duration": self.parse_duration(root),
        }

        self.logger.info(
            VastEvents.PARSE_COMPLETED,
            ad_system=vast_data.get("ad_system"),
            ad_title=vast_data.get("ad_title"),
            impressions_count=len(vast_data.get("impression", [])),
            media_files_count=len(vast_data.get("media_files", [])),
            tracking_events_count=len(vast_data.get("tracking_events", {})),
            duration=vast_data.get("duration"),
        )
        return vast_data

    def parse_extensions(self, root: etree._Element) -> dict[str, Any]:
        """Parse VAST extensions from XML root element.

        Args:
            root: Root XML element

        Returns:
            Dictionary of parsed extensions
        """
        self.logger.debug("Parsing VAST extensions")
        extensions = {}
        try:
            extension_elems = root.findall(self.config.xpath_extensions)
            self.logger.debug("Found extensions", count=len(extension_elems))

            for extension in extension_elems:
                type_attr = extension.get("type")
                if type_attr:
                    extensions[type_attr] = self.element_to_dict(extension)
                    self.logger.debug("Parsed extension", type=type_attr)

            # Parse custom XPath fields
            for field_name, xpath in self.config.custom_xpaths.items():
                custom_elems = root.findall(xpath)
                if custom_elems:
                    extensions[field_name] = [
                        elem.text for elem in custom_elems if elem.text
                    ]
                    self.logger.debug(
                        "Parsed custom field",
                        field_name=field_name,
                        values_count=len(extensions[field_name])
                    )

        except Exception as e:
            self.logger.warning("Failed to parse extensions", error=str(e))

        self.logger.debug(
            "Extensions parsing completed", extensions_count=len(extensions)
        )
        return extensions

    def parse_duration(self, root: etree._Element) -> int | None:
        """Parse duration from VAST XML.

        Args:
            root: Root XML element

        Returns:
            Duration in seconds or None if not found/invalid
        """
        self.logger.debug("Parsing VAST duration")
        try:
            duration_elem = root.find(self.config.xpath_duration)

            if duration_elem is not None and duration_elem.text:
                self.logger.debug(
                    "Found duration element", duration_text=duration_elem.text
                )
                try:
                    duration_parts = duration_elem.text.split(":")
                    if len(duration_parts) == 3:
                        duration = (
                            int(float(duration_parts[0])) * 3600
                            + int(float(duration_parts[1])) * 60
                            + int(float(duration_parts[2]))
                        )
                        self.logger.debug(
                            "Duration parsed successfully", duration_seconds=duration
                        )
                        return duration
                    else:
                        self.logger.warning(
                            "Invalid duration format", duration_text=duration_elem.text
                        )
                except (ValueError, IndexError) as e:
                    self.logger.warning(
                        "Failed to parse duration",
                        duration_text=duration_elem.text,
                        error=str(e),
                    )
            else:
                self.logger.debug("No duration element found")
        except Exception as e:
            self.logger.warning("Failed to find duration element", error=str(e))
        return None

    def element_to_dict(self, element: etree._Element) -> dict[str, Any]:
        """Convert XML element to dictionary.

        Args:
            element: XML element to convert

        Returns:
            Dictionary representation of the element
        """
        result = {}
        try:
            # Direct access to child elements via len() and getitem
            if len(element) == 0:
                # No child elements, take text
                result[element.tag] = element.text
            else:
                # Has child elements, process recursively
                for i in range(len(element)):
                    child = element[i]
                    if len(child) == 0:
                        result[child.tag] = child.text
                    else:
                        result[child.tag] = self.element_to_dict(child)
        except Exception as e:
            self.logger.warning(
                "Failed to convert element to dict",
                error=str(e),
                element_tag=element.tag,
            )
        return result


    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "VastParser":
        """Create parser from configuration dictionary.

        Args:
            config: Configuration dictionary

        Returns:
            VastParser: Configured parser instance
        """
        from .config import VastParserConfig
        parser_config = VastParserConfig(**config)
        return cls(config=parser_config)

__all__ = ["VastParser"]
