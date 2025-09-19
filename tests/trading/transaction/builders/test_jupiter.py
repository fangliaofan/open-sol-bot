import pytest
from unittest.mock import AsyncMock, MagicMock
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from trading.transaction.builders.jupiter import JupiterTransactionBuilder
from trading.swap import SwapDirection, SwapInType

@pytest.mark.asyncio
async def test_build_swap_transaction_sell_pct():
    # Arrange
    mock_rpc_client = AsyncMock(spec=AsyncClient)
    builder = JupiterTransactionBuilder(mock_rpc_client)

    mock_keypair = Keypair()
    token_address = "So11111111111111111111111111111111111111112"
    ui_amount = 50  # 50%
    slippage_bps = 100

    # Mock the dependencies
    builder.jupiter_client = AsyncMock()
    builder.wallet_cache = AsyncMock()
    builder.token_info_cache = AsyncMock()

    # Mock return values
    mock_token_info = MagicMock()
    mock_token_info.decimals = 6
    builder.token_info_cache.get.return_value = mock_token_info

    builder.wallet_cache.get_token_balance.return_value = (10, 6)  # 10 tokens with 6 decimals
    builder.jupiter_client.get_swap_transaction.return_value = {"swapTransaction": "mock_tx"}

    # Act
    await builder.build_swap_transaction(
        keypair=mock_keypair,
        token_address=token_address,
        ui_amount=ui_amount,
        swap_direction=SwapDirection.Sell,
        slippage_bps=slippage_bps,
        in_type=SwapInType.Pct,
    )

    # Assert
    builder.wallet_cache.get_token_balance.assert_called_once_with(
        wallet=mock_keypair.pubkey(), token_mint=token_address
    )

    expected_amount = int(10 * (50 / 100) * 10**6)
    builder.jupiter_client.get_swap_transaction.assert_called_once()
    call_args = builder.jupiter_client.get_swap_transaction.call_args
    assert call_args.kwargs["amount"] == expected_amount
