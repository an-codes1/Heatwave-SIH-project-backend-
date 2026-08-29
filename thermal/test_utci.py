from thermal.utci import calculate_utci


def main() -> None:
    result = calculate_utci(
        air_temperature_c=25.0,
        mean_radiant_temperature_c=25.0,
        wind_speed_ms=1.0,
        relative_humidity_pct=50.0,
    )

    print("UTCI test")
    print("---------")
    print(f"Valid: {result.valid}")
    print(f"UTCI: {result.utci_c}")
    print(f"Stress category: {result.stress_category}")

    if not result.valid:
        raise RuntimeError(
            f"UTCI test failed: {result.reason}"
        )


if __name__ == "__main__":
    main()