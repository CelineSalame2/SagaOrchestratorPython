import httpx
import traceback
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, Callable, Union, Optional


class SagaError(Exception):
    def __init__(
        self,
        failed_step_index: int,
        action_exception: Exception,
        action_traceback: str,
        compensation_exception_tracebacks: dict[int, tuple[Exception, str]],
    ):
        self.failed_step_index = failed_step_index
        self.action_exception = action_exception
        self.action_traceback = action_traceback
        self.compensation_exception_tracebacks = compensation_exception_tracebacks

    def __str__(self):
        header_msg = 'A critical error occurred during the saga execution, leading to transaction failure and compensation attempts.'
        error_detail_msg = (
            f'Transaction failed at step index {self.failed_step_index}: '
            f'An unexpected {type(self.action_exception).__name__} occurred, triggering the compensation process.'
            f'\n{self.format_traceback_indentation(self.action_traceback, 2)}'
        )
        compensation_error_msgs = ''

        if any(self.compensation_exception_tracebacks.values()):
            compensation_error_msgs = 'Compensations encountered errors:\n' + '\n'.join(
                [
                    f'  - (step index {step}): Compensation failed due to a {type(exc).__name__}: {exc}'
                    f'\n{self.format_traceback_indentation(traceback_str, 6)}'
                    for step, (exc, traceback_str) in self.compensation_exception_tracebacks.items()
                ]
            )

        return '\n\n'.join([header_msg, error_detail_msg, compensation_error_msgs]).strip()

    def format_traceback_indentation(self, traceback_str: str, indent: int = 2) -> str:
        """Formats a traceback string by adding indentation to each line."""
        if '\n' in traceback_str:
            return '\n'.join([' ' * indent + '╎' + line for line in traceback_str.splitlines()])
        else:
            return traceback_str


@dataclass
class Action:
    action: Callable[..., Any]
    compensation: Callable[..., Any]
    compensation_args: Optional[Union[tuple, list]] = None
    result: Any = None

    async def act(self, *args):
        result = self.action(*(args if self.action.__code__.co_varnames else []))
        if isawaitable(result):
            result = await result
        return result

    async def compensate(self):
        result = self.compensation(
            *(self.compensation_args if self.compensation.__code__.co_varnames else [])
        )
        if isawaitable(result):
            result = await result
        return result


@dataclass
class Saga:
    steps: list[Action]

    async def execute(self):
        args = []
        for index, action in enumerate(self.steps):
            if isinstance(action, Action):
                try:
                    actioned_result = await action.act(*args)
                    if actioned_result is None:
                        args = []
                    elif isinstance(actioned_result, (list, tuple)):
                        args = actioned_result
                    else:
                        args = (actioned_result,)
                    action.compensation_args = args
                    action.result = actioned_result
                except Exception as exc:
                    action_traceback_str = traceback.format_exc()
                    compensation_exceptions = await self._run_compensations(index)
                    raise SagaError(index, exc, action_traceback_str, compensation_exceptions)

        return self

    async def _run_compensations(self, last_action_index: int) -> dict[int, tuple[Exception, str]]:
        compensation_exceptions = {}
        for compensation_index in range(last_action_index - 1, -1, -1):
            try:
                action = self.steps[compensation_index]
                await action.compensate()
            except Exception as exc:
                _, _, traceback_str = traceback.format_exc().partition(
                    'During handling of the above exception, another exception occurred:\n\n'
                )
                compensation_exceptions[compensation_index] = (exc, traceback_str)

        return compensation_exceptions


class UserCommandOrchestrator:
    """
    Orchestrates the steps of the saga, integrating with various APIs.
    Each step will be a separate API call.
    """

    def __init__(self):
        self.steps: list[Action] = []

    def add_step(self, action: Callable[..., Any], compensation: Callable[..., Any]) -> 'UserCommandOrchestrator':
        action_ = Action(action, compensation)
        self.steps.append(action_)
        return self

    async def execute(self) -> Saga:
        return await Saga(self.steps).execute()


# Hypothetical API Functions
async def create_order():
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.example.com/orders", json={"order_details": "details_here"})
        response.raise_for_status()  # Raise an error if the status code is not 200
        print("Order Created")
        return response.json()  # Return the API response data


async def validate_payment():
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.example.com/payments", json={"payment_data": "data_here"})
        response.raise_for_status()
        print("Payment Validated")
        return response.json()


async def update_inventory():
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.example.com/inventory", json={"inventory_data": "data_here"})
        response.raise_for_status()
        print("Inventory Updated")
        return response.json()


async def ship_order():
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.example.com/shipping", json={"shipping_data": "data_here"})
        response.raise_for_status()
        print("Order Shipped")
        return response.json()


# Compensation Functions
async def cancel_order(order):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"https://api.example.com/orders/{order['order_id']}/cancel")
        response.raise_for_status()
        print(f"Order {order['order_id']} Cancelled")


async def cancel_payment(payment):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"https://api.example.com/payments/{payment['payment_id']}/refund")
        response.raise_for_status()
        print(f"Payment {payment['payment_id']} Refunded")


async def rollback_inventory(inventory):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"https://api.example.com/inventory/{inventory['inventory_id']}/rollback")
        response.raise_for_status()
        print(f"Inventory Rollback {inventory['inventory_id']}")


async def rollback_shipping(shipping):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"https://api.example.com/shipping/{shipping['shipping_id']}/rollback")
        response.raise_for_status()
        print(f"Shipping Rollback {shipping['shipping_id']}")


# Usage Example
async def run_saga():
    orchestrator = UserCommandOrchestrator()

    # Add steps to the orchestrator
    orchestrator.add_step(create_order, cancel_order)  # create order step
    orchestrator.add_step(validate_payment, cancel_payment)  # validate payment step
    orchestrator.add_step(update_inventory, rollback_inventory)  # update inventory step
    orchestrator.add_step(ship_order, rollback_shipping)  # ship order step

    # Execute the saga
    try:
        saga = await orchestrator.execute()
    except SagaError as e:
        print(f"Saga failed: {e}")


# Run the saga (this would be done in an async environment)
# await run_saga()
