import base64
import time

from solana.rpc.async_api import AsyncClient
from solbot_cache import get_latest_blockhash
from solbot_common.config import settings
from solbot_common.constants import SOL_DECIMAL
from solbot_common.log import logger
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price  # type: ignore
from solders.keypair import Keypair  # type: ignore
from solders.message import MessageV0  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.signature import Signature  # type: ignore
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction  # type: ignore

from trading.utils import calc_tx_units, calc_tx_units_and_split_fees


async def sign_transaction_from_raw(
    raw_tx: str,
    keypair: Keypair,
) -> VersionedTransaction:
    # Decode base64 raw transaction
    tx_bytes = base64.b64decode(raw_tx)

    # Deserialize instructions from bytes
    message = VersionedTransaction.from_bytes(tx_bytes).message

    # Create and sign transaction
    txn = VersionedTransaction(message, [keypair])
    return txn


async def build_transaction(
    keypair: Keypair,
    instructions: list,
    use_jito: bool | None = None,
    compute_unit_price_micro_lamports: int | None = None,
) -> VersionedTransaction:
    """Build transaction with instructions.

    Args:
        keypair (Keypair): Keypair of the transaction signer
        instructions (list): List of instructions to include in the transaction
        use_jito (bool): Whether to use Jito or not
        compute_unit_price_micro_lamports (int): The compute unit price in micro lamports

    Returns:
        VersionedTransaction: The built transaction
    """
    if compute_unit_price_micro_lamports is not None:
        unit_price = compute_unit_price_micro_lamports
        logger.info(f"Using custom compute unit price: {unit_price}")
    else:
        unit_price = settings.trading.unit_price
        logger.info(f"Using default compute unit price: {unit_price}")

    unit_limit = settings.trading.unit_limit
    instructions.insert(0, set_compute_unit_limit(unit_limit))
    instructions.insert(1, set_compute_unit_price(unit_price))

    # init tx
    recent_blockhash, _ = await get_latest_blockhash()

    message = MessageV0.try_compile(
        payer=keypair.pubkey(),
        instructions=instructions,
        recent_blockhash=recent_blockhash,
        address_lookup_table_accounts=[],
    )

    txn = VersionedTransaction(message, [keypair])
    return txn


async def new_signed_and_send_transaction(
    client: AsyncClient,
    keypair: Keypair,
    instructions: list,
    use_jito: bool,
) -> Signature:
    if not use_jito:
        instructions.insert(0, set_compute_unit_limit(settings.trading.unit_limit))
        instructions.insert(1, set_compute_unit_price(settings.trading.unit_price))

    # init tx
    recent_blockhash, _ = await get_latest_blockhash()

    message = MessageV0.try_compile(
        payer=keypair.pubkey(),
        instructions=instructions,
        recent_blockhash=recent_blockhash,
        address_lookup_table_accounts=[],
    )

    txn = VersionedTransaction(message, [keypair])

    if settings.trading.tx_simulate is True:
        resp = await client.simulate_transaction(txn)
        if resp.value.err is not None:
            raise Exception(resp.value.err)

    start_time = time.time()
    if use_jito is True:
        raise NotImplementedError("Jito is not implemented yet")
    else:
        resp = await client.send_transaction(txn)
        sig = resp.value
        logger.info(f"Transaction Sent: {sig}")
    logger.info(f"Transaction elapsed: {time.time() - start_time}")
    return sig
