"""
Auto Macro Mapping Example

Demonstrates the simplified macro mapping where:
- device_serial: DEVICE_SERIAL automatically maps to ad_request.device_serial
- No need to write "${ad_request.device_serial}" anymore!
"""

import asyncio
from vast_client import ProviderConfigLoader
from vast_client.capabilities import with_macros
from vast_client.config import VastTrackerConfig
from vast_client.embed_http_client import EmbedHttpClient
from vast_client.trackable import TrackableEvent
from vast_client.tracker import VastTracker


async def example_auto_macro_mapping():
    """Demonstrate automatic macro mapping with ad_request base path."""

    # Sample YAML config would look like:
    # tracker:
    #   macro_mapping:
    #     device_serial: DEVICE_SERIAL  # Maps to ad_request.device_serial
    #     city: CITY                     # Maps to ad_request.city
    #     user_id: USER_ID               # Maps to ad_request.user_id

    macro_mapping = {
        "device_serial": "DEVICE_SERIAL",
        "city": "CITY",
        "user_id": "USER_ID",
        "placement_type": "PLACEMENT_TYPE",
    }

    ad_request = {
        "device_serial": "ABC-123-XYZ-789",
        "city": "New York",
        "user_id": "user_12345",
        "placement_type": "preroll",
    }

    # Process macro mappings
    result = ProviderConfigLoader.process_macro_mappings(macro_mapping, ad_request)

    print("=" * 60)
    print("Auto Macro Mapping Example")
    print("=" * 60)
    print("\nYAML Configuration:")
    print("  tracker:")
    print("    macro_mapping:")
    for param, macro in macro_mapping.items():
        print(f"      {param}: {macro}")

    print("\nAd Request Data:")
    for key, value in ad_request.items():
        print(f"  {key}: {value}")

    print("\nResolved Macros:")
    for macro, value in result.items():
        print(f"  [{macro}] → {value}")

    print("\n" + "=" * 60)
    print("✅ Automatic mapping: param_name → ad_request.param_name")
    print("=" * 60)


async def example_nested_path_mapping():
    """Demonstrate nested path auto-mapping."""

    # YAML config:
    # tracker:
    #   macro_mapping:
    #     device_serial: DEVICE_SERIAL
    #     ext.channel_to.display_name: CHANNEL_NAME
    #     ext.domain: DOMAIN

    macro_mapping = {
        "device_serial": "DEVICE_SERIAL",
        "ext.channel_to.display_name": "CHANNEL_NAME",
        "ext.domain": "DOMAIN",
    }

    ad_request = {
        "device_serial": "DEV-999",
        "ext": {
            "channel_to": {"display_name": "HBO HD", "category": "Movies"},
            "domain": "example.com",
        },
    }

    result = ProviderConfigLoader.process_macro_mappings(macro_mapping, ad_request)

    print("\n" + "=" * 60)
    print("Nested Path Auto-Mapping Example")
    print("=" * 60)
    print("\nMacro Mappings:")
    for param, macro in macro_mapping.items():
        print(f"  {param} → [{macro}]")

    print("\nResolved Macros:")
    for macro, value in result.items():
        print(f"  [{macro}] = {value}")

    print("\n✅ Nested paths work automatically!")
    print("=" * 60)


async def example_before_and_after():
    """Show the difference between old and new approach."""

    print("\n" + "=" * 60)
    print("BEFORE vs AFTER Comparison")
    print("=" * 60)

    print("\n❌ OLD APPROACH (verbose):")
    print("  tracker:")
    print("    macro_mapping:")
    print("      city: CITY")
    print("      city_code: CITY_CODE")
    print('      device_serial: "${ad_request.device_serial}"  # ← Verbose!')

    print("\n✅ NEW APPROACH (simplified):")
    print("  tracker:")
    print("    macro_mapping:")
    print("      city: CITY              # Auto: ad_request.city")
    print("      city_code: CITY_CODE    # Auto: ad_request.city_code")
    print("      device_serial: DEVICE_SERIAL  # Auto: ad_request.device_serial")

    print("\n💡 Benefits:")
    print("  • Less verbose - no need to write '${ad_request.X}'")
    print("  • Clearer intent - just param_name: MACRO_NAME")
    print("  • Auto-resolves to ad_request.param_name")
    print("  • Nested paths supported: ext.channel.name: CHANNEL_NAME")
    print("=" * 60)


async def example_tracking_url_auto_access():
    """Demonstrate auto-accessing ad_request fields from tracking URLs."""

    embed_client = EmbedHttpClient(
        base_url="https://example.com/vast",
        base_params={"device_serial": "AUTO-DEVICE-001"},
    )
    embed_client.set_extra(
        "ad_request",
        {
            "device_serial": "AUTO-DEVICE-001",
            "city": "New York",
            "ext": {"domain": "demo.example"},
        },
    )

    tracker = VastTracker(
        tracking_events={"impression": []},
        embed_client=embed_client,
        config=VastTrackerConfig(macro_formats=["[{macro}]"]),
    )

    MacroTrackable = with_macros(TrackableEvent)
    trackable = MacroTrackable(
        key="impression_0",
        value="https://tracker.example/[DEVICE_SERIAL]?city=[CITY]&domain=[EXT_DOMAIN]",
    )

    resolved_url = tracker._get_trackable_url(trackable, tracker.static_macros)

    print("\n" + "=" * 60)
    print("Tracking URL Auto-Access Example")
    print("=" * 60)
    print("Original URL template:")
    print(f"  {trackable.value}")
    print("\nResolved URL (no macro_mapping needed):")
    print(f"  {resolved_url}")
    print("\nMacros available:")
    for key in sorted(tracker.static_macros.keys()):
        if key in {"DEVICE_SERIAL", "CITY", "EXT_DOMAIN"}:
            print(f"  [{key}] = {tracker.static_macros[key]}")
    print("\n✅ Macros pulled directly from ad_request (auto-access)")
    print("=" * 60)


async def main():
    """Run all examples."""

    print("\n" + "=" * 60)
    print("Auto Macro Mapping Examples")
    print("=" * 60)

    await example_auto_macro_mapping()
    await example_nested_path_mapping()
    await example_before_and_after()
    await example_tracking_url_auto_access()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
