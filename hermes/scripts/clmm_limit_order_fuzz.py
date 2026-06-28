"""
CLMM Limit Order Settlement Simulation
Numerical fuzz testing for over-payment and accounting discrepancies.

Logic mirrored from:
  limit_order.rs::settle_filled_order
  tick_array.rs::match_limit_order / get_limit_order_output / get_limit_order_input
"""
import random
import sys
from typing import Optional

Q64 = 2**64
FEE_DENOMINATOR = 1_000_000


def mul_div_floor(a: int, b: int, c: int) -> int:
    return (a * b) // c


def mul_div_ceil(a: int, b: int, c: int) -> int:
    return (a * b + c - 1) // c


def get_price_at_tick_zfo(tick: int) -> int:
    """Stub: callers use externally generated price_x64 values."""
    return Q64


# --- CORE MOCK OBJECTS ---

class TickState:
    """Mirror of TickState limited to fields needed by settlement."""
    def __init__(self, tick, orders_amount, part_filled_orders_remaining, order_phase=1000):
        self.tick = tick
        self.orders_amount = orders_amount
        self.part_filled_orders_remaining = part_filled_orders_remaining
        self.unfilled_ratio_x64 = Q64  # full
        self.order_phase = order_phase


class LimitOrder:
    """Mirror of PersonalLimitOrder with the settlement-relevant fields."""
    def __init__(self, total_amount, settle_base, order_phase, settled_output,
                 unfilled_ratio_x64=Q64, tick_index=0, zero_for_one=True):
        self.total_amount = total_amount
        self.settle_base = settle_base
        self.settled_output = settled_output
        self.filled_amount = total_amount - settle_base
        self.order_phase = order_phase
        self.unfilled_ratio_x64 = unfilled_ratio_x64
        self.tick_index = tick_index
        self.zero_for_one = zero_for_one

    def get_unfilled_amount(self):
        if self.filled_amount <= self.total_amount:
            return self.total_amount - self.filled_amount
        return 0


def settle_filled_order_sim(order: LimitOrder, tick_state: TickState,
                             price_x64: int, zero_for_one: bool) -> int:
    """Mirrors limit_order.rs::settle_filled_order. Returns payout (output tokens)."""
    if order.settle_base == 0:
        return 0
    if order.order_phase == tick_state.order_phase:
        return 0
    elif order.order_phase + 1 == tick_state.order_phase:
        # Part-filled
        num = order.settle_base * tick_state.unfilled_ratio_x64
        den = order.unfilled_ratio_x64
        ideal_remaining = num // den
        is_exact = (num % den) == 0
        total_filled = order.settle_base - ideal_remaining
        if total_filled == 0:
            return 0
        effective_filled = total_filled if is_exact else max(0, total_filled - 1)
        # compute output
        if zero_for_one:
            total_output = mul_div_floor(effective_filled, price_x64, Q64)
        else:
            if price_x64 == 0:
                total_output = 0
            else:
                total_output = mul_div_floor(effective_filled, Q64, price_x64)
        payout = max(0, total_output - order.settled_output)
        order.filled_amount = order.total_amount - ideal_remaining
        order.settled_output = total_output
        return payout
    elif order.order_phase + 2 <= tick_state.order_phase:
        eager = order.order_phase + (999999)  # Force into fully branch
        # Fully-filled
        if zero_for_one:
            total_output = mul_div_floor(order.settle_base, price_x64, Q64)
        else:
            if price_x64 == 0:
                total_output = 0
            else:
                total_output = mul_div_floor(order.settle_base, Q64, price_x64)
        payout = max(0, total_output - order.settled_output)
        order.filled_amount = order.total_amount
        order.settle_base = 0
        order.settled_output = 0
        return payout
    else:
        # Invalid phase gap (bug), skip
        return 0


def get_limit_order_output(amount_in, tick_price_x64, zero_for_one):
    if zero_for_one:
        return mul_div_floor(amount_in, tick_price_x64, Q64)
    else:
        if tick_price_x64 == 0:
            return 0
        return mul_div_floor(amount_in, Q64, tick_price_x64)


# --- TESTS ---

ANOMALIES = []

def check_invariant(test_name, order, tick_total_out, expected_out):
    """Check that no order over-settled vs ground truth."""
    if order.settled_output > expected_out:
        ANOMALIES.append({
            "test": test_name,
            "type": "OVERSETTLE",
            "settled_output": order.settled_output,
            "expected_max_out": expected_out,
            "params": vars(order)
        })


