"""
State machine model for m_ext protocol.
Tests invariants: collateralization, value conservation, monotonicity.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

INDEX_SCALE = 1_000_000_000_000


def principal_down(amount: int, index: int) -> int:
    if index == INDEX_SCALE:
        return amount
    return amount * INDEX_SCALE // index


def principal_up(amount: int, index: int) -> int:
    if index == INDEX_SCALE:
        return amount
    return (amount * INDEX_SCALE + index - 1) // index


def amount_down(principal: int, index: int) -> int:
    if index == INDEX_SCALE:
        return principal
    return principal * index // INDEX_SCALE


def amount_up(principal: int, index: int) -> int:
    if index == INDEX_SCALE:
        return principal
    return (principal * index + INDEX_SCALE - 1) // INDEX_SCALE


def calc_new_ext(
    last_ext_index: int, last_m_index: int, new_m_index: int
) -> int:
    """Calculate new ext index (simplified, fee=0)."""
    return last_ext_index * new_m_index // last_m_index


@dataclass
class State:
    vault_raw: int = 0          # raw M tokens in vault
    ext_supply: int = 0         # raw EXT tokens minted
    m_index: int = INDEX_SCALE  # M multiplier
    ext_index: int = INDEX_SCALE  # EXT multiplier
    
    def vault_value(self) -> int:
        return amount_down(self.vault_raw, self.m_index)
    
    def ext_value(self) -> int:
        return amount_down(self.ext_supply, self.ext_index)
    
    def is_collateralized(self) -> bool:
        """EXT value must not exceed vault value."""
        return self.ext_value() <= self.vault_value()


def simulate():
    state = State(vault_raw=0, ext_supply=0)
    
    # User wraps 1000 M
    print("=== Initialize ===")
    print(f"vault={state.vault_raw}, ext_supply={state.ext_supply}")
    print(f"m_mult={state.m_index/INDEX_SCALE}x, ext_mult={state.ext_index/INDEX_SCALE}x")
    print(f"vault_value={state.vault_value()}, ext_value={state.ext_value()}")
    print(f"Collateralized: {state.is_collateralized()}")
    
    print("\n=== User wraps 1000 M ===")
    wrap_amount = 1000
    m_principal = principal_down(wrap_amount, state.m_index)
    ext_principal = principal_down(wrap_amount, state.ext_index)
    state.vault_raw += m_principal
    state.ext_supply += ext_principal
    print(f"  M deposited to vault: {m_principal} raw (worth {wrap_amount} UI)")
    print(f"  EXT minted: {ext_principal} raw")
    print(f"  vault_value={state.vault_value()}, ext_value={state.ext_value()}")
    print(f"  Collateralized: {state.is_collateralized()}")
    
    print("\n=== M grows 2x, sync advances ext_index ===")
    old_m = state.m_index
    state.m_index = 2 * INDEX_SCALE
    old_ext = state.ext_index
    state.ext_index = calc_new_ext(state.ext_index, old_m, state.m_index)
    print(f"  m_mult: 1.0 -> {state.m_index/INDEX_SCALE}x")
    print(f"  ext_index: {old_ext} -> {state.ext_index}")
    print(f"  vault_value={state.vault_value()}, ext_value={state.ext_value()}")
    print(f"  Collateralized: {state.is_collateralized()}")
    assert state.is_collateralized(), "FAIL: should be collateralized"
    
    print("\n=== Earn authority claims for earner ===")
    snapshot = ext_principal  # user's balance at last claim
    last_claim = INDEX_SCALE
    rewards = snapshot * state.ext_index // last_claim - snapshot
    print(f"  snapshot={snapshot}, last_claim={last_claim}, ext_index={state.ext_index}")
    print(f"  rewards = {snapshot} * {state.ext_index} / {last_claim} - {snapshot} = {rewards}")
    
    # Buggy check: ext_supply + rewards > vault_value?
    if state.ext_supply + rewards > state.vault_value():
        print(f"  Buggy check: REJECT (ext_supply={state.ext_supply} + rewards={rewards} > vault_value={state.vault_value()})")
    else:
        print(f"  Buggy check: PASS")
        new_ext_value = amount_down(state.ext_supply + rewards, state.ext_index)
        print(f"  EXT value after claim: {new_ext_value}")
        if new_ext_value > state.vault_value():
            print(f"  *** COLLATERALIZATION VIOLATION: ext_value={new_ext_value} > vault_value={state.vault_value()}")
        else:
            print(f"  Collateralized after claim: {new_ext_value} <= {state.vault_value()}")
    
    # Actually execute the claim
    ext_value_before = state.ext_value()
    state.ext_supply += rewards
    ext_value_after = state.ext_value()
    print(f"\n  After claim: vault_value={state.vault_value()}, ext_value_before={ext_value_before}, ext_value_after={ext_value_after}")
    print(f"  Collateralized: {state.is_collateralized()}")
    if not state.is_collateralized():
        print(f"  *** CRITICAL: Value leak of {ext_value_after - state.vault_value()}")
    
    print("\n=== Additional growth: M grows 3x more ===")
    old_m = state.m_index
    state.m_index = 3 * INDEX_SCALE
    state.ext_index = calc_new_ext(state.ext_index, old_m, state.m_index)
    print(f"  m_mult: 2.0 -> {state.m_index/INDEX_SCALE}x")
    print(f"  ext_index: -> {state.ext_index}")
    print(f"  vault_value={state.vault_value()}, ext_value={state.ext_value()}")
    print(f"  Collateralized: {state.is_collateralized()}")
    assert state.is_collateralized(), "FAIL: should be collateralized"
    
    print("\n=== Claim again (last_claim updated to ext_index) ===")
    last_claim = state.ext_index  # updated from previous claim
    # User's balance grew by previous rewards
    snapshot = ext_principal + rewards
    # Need MORE growth to trigger second claim
    old_m = state.m_index
    state.m_index = 4 * INDEX_SCALE
    state.ext_index = calc_new_ext(state.ext_index, old_m, state.m_index)
    rewards2 = snapshot * state.ext_index // last_claim - snapshot
    print(f"  snapshot={snapshot}, last_claim={last_claim}, ext_index={state.ext_index}")
    print(f"  rewards2 = {rewards2}")
    
    if state.ext_supply + rewards2 > state.vault_value():
        print(f"  Collateral check: REJECT (supply exceeds vault)")
    else:
        state.ext_supply += rewards2
        print(f"  After 2nd claim: ext_supply={state.ext_supply}, vault_value={state.vault_value()}")
        print(f"  Collateralized: {state.is_collateralized()}")
    
    print("\n=== Test: wrap at different ext_index levels ===")
    # Reset
    s = State(vault_raw=1_000_000_000_000, ext_supply=0)
    s.m_index = 2 * INDEX_SCALE
    
    for ext_mult in [1.0, 1.1, 1.5, 2.0, 5.0, 10.0]:
        s.ext_index = int(ext_mult * INDEX_SCALE)
        wrap_amount = 100_000_000
        m_principal = principal_down(wrap_amount, s.m_index)
        ext_principal = principal_down(wrap_amount, s.ext_index)
        s.vault_raw += m_principal
        s.ext_supply += ext_principal
        
        vault_val = s.vault_value()
        ext_val = amount_down(s.ext_supply, s.ext_index)
        ok = ext_val <= vault_val
        
        status = "OK" if ok else "LEAK!"
        print(f"  ext_mult={ext_mult:.1f}x: vault_value={vault_val}, ext_value={ext_val} [{status}]")
        
        # Unwrap back
        unwrap_amount = wrap_amount
        ext_burned = principal_down(unwrap_amount, s.ext_index)
        m_received = principal_down(unwrap_amount, s.m_index)
        s.vault_raw -= m_received
        s.ext_supply -= ext_burned
        
        vault_val_after = s.vault_value()
        ext_val_after = amount_down(s.ext_supply, s.ext_index)
        print(f"    Unwrap: vault={vault_val_after}, ext={ext_val_after}")
        
        if not ok:
            print(f"  *** Value leak detected at ext_mult={ext_mult}x!")
            print(f"  *** EXT value {ext_val} exceeds vault {vault_val}")

    print("\n=== Extreme test: vary m_index vs ext_index ===")
    s = State(vault_raw=0, ext_supply=0)
    s.m_index = INDEX_SCALE
    s.ext_index = INDEX_SCALE
    
    # Wrap at initial state
    wrap_amount = 1_000_000
    mp = principal_down(wrap_amount, s.m_index)
    ep = principal_down(wrap_amount, s.ext_index)
    s.vault_raw += mp
    s.ext_supply += ep
    
    print(f"  Initial wrap: vault={s.vault_raw}, ext={s.ext_supply}")
    print(f"  vault_value={s.vault_value()}, ext_value={s.ext_value()}")
    print(f"  Collateralized: {s.is_collateralized()}")
    
    # Multiple rounds of growth and wrap
    for i in range(5):
        old_m = s.m_index
        old_ext = s.ext_index
        s.m_index = int(s.m_index * 1.5)  # 50% growth
        s.ext_index = calc_new_ext(s.ext_index, old_m, s.m_index)
        
        # New user wraps
        wrap_amount = 1_000_000
        mp = principal_down(wrap_amount, s.m_index)
        ep = principal_down(wrap_amount, s.ext_index)
        s.vault_raw += mp
        s.ext_supply += ep
        
        ext_val = amount_down(s.ext_supply, s.ext_index)
        vault_val = amount_down(s.vault_raw, s.m_index)
        ok = ext_val <= vault_val
        
        print(f"  Round {i+1}: m={s.m_index/INDEX_SCALE:.3f}x ext={s.ext_index/INDEX_SCALE:.3f}x vault_val={vault_val} ext_val={ext_val} [{('OK' if ok else 'LEAK!')}]")
        
        if not ok:
            print(f"  *** BUG FOUND: ext value {ext_val} exceeds vault value {vault_val} by {ext_val - vault_val}")


if __name__ == "__main__":
    simulate()
