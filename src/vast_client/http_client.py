"""
VAST Client HTTP Module

HTTP client implementations for VAST operations, including the base EmbedHttpClient
and VAST-specific extensions.
"""

import json
from typing import Any
from urllib.parse import quote


class EmbedHttpClient:
    """
    HTTP клиент с встроенной конфигурацией базового URL, параметров и заголовков.
    Поддерживает автоматическую сериализацию сложных типов данных и настраиваемое кодирование.
    """

    def __init__(
        self,
        base_url: str,
        base_params: dict[str, Any] | None = None,
        base_headers: dict[str, str] | None = None,
        encoding_config: dict[str, bool] | None = None,
    ):
        """
        Инициализирует HTTP клиент с базовой конфигурацией.

        Args:
            base_url (str): Базовый URL для запросов
            base_params (Dict[str, Any], optional): Базовые параметры
            base_headers (Dict[str, str], optional): Базовые заголовки
            encoding_config (Dict[str, bool], optional): Конфигурация кодирования параметров
        """
        self.base_url = base_url
        self.base_params = base_params or {}
        self.base_headers = base_headers or {}
        self.encoding_config = encoding_config or {}

    def build_url(self, additional_params: dict[str, Any] | None = None) -> str:
        """
        Строит полный URL с объединенными базовыми и дополнительными параметрами.

        Args:
            additional_params (Dict[str, Any], optional): Дополнительные параметры

        Returns:
            str: Полный URL с параметрами
        """
        # Объединяем базовые и дополнительные параметры
        final_params = {**self.base_params, **(additional_params or {})}

        return build_url_preserving_unicode(
            self.base_url, final_params, self.encoding_config
        )

    def get_headers(
        self, additional_headers: dict[str, str] | None = None
    ) -> dict[str, str]:
        """
        Возвращает объединенные базовые и дополнительные заголовки.

        Args:
            additional_headers (Dict[str, str], optional): Дополнительные заголовки

        Returns:
            Dict[str, str]: Объединенные заголовки
        """
        return {**self.base_headers, **(additional_headers or {})}

    def to_vast_config(self) -> dict[str, Any]:
        """
        Преобразует в формат конфигурации для VastClient.

        Returns:
            Dict[str, Any]: Конфигурация для VastClient
        """
        return {
            "base_url": self.base_url,
            "params": self.base_params,
            "headers": self.base_headers,
            "encoding_config": self.encoding_config,
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "EmbedHttpClient":
        """
        Создает клиент из словаря конфигурации.

        Args:
            config (Dict[str, Any]): Конфигурация с ключами base_url, params, headers, encoding_config

        Returns:
            EmbedHttpClient: Новый экземпляр клиента
        """
        return cls(
            base_url=config.get("base_url", ""),
            base_params=config.get("params", {}),
            base_headers=config.get("headers", {}),
            encoding_config=config.get("encoding_config", {}),
        )

    def copy(self) -> "EmbedHttpClient":
        """
        Создает копию клиента.

        Returns:
            EmbedHttpClient: Копия текущего клиента
        """
        return EmbedHttpClient(
            base_url=self.base_url,
            base_params=self.base_params.copy(),
            base_headers=self.base_headers.copy(),
            encoding_config=self.encoding_config.copy(),
        )

    def with_params(self, **params) -> "EmbedHttpClient":
        """
        Создает новый клиент с дополнительными параметрами.

        Args:
            **params: Дополнительные параметры

        Returns:
            EmbedHttpClient: Новый клиент с обновленными параметрами
        """
        new_client = self.copy()
        new_client.base_params.update(params)
        return new_client

    def with_headers(self, **headers) -> "EmbedHttpClient":
        """
        Создает новый клиент с дополнительными заголовками.

        Args:
            **headers: Дополнительные заголовки

        Returns:
            EmbedHttpClient: Новый клиент с обновленными заголовками
        """
        new_client = self.copy()
        new_client.base_headers.update(headers)
        return new_client

    def get_tracking_macros(self) -> dict[str, str]:
        """
        Extract tracking macros from embedded context.

        This method extracts macros that can be used for VAST tracking
        from the base_params and base_headers. Subclasses can override
        this method to provide provider-specific macro extraction.

        Returns:
            Dictionary of macro name to macro value
        """
        macros = {}

        # Standard macro mappings from base_params
        macro_mapping = {
            "ab_uid": "DEVICE_SERIAL",
            "ad_place": "PLACEMENT_TYPE",
            "media_title": "CHANNEL_NAME",
            "media_tag": "CHANNEL_CATEGORY",
        }

        for param_key, macro_key in macro_mapping.items():
            if param_key in self.base_params:
                macros[macro_key] = str(self.base_params[param_key])

        # Standard macros from base_headers
        if "User-Agent" in self.base_headers:
            macros["USER_AGENT"] = self.base_headers["User-Agent"]
        if "X-Real-Ip" in self.base_headers:
            macros["DEVICE_IP"] = self.base_headers["X-Real-Ip"]

        return macros

    def __repr__(self) -> str:
        return f"EmbedHttpClient(base_url='{self.base_url}', params={len(self.base_params)}, headers={len(self.base_headers)})"


def build_url_preserving_unicode(
    base_url: str,
    params: dict[str, Any],
    encoding_config: dict[str, bool] | None = None,
) -> str:
    """
    Строит URL с параметрами, сохраняя Unicode-символы согласно конфигурации кодирования.

    Args:
        base_url (str): Базовый URL
        params (Dict[str, Any]): Параметры для добавления к URL
        encoding_config (Dict[str, bool], optional): Конфигурация кодирования для каждого параметра

    Returns:
        str: URL с добавленными параметрами
    """
    if not params:
        return base_url

    encoding_config = encoding_config or {}
    query_parts = []

    for key, value in params.items():
        # Определяем, нужно ли кодировать этот параметр
        should_encode = encoding_config.get(key, True)

        # Сериализация значения
        if isinstance(value, dict | list | tuple):
            str_value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            str_value = str(value)

        # Кодирование согласно конфигурации
        if should_encode:
            encoded_key = quote(key, safe="")
            encoded_value = quote(str_value, safe="")
        else:
            encoded_key = key
            encoded_value = str_value

        query_parts.append(f"{encoded_key}={encoded_value}")

    # Формируем итоговый URL
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{'&'.join(query_parts)}"


class VastEmbedHttpClient(EmbedHttpClient):
    """
    Enhanced EmbedHttpClient specifically for VAST operations.
    Provides VAST-specific functionality while maintaining compatibility
    with the base EmbedHttpClient interface.
    """

    def __init__(
        self,
        base_url: str,
        base_params: dict[str, Any] | None = None,
        base_headers: dict[str, str] | None = None,
        encoding_config: dict[str, bool] | None = None,
        vast_settings: dict[str, Any] | None = None,
    ):
        """
        Initialize VAST-specific HTTP client.

        Args:
            base_url: Base URL for VAST requests
            base_params: Base parameters for all requests
            base_headers: Base headers for all requests
            encoding_config: URL encoding configuration
            vast_settings: VAST-specific settings
        """
        super().__init__(base_url, base_params, base_headers, encoding_config)
        self.vast_settings = vast_settings or {}

    def add_vast_tracking_params(self, **tracking_params) -> "VastEmbedHttpClient":
        """
        Add VAST-specific tracking parameters.

        Args:
            **tracking_params: VAST tracking parameters

        Returns:
            VastEmbedHttpClient: New client with tracking parameters
        """
        vast_params = {f"vast_{key}": value for key, value in tracking_params.items()}
        new_client = self.copy()
        new_client.base_params.update(vast_params)
        return new_client

    def with_vast_headers(self, **vast_headers) -> "VastEmbedHttpClient":
        """
        Add VAST-specific headers.

        Args:
            **vast_headers: VAST-specific headers

        Returns:
            VastEmbedHttpClient: New client with VAST headers
        """
        new_client = self.copy()
        new_client.base_headers.update(vast_headers)
        return new_client

    def copy(self) -> "VastEmbedHttpClient":
        """
        Create a copy of the VAST client.

        Returns:
            VastEmbedHttpClient: Copy of current client
        """
        return VastEmbedHttpClient(
            base_url=self.base_url,
            base_params=self.base_params.copy(),
            base_headers=self.base_headers.copy(),
            encoding_config=self.encoding_config.copy(),
            vast_settings=self.vast_settings.copy(),
        )

    def __repr__(self) -> str:
        return f"VastEmbedHttpClient(base_url='{self.base_url}', params={len(self.base_params)}, headers={len(self.base_headers)}, vast_settings={len(self.vast_settings)})"
