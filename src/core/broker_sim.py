"""Broker simulator with margin, spread, commission."""


class BrokerSim:
    """Simulate broker conditions."""

    def __init__(self, leverage: int = 100, spread_points: float = 20.0,
                 commission_per_lot: float = 7.0, contract_size: int = 100,
                 spread_multiplier: float = 0.01):
        """
        Args:
            leverage: Leverage (e.g., 100 for 1:100)
            spread_points: Spread in points
            commission_per_lot: Round turn commission per lot
            contract_size: Contract size (100 oz for XAUUSD, 1 for indices)
            spread_multiplier: Multiplier for spread (0.01 for XAUUSD, 1.0 for US30)
        """
        self.leverage = leverage
        self.spread = spread_points * spread_multiplier
        self.commission_per_lot = commission_per_lot
        self.contract_size = contract_size

    def calculate_margin_required(self, lot_size: float, price: float) -> float:
        """Calculate required margin for position."""
        margin = (lot_size * self.contract_size * price) / self.leverage
        return margin

    def calculate_commission(self, lot_size: float) -> float:
        """Calculate commission for trade."""
        return lot_size * self.commission_per_lot

    def apply_spread(self, price: float, direction: str) -> float:
        """Apply spread to entry price."""
        if direction == 'BUY':
            return price + self.spread
        else:  # SELL
            return price - self.spread

    def can_open_position(self, balance: float, equity: float, used_margin: float,
                         lot_size: float, price: float) -> bool:
        """Check if position can be opened."""
        margin_required = self.calculate_margin_required(lot_size, price)
        free_margin = equity - used_margin

        return free_margin >= margin_required
