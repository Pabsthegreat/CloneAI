import pytest
from agent.workflows.registry import WorkflowRegistry, WorkflowNotFoundError

def test_weather_bangalore_registered():
    registry = WorkflowRegistry()
    # Import triggers registration
    import agent.workflows.generated.weather_bangalore
    spec = registry._workflows.get("weather:bangalore")
    assert spec is not None
    assert spec.namespace == "weather"
    assert spec.name == "bangalore"
    assert callable(spec.handler)

def test_weather_bangalore_handler(monkeypatch):
    import agent.workflows.generated.weather_bangalore as wb
    from agent.workflows.registry import WorkflowContext

    # Patch _fetch_bangalore_weather to return a fixed value
    monkeypatch.setattr(wb, "_fetch_bangalore_weather", lambda: {
        "temperature": 28.5,
        "windspeed": 10.2,
        "winddirection": 180,
        "weathercode": 2,
        "time": "2024-06-01T12:00:00Z"
    })
    ctx = WorkflowContext(raw_command="weather:bangalore", registry=None)
    result = wb.weather_bangalore_handler(ctx, {})
    assert "Current weather in Bangalore" in result
    assert "Temperature: 28.5" in result
    assert "Partly cloudy" in result
    assert "Wind: 10.2 km/h" in result
    assert "2024-06-01T12:00:00Z" in result

def test_weather_bangalore_handler_error(monkeypatch):
    import agent.workflows.generated.weather_bangalore as wb
    from agent.workflows.registry import WorkflowContext

    def fail():
        raise wb.WorkflowExecutionError("API down")
    monkeypatch.setattr(wb, "_fetch_bangalore_weather", fail)
    ctx = WorkflowContext(raw_command="weather:bangalore", registry=None)
    result = wb.weather_bangalore_handler(ctx, {})
    assert "Error fetching Bangalore weather" in result