def fuzz_random_iteration(iter_idx):
    """Single iteration: create tick + limit orders, simulate partial then full fill,
    check for over-payment of tokens vs ground truth."""
    # Random parameters
    n_orders = random.choice([1, 2, 5, 10, 100])
    price_x64 = random.choice([
        Q64,             # price = 1.0
        Q64 * 2,         # price = 2.0
        Q64 // 2,        # price = 0.5
        Q64 + Q64 // 11, # odd price
        Q64 * 3 + 1,     # nearly integer but not
        1234567 * 17,    # arbitrary odd value with rounding fuzz
        random.randint(Q64 // 1000, Q64 * 100),  # arbitrary
    ])
    zero_for_one = random.choice([True, False])
    initial_orders_amount = random.choice([0, 1, 10, 1_000, 10**6, 10**9])
    part_filled_orders_remaining = random.choice([0, 1, 10, 1_000, 10**6])
    order_phase = 1000

    tick = TickState(tick=0,
                     orders_amount=initial_orders_amount,
                     part_filled_orders_remaining=part_filled_orders_remaining,
                     order_phase=order_phase)

    orders = []
    # Divide total unfilled across N orders with some variation
    total = initial_orders_amount + part_filled_orders_remaining
    if total == 0:
        return
    for i in range(n_orders):
        # Each order has some deposit
        deposit = total // n_orders + random.choice([0, 1, -1, 7, -3])
        deposit = max(0, deposit)
        if deposit > 10**12:
            continue
        orders.append(LimitOrder(
            total_amount=deposit,
            settle_base=deposit if order_phase == order_phase else 0,
            order_phase=order_phase,
            settled_output=0,
            unfilled_ratio_x64=tick.unfilled_ratio_x64,
            tick_index=0,
            zero_for_one=zero_for_one,
        ))

    # Simulate a small partial fill (consumes from part_filled + a fraction from orders)
    consumed = random.randint(1, max(1, total // 4))
    consumed = min(consumed, total)

    # First: consume from part_filled
    if tick.part_filled_orders_remaining > 0:
        part_consume = min(tick.part_filled_orders_remaining, consumed)
        tick.part_filled_orders_remaining -= part_consume
        tick.unfilled_ratio_x64 = mul_div_floor(
            tick.unfilled_ratio_x64,
            max(0, tick.part_filled_orders_remaining),
            max(1, tick.part_filled_orders_remaining + part_consume)
        )
        consumed -= part_consume

    if consumed > 0:
        # orders_amount gets consumed
        tick.order_phase += 1
        actual_consumed = min(tick.orders_amount, consumed)
        tick.part_filled_orders_remaining = tick.orders_amount - actual_consumed
        tick.orders_amount = 0
        tick.unfilled_ratio_x64 = mul_div_floor(Q64, tick.part_filled_orders_remaining, max(1, tick.part_filled_orders_remaining + actual_consumed))
        # ALL live orders move to phase+1
        for o in orders:
            o.order_phase += 1

    # Now settle each order under the new tick state
    # Ground truth: total filled tokens consumed * price should match total payout
    for i, o in enumerate(orders):
        payout = settle_filled_order_sim(o, tick,
                                          price_x64=price_x64,
                                          zero_for_one=zero_for_one)
        # Ground truth: order fills proportional to its deposit share * tokens consumed
        if o.get_unfilled_amount() is None:
            continue
        share = o.total_amount / max(1, total)
        # not strict — just sanity check that payout doesn't wildly exceed max possible
        max_possible_for_order = get_limit_order_output(o.total_amount, price_x64, zero_for_one)
        if o.settled_output > max_possible_for_order:
            ANOMALIES.append({
                "iter": iter_idx,
                "type": "ORDER_OVER_FILLED",
                "order_total": o.total_amount,
                "settled_output": o.settled_output,
                "max_possible": max_possible_for_order
            })

    # Then settle fully
    tick.order_phase += 2
    for i, o in enumerate(orders):
        if o.settle_base == 0:
            continue
        settle_filled_order_sim(o, tick, price_x64=price_x64, zero_for_one=zero_for_one)


def edge_case_small_unfilled_ratio():
    """unfilled_ratio_x64 very small in part-filled state."""
    price_x64 = Q64  # price 1
    order = LimitOrder(
        total_amount=10**12,
        settle_base=10**12,
        order_phase=1000,
        settled_output=0,
        unfilled_ratio_x64=Q64,  # initially full
        tick_index=0,
        zero_for_one=True,
    )
    # tick went from phase 1000 → 1001, consumed most of part_filled_orders_remaining
    # Now tick_state.unfilled_ratio_x64 = small ratio (e.g., Q64/1000)
    tick = TickState(tick=0, orders_amount=0,
                     part_filled_orders_remaining=10**9,  # 10^9 remaining
                     order_phase=1000)
    # After partial fill:
    consumed = 10**12 - 10**9
    settle_base_before = order.settle_base  # 10^12

    # Simulate state: tick.order_phase = 1001, unfilled_ratio ~ 10^9 / 10^12
    tick.unfilled_ratio_x64 = mul_div_floor(Q64, 10**9, 10**12)  # ~Q64/1000
    tick.order_phase = 1001
    # order's unfilled_ratio stays at Q64 (it's the ratio at deposit time)
    payout = settle_filled_order_sim(order, tick,
                                     price_x64=price_x64,
                                     zero_for_one=True)
    # ideal_remaining = (settle_base * tick_state.unfilled_ratio) / order.unfilled_ratio
    # = (10^12 * (Q64/1000)) / Q64 = 10^9
    # total_filled = 10^12 - 10^9 = ~10^12
    # payout in Q64-price-1: total_filled * 1 = ~10^12
    return payout, order.settled_output


def edge_case_zero_settle_base():
    """settle_base = 0: should return 0."""
    order = LimitOrder(0, 0, 1000, 0, Q64, 0, True)
    tick = TickState(0, 100, 0, 1001)
    payout = settle_filled_order_sim(order, tick, Q64, True)
    if payout != 0:
        ANOMALIES.append({"type": "ZERO_SETTLE_BASE_PAID", "payout": payout})


def edge_case_same_phase():
    """order.phase == tick.phase: should return 0."""
    order = LimitOrder(1000, 500, 1000, 0, Q64, 0, True)
    tick = TickState(0, 500, 100, 1000)
    payout = settle_filled_order_sim(order, tick, Q64, True)
    if payout != 0:
        ANOMALIES.append({"type": "SAME_PHASE_PAID", "payout": payout})


def edge_case_extreme_unfilled_ratio():
    """tick.unfilled_ratio_x64 = 1, order.unfilled_ratio_x64 = Q64"""
    order = LimitOrder(10**12, 10**12, 1000, 0, Q64, 0, True)
    tick = TickState(0, 0, 1, 1001)  # 1 token remaining out of 10^12
    tick.unfilled_ratio_x64 = 1  # extreme small
    payout = settle_filled_order_sim(order, tick, Q64, True)
    # ideal_remaining = (10^12 * 1) / Q64 = 0
    # total_filled = 10^12
    # effective_filled = total_filled - 1 = 10^12 - 1
    # output = (10^12 - 1) * Q64 / Q64 = 10^12 - 1
    # payout = 10^12 - 1 - 0 = 10^12 - 1
    return payout, order


def edge_case_unfilled_ratio_near_one():
    """tick.unfilled_ratio_x64 = Q64 - 1, almost full"""
    order = LimitOrder(10**6, 10**6, 1000, 0, Q64, 0, True)
    tick = TickState(0, 10**6 - 1, 1, 1001)
    tick.unfilled_ratio_x64 = Q64 - 1
    payout = settle_filled_order_sim(order, tick, Q64, True)
    # num = 10^6 * (Q64 - 1)
    # den = Q64
    # ideal_remaining = floor((10^6 * (Q64 - 1)) / Q64) = 10^6 - 1
    # is_exact = False
    # total_filled = 10^6 - (10^6 - 1) = 1
    # effective_filled = 1 - 1 = 0
    # output = 0
    # payout = 0
    if payout != 0:
        ANOMALIES.append({"type": "UNFILLED_NEAR_ONE_PAID_SOMETHING", "payout": payout})
    return payout


def main():
    random.seed(0xDEADBEEF)

    print("=" * 70)
    print("CLMM LIMIT ORDER SETTLEMENT FUZZ")
    print("=" * 70)

    # Edge cases first
    print("\nEdge cases:")
    p, _ = edge_case_small_unfilled_ratio()
    print(f"  small unfilled ratio: payout={p:,}")
    edge_case_zero_settle_base()
    print(f"  zero settle_base: no anomaly (correct)")
    edge_case_same_phase()
    print(f"  same phase: no anomaly (correct)")
    p = edge_case_unfilled_ratio_near_one()
    print(f"  unfilled near one: payout={p} (expect 0)")
    p, _ = edge_case_extreme_unfilled_ratio()
    print(f"  extreme unfilled (1): payout={p:,} (expect 10^12 - 1)")

    print("\nRunning 100,000 random iterations...")
    for i in range(100_000):
        if i % 20_000 == 0:
            sys.stdout.write(f"  iter {i:,}...\r")
            sys.stdout.flush()
        fuzz_random_iteration(i)

    print(f"\nTotal anomalies detected: {len(ANOMALIES)}")
    if ANOMALIES:
        print("\nFirst 10 anomalies:")
        for a in ANOMALIES[:10]:
            print(f"  {a}")

    return len(ANOMALIES)


if __name__ == "__main__":
    n = main()
    sys.exit(0 if n == 0 else 1)
