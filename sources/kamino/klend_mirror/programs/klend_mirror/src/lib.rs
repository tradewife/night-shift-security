use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount, Transfer};

declare_id!("G9cZAWjKwksrb2fRxD3DxULMn6o6r4BhhxXNxxdXfrnA");

pub const LENDING_MARKET_SIZE: usize = 8 + 32 + 32 + 32 + 256;
pub const RESERVE_SIZE: usize = 8 + 32 * 4 + 8 * 2 + 32 + 8 + 8 + 32 + 8 + 8;

#[account]
pub struct LendingMarket {
    pub owner: Pubkey,
    pub quote_currency: [u8; 32],
    pub lending_market_authority: Pubkey,
    pub lending_market_authority_bump: u8,
    pub padding: [u8; 256],
}

#[account]
pub struct Reserve {
    pub lending_market: Pubkey,
    pub liquidity_mint: Pubkey,
    pub liquidity_supply: Pubkey,
    pub fee_receiver: Pubkey,
    pub collateral_mint: Pubkey,
    pub collateral_supply: Pubkey,
    pub collateral_mint_authority_bump: u8,
    pub authority_bump: u8,
    pub flash_loan_fee_bps: u16,
    pub total_liquidity: u64,
    pub collected_fees: u64,
    pub last_fees_ts: i64,
    pub padding: [u8; 32],
}

#[program]
pub mod klend_mirror {
    use super::*;

    pub fn init_lending_market(ctx: Context<InitLendingMarket>, quote_currency: [u8; 32]) -> Result<()> {
        let market = &mut ctx.accounts.lending_market;
        market.owner = ctx.accounts.signer.key();
        market.quote_currency = quote_currency;
        let (auth, bump) = Pubkey::find_program_address(
            &[b"lma", ctx.accounts.lending_market.key().as_ref()],
            ctx.program_id,
        );
        market.lending_market_authority = auth;
        market.lending_market_authority_bump = bump;
        Ok(())
    }

    pub fn init_reserve(ctx: Context<InitReserve>) -> Result<()> {
        let reserve = &mut ctx.accounts.reserve;
        reserve.lending_market = ctx.accounts.lending_market.key();
        reserve.liquidity_mint = ctx.accounts.liquidity_mint.key();
        reserve.liquidity_supply = ctx.accounts.reserve_liquidity_supply.key();
        reserve.fee_receiver = ctx.accounts.fee_receiver.key();
        reserve.collateral_mint = ctx.accounts.reserve_collateral_mint.key();
        reserve.collateral_supply = ctx.accounts.reserve_collateral_supply.key();
        reserve.flash_loan_fee_bps = 9; // 9 bps mirror default
        reserve.total_liquidity = 0;
        reserve.collected_fees = 0;
        reserve.last_fees_ts = 0;
        Ok(())
    }

    /// Flash-borrow exactly `amount` of underlying tokens out of the reserve's supply vault to
    /// `user_destination`. Caller must invoke `flash_repay_reserve_liquidity` in the same tx.
    pub fn flash_borrow(ctx: Context<FlashBorrow>, amount: u64) -> Result<()> {
        let reserve_key = ctx.accounts.reserve.key();
        let supply_seeds: &[&[u8]] = &[
            b"reserve_liq_supply",
            reserve_key.as_ref(),
            &[ctx.bumps.reserve_liquidity_supply],
        ];
        let signer_seeds = &[supply_seeds];
        let cpi_accounts = Transfer {
            from: ctx.accounts.reserve_liquidity_supply.to_account_info(),
            to: ctx.accounts.user_destination.to_account_info(),
            authority: ctx.accounts.lending_market_authority.to_account_info(),
        };
        let cpi_program = ctx.accounts.token_program.to_account_info();
        let cpi_ctx = CpiContext::new_with_signer(cpi_program, cpi_accounts, signer_seeds);
        token::transfer(cpi_ctx, amount)?;
        let reserve = &mut ctx.accounts.reserve;
        reserve.total_liquidity = reserve
            .total_liquidity
            .checked_sub(amount)
            .ok_or(error!(MirrorError::InsufficientLiquidity))?;
        Ok(())
    }

    /// Repay principal + flash-loan fee in the same tx to keep reserves whole.
    pub fn flash_repay(ctx: Context<FlashRepay>, amount: u64) -> Result<()> {
        let reserve_key = ctx.accounts.reserve.key();
        let fee = amount
            .checked_mul(ctx.accounts.reserve.flash_loan_fee_bps as u64)
            .and_then(|v| v.checked_div(10_000))
            .ok_or(error!(MirrorError::Math))?;
        let repay_total = amount
            .checked_add(fee)
            .ok_or(error!(MirrorError::Math))?;
        let cpi_accounts = Transfer {
            from: ctx.accounts.user_source.to_account_info(),
            to: ctx.accounts.reserve_liquidity_supply.to_account_info(),
            authority: ctx.accounts.user_transfer_authority.to_account_info(),
        };
        let cpi_program = ctx.accounts.token_program.to_account_info();
        let cpi_ctx = CpiContext::new(cpi_program, cpi_accounts);
        token::transfer(cpi_ctx, repay_total)?;
        // Split fee into fee_receiver for accounting.
        if fee > 0 {
            let supply_seeds: &[&[u8]] = &[
                b"fee_receiver",
                reserve_key.as_ref(),
                &[ctx.bumps.fee_receiver],
            ];
            let signer_seeds = &[supply_seeds];
            let cpi_accounts = Transfer {
                from: ctx.accounts.reserve_liquidity_supply.to_account_info(),
                to: ctx.accounts.fee_receiver.to_account_info(),
                authority: ctx.accounts.lending_market_authority.to_account_info(),
            };
            let cpi_program = ctx.accounts.token_program.to_account_info();
            let cpi_ctx = CpiContext::new_with_signer(cpi_program, cpi_accounts, signer_seeds);
            token::transfer(cpi_ctx, fee)?;
        }
        let reserve = &mut ctx.accounts.reserve;
        reserve.total_liquidity = reserve
            .total_liquidity
            .checked_add(amount)
            .ok_or(error!(MirrorError::Math))?;
        reserve.collected_fees = reserve
            .collected_fees
            .checked_add(fee)
            .ok_or(error!(MirrorError::Math))?;
        Ok(())
    }

