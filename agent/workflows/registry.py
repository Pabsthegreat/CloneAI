"""
Workflow registry and metadata for CloneAI.
Enables modular registration and execution of CLI workflows.
"""

from __future__ import annotations

import shlex
import threading
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
)


# Type aliases for readability
ParameterParser = Callable[[str, "WorkflowSpec"], Dict[str, Any]]
WorkflowHandler = Callable[["WorkflowContext", Dict[str, Any]], Any]


class WorkflowError(Exception):
    """Base exception for workflow related failures."""


class WorkflowNotFoundError(WorkflowError):
    """Raised when no workflow matches the requested command."""


class WorkflowValidationError(WorkflowError):
    """Raised when user input fails validation."""


class WorkflowExecutionError(WorkflowError):
    """Raised when workflow execution fails."""


class WorkflowRegistrationError(WorkflowError):
    """Raised when registration fails (e.g., duplicate command)."""


@dataclass(frozen=True)
class ParameterSpec:
    """Metadata describing a workflow parameter."""

    name: str
    description: str = ""
    type: Callable[[str], Any] = str
    required: bool = False
    default: Any = None
    aliases: Sequence[str] = field(default_factory=tuple)
    parser: Optional[Callable[[str], Any]] = None
    position: Optional[int] = None  # for positional arguments

    def parse_value(self, raw: str) -> Any:
        """Convert raw string to typed value."""
        converter = self.parser or self.type
        if converter is bool:
            # Interpret common truthy/falsey values
            lowered = raw.lower()
            if lowered in ("false", "0", "no", "n", "off"):
                return False
            if lowered in ("true", "1", "yes", "y", "on"):
                return True
            raise WorkflowValidationError(
                f"Invalid boolean value '{raw}' for parameter '{self.name}'"
            )
        try:
            return converter(raw)
        except WorkflowValidationError:
            raise
        except Exception as exc:  # pragma: no cover - repr for unexpected parser error
            raise WorkflowValidationError(
                f"Failed to parse parameter '{self.name}': {exc}"
            ) from exc


@dataclass
class WorkflowSpec:
    """Represents a workflow command that can be executed."""

    namespace: str
    name: str
    summary: str
    description: str
    handler: WorkflowHandler
    parameters: Sequence[ParameterSpec] = field(default_factory=tuple)
    parameter_parser: Optional[ParameterParser] = None
    preferred_llm: str = "local"  # "local" or "cloud"
    safety_tags: Sequence[str] = field(default_factory=tuple)
    auto_retry: bool = False
    max_retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def command_key(self) -> str:
        return f"{self.namespace}:{self.name}"

    def parse_arguments(self, raw_args: str) -> Dict[str, Any]:
        """Parse argument string using custom parser or default logic."""
        if not raw_args.strip() and not self.parameters:
            return {}

        if self.parameter_parser:
            return self.parameter_parser(raw_args, self)

        return _default_parse_arguments(raw_args, self.parameters)


@dataclass
class WorkflowContext:
    """Context provided to workflow handlers."""

    raw_command: str
    registry: "WorkflowRegistry"
    extras: MutableMapping[str, Any] = field(default_factory=dict)

    def with_extra(self, key: str, value: Any) -> None:
        """Attach additional metadata for downstream consumers."""
        self.extras[key] = value


@dataclass
class WorkflowExecutionResult:
    """Structured result from executing a workflow."""

    spec: WorkflowSpec
    arguments: Dict[str, Any]
    output: Any


