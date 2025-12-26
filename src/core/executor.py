"""Trade executor - manages position lifecycle."""


class Position:
    """Single position."""

    def __init__(self, direction: str, entry_price: float, sl: float, tp: float,
                 lot_size: float, entry_time, commission: float):
        self.direction = direction
        self.entry_price = entry_price
        self.sl = sl
        self.tp = tp
        self.lot_size = lot_size
        self.entry_time = entry_time
        self.commission = commission
        self.exit_price = None
        self.exit_time = None
        self.pnl = 0.0
        self.exit_reason = None
        self.be_moved = False  # Track if SL moved to BE

    def update_sl_to_be(self, be_price: float):
        """Move SL to breakeven."""
        self.sl = be_price
        self.be_moved = True


class Executor:
    """Execute and manage trades."""

    def __init__(self, broker_sim, contract_size: int = 100):
        self.broker = broker_sim
        self.contract_size = contract_size
        self.position = None
        self.last_closed_position = None

    def has_position(self) -> bool:
        """Check if position is open."""
        return self.position is not None

    def open_position(self, signal: dict, lot_size: float, current_price: float,
                     current_time, balance: float, equity: float, used_margin: float) -> bool:
        """
        Try to open position.

        Returns:
            True if opened, False if rejected
        """
        # Check if can open
        if not self.broker.can_open_position(balance, equity, used_margin, lot_size, current_price):
            return False

        # Apply spread
        entry_price = self.broker.apply_spread(current_price, signal['direction'])

        # Calculate commission
        commission = self.broker.calculate_commission(lot_size)

        # Create position
        self.position = Position(
            direction=signal['direction'],
            entry_price=entry_price,
            sl=signal['sl'],
            tp=signal['tp'],
            lot_size=lot_size,
            entry_time=current_time,
            commission=commission
        )

        return True

    def update_position(self, current_price: float, current_time) -> dict:
        """
        Update position and check for exit.

        Returns:
            dict with 'closed' (bool) and 'pnl' (float)
        """
        if not self.position:
            return {'closed': False, 'pnl': 0.0}

        # Check SL/TP hit
        exit_triggered = False
        exit_reason = None

        if self.position.direction == 'BUY':
            if current_price <= self.position.sl:
                exit_triggered = True
                exit_reason = 'SL'
            elif current_price >= self.position.tp:
                exit_triggered = True
                exit_reason = 'TP'
        else:  # SELL
            if current_price >= self.position.sl:
                exit_triggered = True
                exit_reason = 'SL'
            elif current_price <= self.position.tp:
                exit_triggered = True
                exit_reason = 'TP'

        if exit_triggered:
            pnl = self._close_position(current_price, current_time, exit_reason)
            return {'closed': True, 'pnl': pnl}

        # Check for BE move
        if not self.position.be_moved:
            current_rr = self._calculate_current_rr(current_price)
            if current_rr >= 1.0:
                # Move SL to BE (entry price)
                self.position.update_sl_to_be(self.position.entry_price)

        return {'closed': False, 'pnl': 0.0}

    def _calculate_current_rr(self, current_price: float) -> float:
        """Calculate current risk-reward ratio."""
        risk = abs(self.position.entry_price - self.position.sl)
        if risk == 0:
            return 0.0

        if self.position.direction == 'BUY':
            current_profit = current_price - self.position.entry_price
        else:
            current_profit = self.position.entry_price - current_price

        return current_profit / risk

    def _close_position(self, exit_price: float, exit_time, reason: str) -> float:
        """Close position and calculate PnL."""
        self.position.exit_price = exit_price
        self.position.exit_time = exit_time
        self.position.exit_reason = reason

        # Calculate PnL
        if self.position.direction == 'BUY':
            price_diff = exit_price - self.position.entry_price
        else:
            price_diff = self.position.entry_price - exit_price

        pnl = (price_diff * self.contract_size * self.position.lot_size) - self.position.commission
        self.position.pnl = pnl

        # Save closed position before clearing
        self.last_closed_position = self.position

        # Clear position
        self.position = None

        return pnl

    def get_used_margin(self, current_price: float) -> float:
        """Get currently used margin."""
        if not self.position:
            return 0.0

        return self.broker.calculate_margin_required(self.position.lot_size, current_price)

    def get_floating_pnl(self, current_price: float) -> float:
        """Get floating PnL."""
        if not self.position:
            return 0.0

        if self.position.direction == 'BUY':
            price_diff = current_price - self.position.entry_price
        else:
            price_diff = self.position.entry_price - current_price

        return price_diff * self.contract_size * self.position.lot_size