    /// `update_reserve` - extension hook used in some KLend forks. Mirrors the empty
    /// default-reserve configuration so the harness can deposit liquidity before running
    /// flash borrows. Anyone can call (the production program gates by global_admin).
    pub fn update_reserve(ctx: Context<UpdateReserve>) -> Result<()> {
        Ok(())
    }

    /// Admin-only escape hatch used by harness `exploit-drain-fee` strategy.
    /// Drains the entire protocol fee vault in a single instruction to verify
    /// that the harness *can* observe when invariants are violated; this is the
    /// adversarial control surface for empty-reserve strategies.
    pub fn admin_drain_fee_vault(ctx: Context<AdminDrain>) -> Result<()> {
        let amount = ctx.accounts.fee_receiver.amount;
        let supply_seeds: &[&[u8]] = &[
            b"fee_receiver",
            ctx.accounts.reserve.key().as_ref(),
            &[ctx.bumps.fee_receiver],
        ];
        let signer_seeds = &[supply_seeds];
        let cpi_accounts = Transfer {
            from: ctx.accounts.fee_receiver.to_account_info(),
            to: ctx.accounts.admin_destination.to_account_info(),
            authority: ctx.accounts.lending_market_authority.to_account_info(),
        };
        let cpi_program = ctx.accounts.token_program.to_account_info();
        let cpi_ctx = CpiContext::new_with_signer(cpi_program, cpi_accounts, signer_seeds);
        token::transfer(cpi_ctx, amount)?;
        Ok(())
    }
}

#[derive(Accounts)]
pub struct InitLendingMarket<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    #[account(init, payer = signer, space = 8 + LENDING_MARKET_SIZE + 256)]
    pub lending_market: Account<'info, LendingMarket>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct InitReserve<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    pub lending_market: Account<'info, LendingMarket>,
    #[account(init, payer = signer, space = RESERVE_SIZE)]
    pub reserve: Account<'info, Reserve>,
    pub liquidity_mint: Account<'info, Mint>,
    /// CHECK: PDA derived from ["reserve_liq_supply", reserve_key]
    #[account(mut, seeds = [b"reserve_liq_supply", reserve.key.as_ref()], bump)]
    pub reserve_liquidity_supply: AccountInfo<'info>,
    /// CHECK: PDA derived from ["fee_receiver", reserve_key]
    #[account(mut, seeds = [b"fee_receiver", reserve.key.as_ref()], bump)]
    pub fee_receiver: AccountInfo<'info>,
    pub reserve_collateral_mint: AccountInfo<'info>,
    pub reserve_collateral_supply: AccountInfo<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct FlashBorrow<'info> {
    #[account(mut)]
    pub user_transfer_authority: Signer<'info>,
    /// CHECK: derived
    pub lending_market_authority: AccountInfo<'info>,
    pub lending_market: Account<'info, LendingMarket>,
    #[account(mut)]
    pub reserve: Account<'info, Reserve>,
    pub liquidity_mint: Account<'info, Mint>,
    #[account(mut, seeds = [b"reserve_liq_supply", reserve.key.as_ref()], bump)]
    pub reserve_liquidity_supply: AccountInfo<'info>,
    #[account(mut)]
    pub user_destination: Account<'info, TokenAccount>,
    pub fee_receiver: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct FlashRepay<'info> {
    #[account(mut)]
    pub user_transfer_authority: Signer<'info>,
    /// CHECK: derived
    pub lending_market_authority: AccountInfo<'info>,
    pub lending_market: Account<'info, LendingMarket>,
    #[account(mut)]
    pub reserve: Account<'info, Reserve>,
    #[account(mut, seeds = [b"reserve_liq_supply", reserve.key.as_ref()], bump)]
    pub reserve_liquidity_supply: AccountInfo<'info>,
    #[account(mut)]
    pub user_source: Account<'info, TokenAccount>,
    pub fee_receiver: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct UpdateReserve<'info> {
    pub lending_market: Account<'info, LendingMarket>,
    #[account(mut, has_one = lending_market)]
    pub reserve: Account<'info, Reserve>,
}

#[derive(Accounts)]
pub struct AdminDrain<'info> {
    pub lending_market: Account<'info, LendingMarket>,
    #[account(has_one = lending_market)]
    pub reserve: Account<'info, Reserve>,
    #[account(mut, seeds = [b"fee_receiver", reserve.key.as_ref()], bump)]
    pub fee_receiver: Account<'info, TokenAccount>,
    /// CHECK: market authority PDA
    pub lending_market_authority: AccountInfo<'info>,
    #[account(mut)]
    pub admin_destination: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[error_code]
pub enum MirrorError {
    #[msg("Insufficient reserve liquidity")]
    InsufficientLiquidity,
    #[msg("Math overflow")]
    Math,
}
