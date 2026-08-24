"""Microsoft Store PRO add-on integration for Media Flow.

PRO add-on product ID: 9N6VZZ3HDFHJ

Import this module from the main application and call:
    store = MicrosoftStorePro()
    owned = store.is_pro_owned()
    purchased = store.purchase_pro()

The module intentionally has no demo/trial activation path.
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import sys
from typing import Any

PRODUCT_ID = "9N6VZZ3HDFHJ"


class MicrosoftStorePro:
    def __init__(self, product_id: str = PRODUCT_ID) -> None:
        self.product_id = product_id
        self._store_context: Any = None

    def _get_context(self) -> Any:
        if self._store_context is not None:
            return self._store_context

        if sys.platform != "win32":
            raise RuntimeError("Microsoft Store solo está disponible en Windows.")

        module_name = "winrt.windows.services.store"
        if importlib.util.find_spec(module_name) is None:
            raise RuntimeError(
                "Falta el paquete Windows Runtime. Instala "
                "winrt-Windows.Services.Store compatible con Media Flow."
            )

        StoreContext = importlib.import_module(module_name).StoreContext
        self._store_context = StoreContext.get_default()
        return self._store_context

    async def _get_add_on(self) -> Any | None:
        context = self._get_context()
        result = await context.get_store_products_async(
            ["Durable"],
            [self.product_id],
        )

        products = getattr(result, "products", {})
        product_values = products.values() if hasattr(products, "values") else products

        for product in product_values:
            store_id = getattr(product, "store_id", "")
            if store_id == self.product_id:
                return product

        return None

    async def _is_owned_async(self) -> bool:
        product = await self._get_add_on()
        if product is None:
            return False

        # StoreProduct exposes durable add-on ownership through this property.
        # Checking it prevents a local setting from granting PRO access.
        if hasattr(product, "is_in_user_collection"):
            return bool(product.is_in_user_collection)

        # Keep compatibility with WinRT projections that expose a license
        # object instead of is_in_user_collection.
        license_obj = getattr(product, "license", None)
        if license_obj is not None:
            return bool(getattr(license_obj, "is_active", False))

        # Some WinRT projections expose the license through the product's
        # package/license object differently. If no license is exposed, do
        # not grant PRO locally.
        return False

    @staticmethod
    def _run_sync(coroutine: Any) -> Any:
        """Run a WinRT coroutine without conflicting with an existing event loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)

        result: list[Any] = []
        error: list[BaseException] = []

        def worker() -> None:
            try:
                result.append(asyncio.run(coroutine))
            except BaseException as exc:
                error.append(exc)

        import threading

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join()
        if error:
            raise error[0]
        return result[0]

    def is_pro_owned(self) -> bool:
        try:
            return bool(self._run_sync(self._is_owned_async()))
        except Exception:
            return False

    async def _purchase_async(self) -> bool:
        product = await self._get_add_on()
        if product is None:
            raise RuntimeError(
                f"No se encontró el complemento PRO {self.product_id} en Microsoft Store."
            )

        license_obj = getattr(product, "license", None)
        if license_obj is not None and getattr(license_obj, "is_active", False):
            return True

        context = self._get_context()
        result = await context.request_purchase_async(self.product_id)
        status = getattr(result, "status", None)
        status_name = str(status).lower()

        # WinRT enum values differ between projections; accept the documented
        # succeeded status without relying on a numeric enum value.
        if "succeeded" in status_name:
            return True
        if "already" in status_name or "purchased" in status_name:
            return True

        # Verify ownership after the purchase request instead of trusting a
        # local flag.
        return await self._is_owned_async()

    def purchase_pro(self) -> bool:
        return bool(self._run_sync(self._purchase_async()))

    def open_store_page(self) -> None:
        """Open the Microsoft Store listing for the PRO add-on."""
        import webbrowser
        webbrowser.open(f"ms-windows-store://pdp/?productid={self.product_id}")
