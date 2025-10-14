import pytest
from agent.workflows.registry import WorkflowRegistry, WorkflowValidationError, WorkflowExecutionError

def get_registry():
    from agent.workflows.catalog import get_workflow_registry
    return get_workflow_registry()

def test_weather_forecast_success(monkeypatch):
    registry = get_registry()
    spec = registry._workflows["weather:forecast"]

    # Patch urllib to avoid real HTTP requests
    import agent.workflows.generated.weather_forecast as wfmod

    def fake_geocode(city):
        assert city.lower() == "seattle"
        return "Weather forecast for Seattle, King County, Washington, USA:\nTemperature: 15°C\nWind speed: 10 km/h\nConditions: Clear sky"
    monkeypatch.setattr(wfmod, "fetch_weather_forecast", fake_geocode)

    ctx = type("Ctx", (), {"raw_command": "weather:forecast city:Seattle", "registry": registry, "extras": {}})()
    params = {"city": "Seattle"}
    result = wfmod.weather_forecast_handler(ctx, params)
    assert "Weather forecast for Seattle" in result
    assert "Temperature:" in result
    assert "Conditions:" in result

def test_weather_forecast_missing_city():
    registry = get_registry()
    spec = registry._workflows["weather:forecast"]
    ctx = type("Ctx", (), {"raw_command": "weather:forecast", "registry": registry, "extras": {}})()
    import agent.workflows.generated.weather_forecast as wfmod
    with pytest.raises(WorkflowValidationError):
        wfmod.weather_forecast_handler(ctx, {"city": ""})
    with pytest.raises(WorkflowValidationError):
        wfmod.weather_forecast_handler(ctx, {})

def test_weather_forecast_geocode_error(monkeypatch):
    registry = get_registry()
    ctx = type("Ctx", (), {"raw_command": "weather:forecast city:Atlantis", "registry": registry, "extras": {}})()
    import agent.workflows.generated.weather_forecast as wfmod
    def fail_geocode(city):
        raise WorkflowExecutionError("Failed to geocode city")
    monkeypatch.setattr(wfmod, "fetch_weather_forecast", fail_geocode)
    with pytest.raises(WorkflowExecutionError):
        wfmod.weather_forecast_handler(ctx, {"city": "Atlantis"})
