"""VAST XML parser for processing ad responses."""

from typing import Any

from lxml import etree

from .events import VastEvents
from .exceptions import (
    VastDurationError,
    VastElementError,
    VastXMLError,
)
from .log_config import get_context_logger


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
            VastXMLError: If XML parsing fails
        """
        self.logger.debug(VastEvents.PARSE_STARTED, xml_length=len(xml_string))

        try:
            # lxml parsing with configurable encoding and recovery
            if isinstance(xml_string, str):
                parser = etree.XMLParser(
                    recover=self.config.recover_on_error, encoding=self.config.encoding
                )
                root = etree.fromstring(xml_string.encode(self.config.encoding), parser=parser)  # ruff: noqa: S320
            else:
                root = etree.fromstring(xml_string)  # ruff: noqa: S320
            self.logger.debug("XML parsed successfully", root_tag=root.tag)
        except etree.XMLSyntaxError as e:
            self.logger.error(VastEvents.PARSE_FAILED, error=str(e), xml_preview=xml_string[:200])
            raise VastXMLError(
                f"Failed to parse VAST XML: {str(e)}",
                xml_preview=xml_string[:200],
                parser_error=e,
            ) from e
        except (UnicodeDecodeError, ValueError) as e:
            self.logger.error(VastEvents.PARSE_FAILED, error=str(e), xml_preview=xml_string[:200])
            raise VastXMLError(
                f"Failed to decode or parse VAST XML: {str(e)}",
                xml_preview=xml_string[:200],
                parser_error=e,
            ) from e

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
                    "id": (creative_elem.get("id") if creative_elem is not None else None),
                    "ad_id": (creative_elem.get("adId") if creative_elem is not None else None),
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
            "media_url": (media_files[0].text if media_files and media_files[0].text else None),
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

    def parse_with_specs(self, xml_string: str, xpath_specs: list) -> dict[str, Any]:
        """Parse VAST XML using XPath specifications with callback processing.

        Args:
            xml_string: Raw VAST XML string
            xpath_specs: List of XPathSpec objects defining extraction rules

        Returns:
            Dictionary with extracted and processed data

        Raises:
            VastXMLError: If XML parsing fails or required fields are missing
        """
        from .config import ExtractMode

        self.logger.debug(
            VastEvents.PARSE_STARTED, xml_length=len(xml_string), specs_count=len(xpath_specs)
        )

        # Parse XML once
        try:
            if isinstance(xml_string, str):
                parser = etree.XMLParser(
                    recover=self.config.recover_on_error, encoding=self.config.encoding
                )
                root = etree.fromstring(xml_string.encode(self.config.encoding), parser=parser)  # ruff: noqa: S320
            else:
                root = etree.fromstring(xml_string)  # ruff: noqa: S320
            self.logger.debug(
                "XML parsed successfully for spec-based extraction", root_tag=root.tag
            )
        except etree.XMLSyntaxError as e:
            self.logger.error(VastEvents.PARSE_FAILED, error=str(e), xml_preview=xml_string[:200])
            raise VastXMLError(
                f"Failed to parse VAST XML: {str(e)}",
                xml_preview=xml_string[:200],
                parser_error=e,
            ) from e
        except (UnicodeDecodeError, ValueError) as e:
            self.logger.error(VastEvents.PARSE_FAILED, error=str(e), xml_preview=xml_string[:200])
            raise VastXMLError(
                f"Failed to decode or parse VAST XML: {str(e)}",
                xml_preview=xml_string[:200],
                parser_error=e,
            ) from e

        # Process each XPath specification
        result = {}
        processed_specs = 0

        for spec in xpath_specs:
            try:
                self.logger.debug(
                    "Processing XPath spec",
                    name=spec.name,
                    xpath=spec.xpath,
                    mode=spec.mode.value,
                    has_callback=spec.callback is not None,
                    required=spec.required,
                )

                # Extract elements based on mode
                if spec.mode == ExtractMode.SINGLE:
                    elem = root.find(spec.xpath)
                    value = elem.text if elem is not None else None
                    if spec.mode == ExtractMode.SINGLE and elem is None:
                        extracted_count = 0
                    else:
                        extracted_count = 1 if elem is not None else 0
                else:  # ExtractMode.LIST
                    elems = root.findall(spec.xpath)
                    value = [elem.text for elem in elems if elem is not None and elem.text]
                    extracted_count = len(value)

                self.logger.debug(
                    "XPath extraction completed",
                    name=spec.name,
                    extracted_count=extracted_count,
                    has_value=value is not None
                    and (len(value) > 0 if isinstance(value, list) else True),
                )

                # Apply callback if provided
                if spec.callback and value is not None:
                    try:
                        original_value = value
                        value = spec.callback(value)
                        self.logger.debug(
                            "Callback applied successfully",
                            name=spec.name,
                            original_type=type(original_value).__name__,
                            result_type=type(value).__name__,
                        )
                    except Exception as e:
                        self.logger.error(
                            "Callback failed for XPath spec",
                            name=spec.name,
                            error=str(e),
                            xpath=spec.xpath,
                        )
                        if spec.required:
                            raise VastXMLError(
                                f"Required callback failed for field '{spec.name}': {str(e)}",
                                context={
                                    "xpath": spec.xpath,
                                    "spec_name": spec.name,
                                    "callback_error": str(e),
                                },
                            ) from e
                        # For optional specs, continue with original value
                        value = original_value

                # Check required fields
                if spec.required:
                    if spec.mode == ExtractMode.SINGLE and value is None:
                        raise VastXMLError(
                            f"Required field '{spec.name}' not found",
                            context={
                                "xpath": spec.xpath,
                                "spec_name": spec.name,
                            },
                        )
                    elif spec.mode == ExtractMode.LIST and (value is None or len(value) == 0):
                        raise VastXMLError(
                            f"Required field '{spec.name}' has no values",
                            context={
                                "xpath": spec.xpath,
                                "spec_name": spec.name,
                            },
                        )

                result[spec.name] = value
                processed_specs += 1

                self.logger.debug(
                    "XPath spec processed successfully",
                    name=spec.name,
                    processed_specs=processed_specs,
                    total_specs=len(xpath_specs),
                )

            except VastXMLError:
                # Re-raise required field errors
                raise
            except Exception as e:
                self.logger.error(
                    "Failed to process XPath spec", name=spec.name, xpath=spec.xpath, error=str(e)
                )
                if spec.required:
                    raise VastXMLError(
                        f"Failed to process required field '{spec.name}': {str(e)}",
                        context={
                            "xpath": spec.xpath,
                            "spec_name": spec.name,
                            "processing_error": str(e),
                        },
                    ) from e
                # For optional specs, set to None and continue
                result[spec.name] = None
                processed_specs += 1

        self.logger.info(
            "Spec-based parsing completed",
            processed_specs=processed_specs,
            total_specs=len(xpath_specs),
            result_keys=list(result.keys()),
        )
        return result

    def parse_extensions(self, root: etree._Element) -> dict[str, Any]:
        """Parse VAST extensions from XML root element.

        Args:
            root: Root XML element

        Returns:
            Dictionary of parsed extensions

        Note:
            Element parsing errors are logged as warnings and do not stop parsing.
        """
        self.logger.debug("Parsing VAST extensions")
        extensions = {}
        try:
            extension_elems = root.findall(self.config.xpath_extensions)
            self.logger.debug("Found extensions", count=len(extension_elems))

            for extension in extension_elems:
                type_attr = extension.get("type")
                if type_attr:
                    try:
                        extensions[type_attr] = self.element_to_dict(extension)
                        self.logger.debug("Parsed extension", type=type_attr)
                    except VastElementError as e:
                        self.logger.warning(
                            "Failed to parse extension",
                            error=str(e),
                            extension_type=type_attr,
                            message=e.message,
                        )
                        # Continue parsing other extensions
                        continue

            # Parse custom XPath fields
            for field_name, xpath in self.config.custom_xpaths.items():
                try:
                    custom_elems = root.findall(xpath)
                    if custom_elems:
                        extensions[field_name] = [elem.text for elem in custom_elems if elem.text]
                        self.logger.debug(
                            "Parsed custom field",
                            field_name=field_name,
                            values_count=len(extensions[field_name]),
                        )
                except ValueError as e:
                    self.logger.warning(
                        "Failed to parse custom XPath field",
                        error=str(e),
                        field_name=field_name,
                    )
                    # Continue parsing other custom fields
                    continue

        except etree.XPathError as e:
            self.logger.warning(
                "XPath error while parsing extensions",
                error=str(e),
            )
            # Return partial results
        except Exception as e:
            # Catch any remaining unexpected errors
            self.logger.error(
                "Unexpected error while parsing extensions",
                error=str(e),
            )
            # Return partial results - extensions are not critical

        self.logger.debug("Extensions parsing completed", extensions_count=len(extensions))
        return extensions

    def parse_duration(self, root: etree._Element) -> int | None:
        """Parse duration from VAST XML.

        Args:
            root: Root XML element

        Returns:
            Duration in seconds or None if not found/invalid

        Raises:
            VastDurationError: If duration parsing fails (logged as warning)
        """
        self.logger.debug("Parsing VAST duration")
        try:
            duration_elem = root.find(self.config.xpath_duration)

            if duration_elem is not None and duration_elem.text:
                self.logger.debug("Found duration element", duration_text=duration_elem.text)
                return self._parse_duration_string(duration_elem.text)
            self.logger.debug("No duration element found")
            return None
        except VastDurationError as e:
            self.logger.warning(
                "Failed to parse duration",
                error=str(e),
                message=e.message,
                duration_text=e.duration_text,
            )
            return None
        except Exception as e:
            self.logger.warning(
                "Unexpected error while finding duration element",
                error=str(e),
            )
            return None

    def _parse_duration_string(self, duration_text: str) -> int:
        """Parse duration string in HH:MM:SS format.

        Args:
            duration_text: Duration string (e.g., "00:00:30")

        Returns:
            Duration in seconds

        Raises:
            VastDurationError: If duration format is invalid
        """
        try:
            duration_parts = duration_text.split(":")
            if len(duration_parts) != 3:
                raise VastDurationError(
                    f"Invalid duration format: {duration_text}. Expected HH:MM:SS",
                    duration_text=duration_text,
                )

            duration = (
                int(float(duration_parts[0])) * 3600
                + int(float(duration_parts[1])) * 60
                + int(float(duration_parts[2]))
            )
            self.logger.debug("Duration parsed successfully", duration_seconds=duration)
            return duration
        except ValueError as e:
            raise VastDurationError(
                f"Failed to parse duration value: {str(e)}",
                duration_text=duration_text,
            ) from e

    def element_to_dict(self, element: etree._Element) -> dict[str, Any]:
        """Convert XML element to dictionary.

        Args:
            element: XML element to convert

        Returns:
            Dictionary representation of the element

        Raises:
            VastElementError: If element conversion fails
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
                        try:
                            result[child.tag] = self.element_to_dict(child)
                        except Exception as e:
                            if isinstance(e, VastElementError):
                                raise
                            raise VastElementError(
                                f"Failed to recursively convert child element: {str(e)}",
                                element_tag=child.tag,
                                operation="recursive_conversion",
                            ) from e
        except AttributeError as e:
            raise VastElementError(
                f"Invalid element structure: {str(e)}",
                element_tag=getattr(element, "tag", "unknown"),
                operation="element_access",
            ) from e
        except Exception as e:
            if isinstance(e, VastElementError):
                raise
            raise VastElementError(
                f"Failed to convert element to dictionary: {str(e)}",
                element_tag=element.tag,
                operation="to_dict",
            ) from e
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