class WorkflowRegistry:
    """Stores registered workflows and executes them."""

    def __init__(self):
        self._lock = threading.RLock()
        self._workflows: Dict[str, WorkflowSpec] = {}

    def register(self, spec: WorkflowSpec) -> WorkflowSpec:
        """Register a workflow spec."""
        key = spec.command_key()
        with self._lock:
            if key in self._workflows:
                raise WorkflowRegistrationError(
                    f"Workflow '{key}' is already registered"
                )
            self._workflows[key] = spec
        return spec

    def register_from_callable(
        self,
        *,
        namespace: str,
        name: str,
        summary: str,
        description: str,
        handler: WorkflowHandler,
        parameters: Optional[Sequence[ParameterSpec]] = None,
        parameter_parser: Optional[ParameterParser] = None,
        preferred_llm: str = "local",
        safety_tags: Optional[Sequence[str]] = None,
        auto_retry: bool = False,
        max_retries: int = 0,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> WorkflowSpec:
        """Helper to build and register a workflow spec from a callable."""
        spec = WorkflowSpec(
            namespace=namespace,
            name=name,
            summary=summary,
            description=description,
            handler=handler,
            parameters=tuple(parameters or ()),
            parameter_parser=parameter_parser,
            preferred_llm=preferred_llm,
            safety_tags=tuple(safety_tags or ()),
            auto_retry=auto_retry,
            max_retries=max_retries,
            metadata=dict(metadata or {}),
        )
        return self.register(spec)

    def iter_workflows(self) -> Iterable[WorkflowSpec]:
        """Yield registered workflow specs."""
        with self._lock:
            # Return a snapshot to avoid mutation during iteration
            return tuple(self._workflows.values())

    def register_decorator(
        self,
        *,
        namespace: str,
        name: str,
        summary: str,
        description: str,
        parameters: Optional[Sequence[ParameterSpec]] = None,
        parameter_parser: Optional[ParameterParser] = None,
        preferred_llm: str = "local",
        safety_tags: Optional[Sequence[str]] = None,
        auto_retry: bool = False,
        max_retries: int = 0,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> Callable[[WorkflowHandler], WorkflowHandler]:
        """Decorator to register a workflow."""

        def decorator(func: WorkflowHandler) -> WorkflowHandler:
            self.register_from_callable(
                namespace=namespace,
                name=name,
                summary=summary,
                description=description,
                handler=func,
                parameters=parameters,
                parameter_parser=parameter_parser,
                preferred_llm=preferred_llm,
                safety_tags=safety_tags,
                auto_retry=auto_retry,
                max_retries=max_retries,
                metadata=metadata,
            )
            return func

        return decorator

    def get(self, namespace: str, name: str) -> WorkflowSpec:
        """Retrieve a workflow spec by namespace/name."""
        key = f"{namespace}:{name}"
        with self._lock:
            if key not in self._workflows:
                raise WorkflowNotFoundError(f"No workflow registered for '{key}'")
            return self._workflows[key]

    def list(self, namespace: Optional[str] = None) -> Iterable[WorkflowSpec]:
        """Iterate over registered workflows (optionally filtered by namespace)."""
        with self._lock:
            specs = list(self._workflows.values())
        if namespace:
            return (spec for spec in specs if spec.namespace == namespace)
        return iter(specs)

    def export_command_info(self) -> Iterable[Dict[str, Any]]:
        """Produce metadata dictionaries for each registered workflow."""
        for spec in self.list():
            metadata = dict(spec.metadata)
            usage = metadata.get("usage") or f"{spec.command_key()}"
            category = metadata.get("category") or f"{spec.namespace.upper()} COMMANDS"

            yield {
                "namespace": spec.namespace,
                "name": spec.name,
                "usage": usage,
                "summary": spec.summary,
                "description": spec.description,
                "category": category,
                "examples": metadata.get("examples", []),
                "preferred_llm": spec.preferred_llm,
                "safety_tags": spec.safety_tags,
            }

    def execute(
        self,
        raw_command: str,
        *,
        extras: Optional[MutableMapping[str, Any]] = None,
    ) -> WorkflowExecutionResult:
        """
        Execute a workflow from a raw command string.

        Args:
            raw_command: e.g. "mail:list last 5"
            extras: optional metadata for context
        """
        namespace, name, arg_string = self._split_command(raw_command)
        spec = self.get(namespace, name)
        arguments = spec.parse_arguments(arg_string)

        context = WorkflowContext(
            raw_command=raw_command,
            registry=self,
            extras=extras or {},
        )

        try:
            output = spec.handler(context, arguments)
        except WorkflowExecutionError:
            raise
        except Exception as exc:
            raise WorkflowExecutionError(
                f"Workflow '{spec.command_key()}' failed: {exc}"
            ) from exc

        return WorkflowExecutionResult(spec=spec, arguments=arguments, output=output)

    @staticmethod
    def _split_command(raw_command: str) -> tuple[str, str, str]:
        if not raw_command or ":" not in raw_command:
            raise WorkflowValidationError(
                "Commands must include a namespace and action (e.g. 'mail:list')."
            )

        stripped = raw_command.strip()
        head, _, tail = stripped.partition(" ")
        namespace, _, name = head.partition(":")

        if not namespace or not name:
            raise WorkflowValidationError(
                "Invalid command format. Expected 'namespace:action'."
            )

        return namespace, name, tail.strip()


def _default_parse_arguments(
    raw_args: str,
    parameters: Sequence[ParameterSpec],
) -> Dict[str, Any]:
    """Parse key/value arguments using shlex semantics."""
    if not parameters:
        if raw_args.strip():
            raise WorkflowValidationError(
                f"Unexpected arguments: '{raw_args.strip()}'"
            )
        return {}

    tokens = shlex.split(raw_args, posix=True)
    params_by_name = {param.name: param for param in parameters}
    alias_map = {
        alias: param.name
        for param in parameters
        for alias in param.aliases
    }
    positional_params = sorted(
        (param for param in parameters if param.position is not None),
        key=lambda p: p.position,
    )
    results: Dict[str, Any] = {
        param.name: param.default for param in parameters if param.default is not None
    }

    positional_index = 0

    for token in tokens:
        key: Optional[str] = None
        value: Optional[str] = None

        if ":" in token:
            key, value = token.split(":", 1)
        elif "=" in token:
            key, value = token.split("=", 1)

        if key is not None:
            key = key.lstrip("-")
            key_lower = key.lower()
            resolved_key = alias_map.get(key_lower) or alias_map.get(key) or key
            if resolved_key not in params_by_name:
                raise WorkflowValidationError(
                    f"Unknown parameter '{key}' (resolved as '{resolved_key}')"
                )
            param = params_by_name[resolved_key]
            if value is None or value == "":
                if param.type is bool or param.parser is bool:
                    results[param.name] = True
                else:
                    raise WorkflowValidationError(
                        f"Parameter '{param.name}' requires a value"
                    )
            else:
                results[param.name] = param.parse_value(value)
        else:
            if positional_index >= len(positional_params):
                raise WorkflowValidationError(
                    f"Unexpected positional argument '{token}'"
                )
            param = positional_params[positional_index]
            positional_index += 1
            results[param.name] = param.parse_value(token)

    # Validate required params
    missing = [
        param.name
        for param in parameters
        if param.required and results.get(param.name) is None
    ]
    if missing:
        raise WorkflowValidationError(
            f"Missing required parameter(s): {', '.join(missing)}"
        )

    # Apply defaults for optional params not set
    for param in parameters:
        if param.name not in results and param.default is not None:
            results[param.name] = param.default

    return results


# Registry instance shared across the application
registry = WorkflowRegistry()


def register_workflow(
    *,
    namespace: str,
    name: str,
    summary: str,
    description: str,
    parameters: Optional[Sequence[ParameterSpec]] = None,
    parameter_parser: Optional[ParameterParser] = None,
    preferred_llm: str = "local",
    safety_tags: Optional[Sequence[str]] = None,
    auto_retry: bool = False,
    max_retries: int = 0,
    metadata: Optional[Mapping[str, Any]] = None,
) -> Callable[[WorkflowHandler], WorkflowHandler]:
    """
    Public decorator to register workflows globally.

    Usage:
        @register_workflow(
            namespace="mail",
            name="list",
            summary="List recent emails",
            description="Fetches emails from Gmail",
            parameters=[...],
        )
        def handle_mail_list(ctx, params):
            ...
    """
    return registry.register_decorator(
        namespace=namespace,
        name=name,
        summary=summary,
        description=description,
        parameters=parameters,
        parameter_parser=parameter_parser,
        preferred_llm=preferred_llm,
        safety_tags=safety_tags,
        auto_retry=auto_retry,
        max_retries=max_retries,
        metadata=metadata,
    )


__all__ = [
    "WorkflowError",
    "WorkflowExecutionError",
    "WorkflowNotFoundError",
    "WorkflowRegistry",
    "WorkflowSpec",
    "WorkflowContext",
    "WorkflowExecutionResult",
    "WorkflowValidationError",
    "WorkflowRegistrationError",
    "ParameterSpec",
    "register_workflow",
    "registry",
]
