from solana.rpc.async_api import AsyncClient
from solbot_cache.token_info import TokenInfoCache
from solbot_cache.wallet import WalletCache
from solbot_common.constants import SOL_DECIMAL, WSOL
from solbot_common.utils.jupiter import JupiterAPI
from solders.keypair import Keypair  # type: ignore
from solders.transaction import VersionedTransaction  # type: ignore

from trading.swap import SwapDirection, SwapInType
from trading.tx import sign_transaction_from_raw

from .base import TransactionBuilder


class JupiterTransactionBuilder(TransactionBuilder):
    """Jupiter 交易构建器"""

    def __init__(self, rpc_client: AsyncClient) -> None:
        super().__init__(rpc_client=rpc_client)
        self.token_info_cache = TokenInfoCache()
        self.jupiter_client = JupiterAPI()
        self.wallet_cache = WalletCache()

    async def build_swap_transaction(
        self,
        keypair: Keypair,
        token_address: str,
        ui_amount: float,
        swap_direction: SwapDirection,
        slippage_bps: int,
        in_type: SwapInType | None = None,
        use_jito: bool = False,
        compute_unit_price_micro_lamports: int | None = None,
    ) -> VersionedTransaction:
        """Build swap transaction with GMGN API.

        Args:
            token_address (str): token address
            amount_in (float): amount in
            swap_direction (SwapDirection): swap direction
            slippage (int): slippage, percentage
            in_type (SwapInType | None, optional): in type. Defaults to None.
            use_jto (bool, optional): use jto. Defaults to False.
            priority_fee (float | None, optional): priority fee. Defaults to None.

        Returns:
            VersionedTransaction: The built transaction ready to be signed and sent
        """
        if swap_direction == "sell" and in_type is None:
            raise ValueError("in_type must be specified when selling")

        if swap_direction == SwapDirection.Buy:
            token_in = str(WSOL)
            token_out = token_address
            amount = int(ui_amount * SOL_DECIMAL)
        elif swap_direction == SwapDirection.Sell:
            token_info = await self.token_info_cache.get(token_address)
            if token_info is None:
                raise ValueError("Token info not found")

            token_in = token_address
            token_out = str(WSOL)

            if in_type == SwapInType.Pct:
                balance, decimals = await self.wallet_cache.get_token_balance(
                    wallet=keypair.pubkey(), token_mint=token_address
                )
                amount = int(balance * (ui_amount / 100) * 10**decimals)
            else:
                decimals = token_info.decimals
                amount = int(ui_amount * 10**decimals)
        else:
            raise ValueError("swap_direction must be buy or sell")

        swap_tx_response = await self.jupiter_client.get_swap_transaction(
            input_mint=token_in,
            output_mint=token_out,
            user_publickey=str(keypair.pubkey()),
            amount=amount,
            slippage_bps=slippage_bps,
            use_jito=use_jito,
            compute_unit_price_micro_lamports=compute_unit_price_micro_lamports,
        )
        swap_tx = swap_tx_response["swapTransaction"]
        signed_tx = await sign_transaction_from_raw(swap_tx, keypair)
        return signed_tx
