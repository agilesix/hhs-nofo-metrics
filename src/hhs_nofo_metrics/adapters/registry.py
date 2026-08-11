"""Built-in and Python-entry-point adapter discovery."""

from __future__ import annotations

from importlib import metadata
from typing import Iterable

from hhs_nofo_metrics.errors import AdapterContractError, AdapterNotFoundError

from .builtin import HtmlAdapterPlugin, PdfAdapterPlugin
from .contracts import AdapterDescriptor, AdapterPlugin
from .tagged_pdf import TaggedPdfAdapterPlugin

ENTRY_POINT_GROUP = "hhs_nofo_metrics.adapters"


class _LazyEntryPointPlugin:
    """Expose a descriptor without constructing the plugin until first use."""

    def __init__(self, loaded: object, descriptor: AdapterDescriptor) -> None:
        self.descriptor = descriptor
        self._loaded = loaded
        self._instance: AdapterPlugin | None = None

    def _plugin(self) -> AdapterPlugin:
        if self._instance is None:
            candidate = self._loaded() if callable(self._loaded) else self._loaded
            if getattr(candidate, "descriptor", None) != self.descriptor:
                raise AdapterContractError(
                    f"adapter factory for {self.descriptor.reference} returned a "
                    "plugin with a different descriptor"
                )
            self._instance = candidate  # type: ignore[assignment]
        return self._instance

    def inspect_support(self, source):
        return self._plugin().inspect_support(source)

    def extract(self, source, *, config):
        return self._plugin().extract(source, config=config)


class AdapterRegistry:
    def __init__(
        self,
        *,
        plugins: Iterable[AdapterPlugin] = (),
        aliases: dict[str, str] | None = None,
        load_entry_points: bool = False,
    ) -> None:
        self._plugins: dict[str, AdapterPlugin] = {}
        self._aliases = dict(aliases or {})
        self._entry_points_loaded = not load_entry_points
        for plugin in plugins:
            self.register(plugin)

    def register(self, plugin: AdapterPlugin) -> None:
        try:
            descriptor = plugin.descriptor
        except AttributeError as exc:
            raise AdapterContractError("adapter plugin has no descriptor") from exc
        if not isinstance(descriptor, AdapterDescriptor):
            raise AdapterContractError(
                "adapter plugin descriptor must be an AdapterDescriptor"
            )
        if descriptor.reference in self._plugins:
            raise AdapterContractError(
                f"duplicate adapter reference: {descriptor.reference}"
            )
        self._plugins[descriptor.reference] = plugin

    def _load_entry_points(self) -> None:
        if self._entry_points_loaded:
            return
        entry_points = metadata.entry_points()
        selected = (
            entry_points.select(group=ENTRY_POINT_GROUP)
            if hasattr(entry_points, "select")
            else entry_points.get(ENTRY_POINT_GROUP, ())
        )
        pending: list[AdapterPlugin] = []
        for entry_point in selected:
            try:
                loaded = entry_point.load()
                descriptor = getattr(loaded, "descriptor", None)
                if not isinstance(descriptor, AdapterDescriptor):
                    raise AdapterContractError(
                        f"adapter entry point '{entry_point.name}' must expose an "
                        "AdapterDescriptor without factory execution"
                    )
                plugin = _LazyEntryPointPlugin(loaded, descriptor)
                pending.append(plugin)
            except AdapterContractError:
                raise
            except Exception as exc:
                raise AdapterContractError(
                    f"unable to load adapter entry point '{entry_point.name}': {exc}"
                ) from exc
        references = [plugin.descriptor.reference for plugin in pending]
        duplicate_pending = {
            reference for reference in references if references.count(reference) > 1
        }
        duplicate_existing = set(references) & set(self._plugins)
        duplicates = duplicate_pending | duplicate_existing
        if duplicates:
            raise AdapterContractError(
                "duplicate adapter reference(s): " + ", ".join(sorted(duplicates))
            )
        for plugin in pending:
            self.register(plugin)
        self._entry_points_loaded = True

    def resolve(self, reference: str) -> AdapterPlugin:
        self._load_entry_points()
        requested = self._aliases.get(reference, reference)
        if "@" in requested:
            try:
                return self._plugins[requested]
            except KeyError as exc:
                raise AdapterNotFoundError(f"Unknown adapter: {reference}") from exc
        matches = [
            plugin
            for plugin in self._plugins.values()
            if plugin.descriptor.id == requested
        ]
        if not matches:
            raise AdapterNotFoundError(f"Unknown adapter: {reference}")
        if len(matches) > 1:
            available = ", ".join(
                sorted(plugin.descriptor.reference for plugin in matches)
            )
            raise AdapterContractError(
                f"Adapter reference '{reference}' is ambiguous; use one of: {available}"
            )
        return matches[0]

    def descriptors(self) -> tuple[AdapterDescriptor, ...]:
        self._load_entry_points()
        return tuple(
            sorted(
                (plugin.descriptor for plugin in self._plugins.values()),
                key=lambda descriptor: descriptor.reference,
            )
        )


def create_default_registry(*, load_entry_points: bool = True) -> AdapterRegistry:
    pdf = PdfAdapterPlugin()
    html = HtmlAdapterPlugin()
    tagged_pdf = TaggedPdfAdapterPlugin()
    return AdapterRegistry(
        plugins=(pdf, html, tagged_pdf),
        aliases={
            "pdf": pdf.descriptor.reference,
            "html": html.descriptor.reference,
            "tagged-pdf": tagged_pdf.descriptor.reference,
        },
        load_entry_points=load_entry_points,
    )


_DEFAULT_REGISTRY: AdapterRegistry | None = None


def default_registry() -> AdapterRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = create_default_registry()
    return _DEFAULT_REGISTRY
