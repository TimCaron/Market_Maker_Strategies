from dataclasses import dataclass

@dataclass
class Position:
    total_realized_pnl: float = 0.0  # total realized pnl in usd since start
    total_fee_paid: float = 0.0  # total fee paid in usd since start
    unrealized_pnl: float = 0.0  # in usd
    previous_entry_price: float = None  # entry price
    current_quantity: float = 0.0  # position quantity
    last_close_price: float = None  # last known close price

    def repr(self):
        return f'Position(size={self.current_quantity}, total_realized_pnl={self.total_realized_pnl}, unrealized_pnl={self.unrealized_pnl}, entry_price={self.previous_entry_price})'
    
    def execute_position_change(
        self,
        execution_price: float,
        old_position_size: float,
        updated_position_size: float,
        trade_size: float,
        fee_rate: float
    ) -> tuple[float, float]:
        """
        Update position state after trade and compute realized PnL and fees.

        Args:
            execution_price: The price at which the trade was executed.
            old_position_size: The position size before the trade.
            updated_position_size: The new position size after applying the trade.
            trade_size: Quantity of this trade (positive = buy, negative = sell).
            fee_rate: Fee rate applied to trade value.

        Returns:
            Tuple of (realized_pnl: float, fee_paid: float) where:
                - realized_pnl is the PnL from the trade excluding fees
                - fee_paid is the trading fee paid
        """
        trade_value = abs(trade_size * execution_price)
        fee_paid = trade_value * fee_rate # always positive if not maker rebate (negative fee rate)
        realized_pnl = 0.0 # Initialize PnL without fees

        # Pedestrian, but clear implementation of all possible position changes and average entry price changes
        # CASE 1: Flat → Long
        if old_position_size == 0 and updated_position_size > 0:
            self.previous_entry_price = execution_price

        # CASE 2: Flat → Short
        elif old_position_size == 0 and updated_position_size < 0:
            self.previous_entry_price = execution_price

        # CASE 3: Long → More Long
        elif old_position_size > 0 and updated_position_size > old_position_size:
            self.previous_entry_price = (
                self.previous_entry_price * old_position_size + execution_price * trade_size
            ) / updated_position_size

        # CASE 4: Long → Less Long or Flat
        elif old_position_size > 0 and updated_position_size < old_position_size and updated_position_size >=0:
            # trade_size is negative; you partially close a long position, so
            realized_pnl += abs(trade_size) * (execution_price - self.previous_entry_price) #positive qty * (exit price - entry price)
            if updated_position_size == 0:
                self.previous_entry_price = None

        # CASE 5: Long → Short (flip)
        elif old_position_size > 0 and updated_position_size < 0:
            #first full close long position
            realized_pnl += old_position_size * (execution_price - self.previous_entry_price)
            # then enter a short position
            self.previous_entry_price = execution_price  # new entry for short

        # CASE 6: Short → More Short
        elif old_position_size < 0 and updated_position_size < old_position_size:
            self.previous_entry_price = (
                self.previous_entry_price * abs(old_position_size) + execution_price * abs(trade_size)
            ) / abs(updated_position_size)

        # CASE 7: Short → Less Short or Flat
        elif old_position_size < 0 and updated_position_size > old_position_size and updated_position_size <= 0:
            # here trade_size is positive, you partially close a short position, so
            realized_pnl += abs(trade_size) * (self.previous_entry_price - execution_price)
            if updated_position_size == 0:
                self.previous_entry_price = None

        # CASE 8: Short → Long (flip)
        elif old_position_size < 0 and updated_position_size > 0:
            #first full close short position
            realized_pnl += abs(old_position_size) * (self.previous_entry_price - execution_price)
            self.previous_entry_price = execution_price  # new entry for long

        else:
            raise ValueError("Unhandled position change case.")

        self.current_quantity = updated_position_size
        return realized_pnl, fee_paid

    def update_unrealized_pnl(self, price: float) -> float:
        """Update unrealized PnL based on a given price"""
        if self.current_quantity == 0:
            self.unrealized_pnl = 0.0
        elif self.current_quantity > 0:  # long position
            self.unrealized_pnl = self.current_quantity * (price - self.previous_entry_price)
        else:  # short position
            self.unrealized_pnl = abs(self.current_quantity) * (self.previous_entry_price - price)
        return self.unrealized_pnl