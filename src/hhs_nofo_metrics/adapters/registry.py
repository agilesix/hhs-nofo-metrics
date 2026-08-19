"""Registry for the package's supported built-in adapters."""

from __future__ import annotations

from typing import Iterable

from hhs_nofo_metrics.errors import AdapterContractError, AdapterNotFoundError

from .builtin import HtmlAdapterPlugin, PdfAdapterPlugin
from .contracts import AdapterDescriptor, AdapterPlugin
from .tagged_pdf import TaggedPdfAdapterPlugin


class AdapterRegistry:
    def __init__(
        self,
        *,
        plugins: Iterable[AdapterPlugin] = (),
        aliases: dict[str, str] | None = None,
    ) -> None:
        self._plugins: dict[str, AdapterPlugin] = {}
        self._aliases = dict(aliases or {})
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

    def resolve(self, reference: str) -> AdapterPlugin:
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
        return tuple(
            sorted(
                (plugin.descriptor for plugin in self._plugins.values()),
                key=lambda descriptor: descriptor.reference,
            )
        )


def create_default_registry() -> AdapterRegistry:
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
    )


_DEFAULT_REGISTRY: AdapterRegistry | None = None


def default_registry() -> AdapterRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = create_default_registry()
    return _DEFAULT_REGISTRY
