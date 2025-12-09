"""
YAML-Based Provider Configuration Example

Demonstrates the new declarative provider configuration system.
"""

import asyncio
from vast_client import build_provider_client, EmbedHttpClient


async def example_global_provider():
    """Example: Using AdStream Global provider."""

    # Prepare ad request context
    ad_request = {
        "device_macaddr": "00:11:22:33:44:55",
        "user_agent": "SmartTV/1.0 (Linux; Android 9)",
        "placement_type": "switchroll",
        "ext": {
            "domain": "example.com",
            "channel_to": {"display_name": "Channel 1 HD", "iptvorg_categories": "News;Sports"},
        },
    }

    # Build client from YAML configuration
    client = await build_provider_client("global", ad_request)

    print("=" * 60)
    print("AdStream Global Provider")
    print("=" * 60)
    print(f"Client: {client}")
    print(f"URL: {client.build_url()}")
    print(f"Headers: {client.get_headers()}")
    print()


async def example_tiger_provider():
    """Example: Using AdStream Tiger provider."""

    ad_request = {
        "device_macaddr": "AA:BB:CC:DD:EE:FF",
        "user_agent": "AndroidTV/2.0",
        "placement_type": "preroll",
        "ext": {
            "domain": "provider.tv",
            "channel_to": {"display_name": "Movie Channel", "iptvorg_categories": "Movies"},
        },
    }

    client = await build_provider_client("tiger", ad_request)

    print("=" * 60)
    print("AdStream Tiger Provider")
    print("=" * 60)
    print(f"URL: {client.build_url()}")
    print()


async def example_leto_provider():
    """Example: Using Leto (Rambler SSP) provider."""

    ad_request = {
        "device_macaddr": "11:22:33:44:55:66",
        "user_agent": "WebOS/3.0",
        "ext": {"domain": "rambler.ru"},
    }

    client = await build_provider_client("leto", ad_request)

    print("=" * 60)
    print("Leto (Rambler SSP) Provider")
    print("=" * 60)
    print(f"URL: {client.build_url()}")
    print()


async def example_yandex_provider():
    """Example: Using Yandex AdFox provider."""

    ad_request = {
        "device_macaddr": "FF:EE:DD:CC:BB:AA",
        "user_agent": "Tizen/5.0",
        "ext": {"domain": "yandex.ru"},
    }

    client = await build_provider_client("yandex", ad_request)

    print("=" * 60)
    print("Yandex AdFox Provider")
    print("=" * 60)
    print(f"URL: {client.build_url()}")
    print(f"Headers: {client.get_headers()}")
    print()


async def example_alternative_factory():
    """Example: Using alternative factory method."""

    ad_request = {
        "device_macaddr": "12:34:56:78:90:AB",
        "user_agent": "CustomDevice/1.0",
        "ext": {"domain": "test.com", "channel_to": {"display_name": "Test Channel"}},
    }

    # Alternative: Use class method
    client = await EmbedHttpClient.from_provider_config("global", ad_request)

    print("=" * 60)
    print("Alternative Factory Method")
    print("=" * 60)
    print(f"Client created via EmbedHttpClient.from_provider_config()")
    print(f"URL: {client.build_url()}")
    print()


async def example_template_resolution():
    """Example: Demonstrating template variable resolution."""

    from vast_client import TemplateResolver

    # Create context
    context = {
        "user": "john_doe",
        "device_serial": "DEVICE-12345",
        "placement_type": "midroll",
        "channel": {"display_name": "Premium Channel", "categories": "Entertainment;Drama"},
        "ext": {"domain": "premium.tv"},
    }

    # Test different template patterns
    templates = [
        "${user}",  # Simple substitution
        "${channel.display_name}",  # Nested path
        "${placement_type|switchroll}",  # Default value (used)
        "${missing_var|fallback}",  # Default value (missing)
        "User: ${user}, Device: ${device_serial}",  # Multiple substitutions
    ]

    print("=" * 60)
    print("Template Variable Resolution")
    print("=" * 60)

    for template in templates:
        resolved = TemplateResolver.resolve(template, context)
        print(f"Template: {template}")
        print(f"Resolved: {resolved}")
        print()


async def example_context_preparation():
    """Example: Context preparation with provider config loader."""

    from vast_client import ProviderConfigLoader

    ad_request = {
        "device_macaddr": "00:11:22:33:44:55",
        "user_agent": "SmartTV/1.0",
        "placement_type": "switchroll",
        "ext": {
            "domain": "example.com",
            "channel_to": {"display_name": "Channel 1", "iptvorg_categories": "News"},
        },
    }

    loader = ProviderConfigLoader()

    # Prepare context for global provider
    context = loader.prepare_context("global", ad_request)

    print("=" * 60)
    print("Context Preparation")
    print("=" * 60)
    print("Original ad_request keys:", list(ad_request.keys()))
    print("Prepared context keys:", list(context.keys()))
    print()
    print("Generated variables:")
    print(f"  device_serial: {context.get('device_serial')}")
    print(f"  selected_ip: {context.get('selected_ip')}")
    print(f"  channel.display_name: {context.get('channel', {}).get('display_name')}")
    print()


async def main():
    """Run all examples."""

    print("\n" + "=" * 60)
    print("YAML-Based Provider Configuration Examples")
    print("=" * 60 + "\n")

    try:
        await example_global_provider()
        await example_tiger_provider()
        await example_leto_provider()
        await example_yandex_provider()
        await example_alternative_factory()
        await example_template_resolution()
        await example_context_preparation()

        print("=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
