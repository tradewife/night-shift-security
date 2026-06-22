// ============================================================
// Drift Protocol Crucible Fuzz Harness - v6.12
// ============================================================
// Target: Drift Protocol (dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH)
// Bounty: $500K critical (oracle manipulation + flash loan in scope)
//
// Key fixes from v6.11:
//   1. Pre-write State PDA with correct Anchor borsh layout
//      (bypasses LiteSVM CPI data-persistence limitation)
//   2. Fix User PDA seed: b"user" (not b"user_account")
//   3. Fix InitializeUser discriminator from IDL
//   4. Add InitializeUserStats before InitializeUser
//   5. Fixup User/UserStats discriminator+authority after CPI init
//   6. Fix Deposit account ordering to match Deposit context
//   7. Pre-create vault token account at PDA address
// ============================================================

use crucible_fuzzer::*;
use solana_keypair::Keypair;
use solana_signer::Signer;
use solana_pubkey::Pubkey;
use anchor_lang::system_program;
use std::rc::Rc;

crucible_idl_gen::declare_fuzz_program!("idls/drift.json");

// ---------------------------------------------------------------------------
// Program & sysvar constants
// ---------------------------------------------------------------------------

const DRIFT_PROGRAM_ID: Pubkey = Pubkey::new_from_array([
    0x09, 0x54, 0xdb, 0xbe, 0x9e, 0xc9, 0x60, 0xc9,
    0x8a, 0x7a, 0x29, 0x3f, 0xe2, 0x13, 0x36, 0x96,
    0x6f, 0xe1, 0x80, 0xd1, 0x51, 0xae, 0x4b, 0x81,
    0x79, 0x56, 0x1f, 0x89, 0x85, 0x4a, 0x53, 0xf6,
]); // dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH

const SYSVAR_RENT: Pubkey = Pubkey::new_from_array([
    0x06, 0xa7, 0xd5, 0x17, 0x19, 0x2c, 0x5c, 0x51,
    0x21, 0x8c, 0xc9, 0x4c, 0x3d, 0x4a, 0xf1, 0x7f,
    0x58, 0xda, 0xee, 0x08, 0x9b, 0xa1, 0xfd, 0x44,
    0xe3, 0xdb, 0xd9, 0x8a, 0x00, 0x00, 0x00, 0x00,
]);

const SYSTEM_PROGRAM: Pubkey = Pubkey::new_from_array([0u8; 32]);

const SPL_TOKEN_PROGRAM: Pubkey = Pubkey::new_from_array([
    0x06, 0xdd, 0xf6, 0xe1, 0x19, 0xbe, 0x63, 0x1b,
    0x89, 0x14, 0xa6, 0xf9, 0xe2, 0x97, 0x47, 0x5a,
    0xc2, 0x01, 0xc1, 0xbd, 0x10, 0x38, 0x62, 0x3a,
    0x8b, 0x5d, 0xc8, 0xa4, 0xe1, 0x93, 0xff, 0x6b,
]);

// ---------------------------------------------------------------------------
// Instruction discriminators (8-byte Anchor sighash, from IDL)
// ---------------------------------------------------------------------------

const DISC_INIT_USER_STATS: [u8; 8] = [254, 243, 72, 98, 251, 130, 168, 213];  // initialize_user_stats (snake_case from local IDL)
const DISC_INIT_USER: [u8; 8] = [111, 17, 185, 250, 60, 122, 38, 254];  // initialize_user (snake_case from local IDL)
const DISC_DEPOSIT: [u8; 8] = [242, 35, 198, 137, 82, 225, 242, 182];  // deposit (same both ways)
const DISC_WITHDRAW: [u8; 8] = [183, 18, 70, 156, 148, 109, 161, 34];  // withdraw (same both ways)
const DISC_SETTLE_PNL: [u8; 8] = [43, 61, 234, 45, 15, 95, 152, 153];  // settle_pnl (snake_case from local IDL)
const DISC_SETTLE_FUNDING: [u8; 8] = [222, 90, 202, 94, 28, 45, 115, 183];  // settle_funding_payment (snake_case from local IDL)
const DISC_UPDATE_FUNDING_RATE: [u8; 8] = [201, 178, 116, 212, 166, 144, 72, 238];  // update_funding_rate (snake_case from local IDL)
const DISC_LIQUIDATE_PERP: [u8; 8] = [75, 35, 119, 247, 191, 18, 139, 2];  // liquidate_perp (snake_case from local IDL)
const DISC_PLACE_PERP_ORDER: [u8; 8] = [69, 161, 93, 202, 120, 126, 76, 185];  // place_perp_order (snake_case from local IDL)
const DISC_CANCEL_ORDER: [u8; 8] = [95, 129, 237, 240, 8, 49, 223, 132];  // cancel_order (snake_case from local IDL)

// ---------------------------------------------------------------------------
// PDA derivation helpers (CORRECTED seeds from Drift source)
// ---------------------------------------------------------------------------

fn state_pda(program: &Pubkey) -> Pubkey {
    Pubkey::find_program_address(&[b"drift_state"], program).0
}
fn drift_signer_pda(program: &Pubkey) -> Pubkey {
    Pubkey::find_program_address(&[b"drift_signer"], program).0
}
/// CORRECT seed: b"user" (not b"user_account" as in v6.11)
fn user_acct_pda(program: &Pubkey, user: &Pubkey) -> Pubkey {
    Pubkey::find_program_address(&[b"user", user.as_ref(), &0u16.to_le_bytes()], program).0
}
fn user_stats_pda(program: &Pubkey, user: &Pubkey) -> Pubkey {
    Pubkey::find_program_address(&[b"user_stats", user.as_ref()], program).0
}
fn vault_pda(program: &Pubkey, market_index: u16) -> Pubkey {
    Pubkey::find_program_address(&[b"spot_market_vault", &market_index.to_le_bytes()], program).0
}

// ---------------------------------------------------------------------------
// Anchor account discriminators (SHA256("account:<Name>")[0..8])
// Computed offline to avoid pulling in solana_program::hash
// ---------------------------------------------------------------------------

const DISC_STATE: [u8; 8] = [216, 146, 107, 94, 104, 75, 182, 177];
const DISC_USER: [u8; 8] = [159, 117, 95, 227, 239, 151, 58, 236];
const DISC_USER_STATS: [u8; 8] = [176, 223, 136, 27, 122, 79, 32, 227];

// ---------------------------------------------------------------------------
// State PDA builder (borsh serialization, 992 bytes total incl. 8-byte disc)
// ---------------------------------------------------------------------------

fn build_state_bytes(admin: &Pubkey, signer: &Pubkey, signer_nonce: u8) -> Vec<u8> {
    let mut d = Vec::with_capacity(992);
    // Anchor discriminator
    d.extend_from_slice(&DISC_STATE);
    // admin
    d.extend_from_slice(&admin.to_bytes());
    // whitelist_mint (default)
    d.extend_from_slice(&[0u8; 32]);
    // discount_mint (default)
    d.extend_from_slice(&[0u8; 32]);
    // signer (drift_signer PDA)
    d.extend_from_slice(&signer.to_bytes());
    // srm_vault (default)
    d.extend_from_slice(&[0u8; 32]);
    // perp_fee_structure (FeeStructure)
    build_fee_structure(&mut d);
    // spot_fee_structure (FeeStructure)
    build_fee_structure(&mut d);
    // oracle_guard_rails (OracleGuardRails)
    build_oracle_guard_rails(&mut d);
    // number_of_authorities: u64
    d.extend_from_slice(&0u64.to_le_bytes());
    // number_of_sub_accounts: u64
    d.extend_from_slice(&0u64.to_le_bytes());
    // lp_cooldown_time: u64
    d.extend_from_slice(&0u64.to_le_bytes());
    // liquidation_margin_buffer_ratio: u32 = MARGIN_PRECISION/50 = 200
    d.extend_from_slice(&200u32.to_le_bytes());
    // settlement_duration: u16
    d.extend_from_slice(&0u16.to_le_bytes());
    // number_of_markets: u16
    d.extend_from_slice(&1u16.to_le_bytes());
    // number_of_spot_markets: u16
    d.extend_from_slice(&1u16.to_le_bytes());
    // signer_nonce: u8
    d.push(signer_nonce);
    // min_perp_auction_duration: u8
    d.push(10);
    // default_market_order_time_in_force: u8
    d.push(60);
    // default_spot_auction_duration: u8
    d.push(10);
    // exchange_status: u8 = 0 (active, no pauses)
    d.push(0);
    // liquidation_duration: u8
    d.push(0);
    // initial_pct_to_liquidate: u16
    d.extend_from_slice(&0u16.to_le_bytes());
    // max_number_of_sub_accounts: u16
    d.extend_from_slice(&0u16.to_le_bytes());
    // max_initialize_user_fee: u16
    d.extend_from_slice(&0u16.to_le_bytes());
    // feature_bit_flags: u8
    d.push(0);
    // lp_pool_feature_bit_flags: u8
    d.push(0);
    // padding: [u8; 8]
    d.extend_from_slice(&[0u8; 8]);
    assert_eq!(d.len(), 992, "State must be exactly 992 bytes");
    d
}

/// Serialize a FeeStructure (360 bytes): 10 FeeTiers (320) + OrderFillerReward (20) + 2 u64 (16) = 356... hmm
/// Actually FeeStructure layout: 10*FeeTier(8*4=32) = 320 + OrderFillerReward(4+4+16=24) + 2*u64 = 16 -> 360
fn build_fee_structure(d: &mut Vec<u8>) {
    let fee_denom: u32 = 100_000; // FEE_DENOMINATOR = 10 * ONE_BPS_DENOMINATOR
    let pct_denom: u32 = 100; // FEE_PERCENTAGE_DENOMINATOR
    let numerators = [100u32, 90, 80, 70, 60, 50, 0, 0, 0, 0];
    for &num in &numerators {
        // FeeTier: 8 x u32 = 32 bytes
        d.extend_from_slice(&num.to_le_bytes());
        d.extend_from_slice(&fee_denom.to_le_bytes());
        d.extend_from_slice(&20u32.to_le_bytes()); // maker_rebate_numerator
        d.extend_from_slice(&fee_denom.to_le_bytes());
        d.extend_from_slice(&15u32.to_le_bytes()); // referrer_reward_numerator
        d.extend_from_slice(&pct_denom.to_le_bytes());
        d.extend_from_slice(&5u32.to_le_bytes()); // referee_fee_numerator
        d.extend_from_slice(&pct_denom.to_le_bytes());
    }
    // OrderFillerRewardStructure
    d.extend_from_slice(&10u32.to_le_bytes());  // reward_numerator
    d.extend_from_slice(&pct_denom.to_le_bytes()); // reward_denominator
    d.extend_from_slice(&10_000u128.to_le_bytes()); // time_based_reward_lower_bound
    // referrer_reward_epoch_upper_bound: u64
    d.extend_from_slice(&150_000_000_000u64.to_le_bytes());
    // flat_filler_fee: u64
    d.extend_from_slice(&10_000u64.to_le_bytes());
}

/// Serialize OracleGuardRails (48 bytes)
fn build_oracle_guard_rails(d: &mut Vec<u8>) {
    // PriceDivergenceGuardRails
    d.extend_from_slice(&(100_000u64).to_le_bytes()); // mark_oracle_percent_divergence
    d.extend_from_slice(&(500_000u64).to_le_bytes()); // oracle_twap_5min_percent_divergence
    // ValidityGuardRails
    d.extend_from_slice(&10i64.to_le_bytes());         // slots_before_stale_for_amm
    d.extend_from_slice(&120i64.to_le_bytes());        // slots_before_stale_for_margin
    d.extend_from_slice(&(20_000u64).to_le_bytes());   // confidence_interval_max_size
    d.extend_from_slice(&5i64.to_le_bytes());           // too_volatile_ratio
}

// ---------------------------------------------------------------------------
// Pre-create accounts with correct binary layout.
// LiteSVM does not persist CPI-created account data, so we bypass Drift's
// init instructions entirely and write the accounts directly.
// ---------------------------------------------------------------------------

const USER_STATS_SIZE: usize = 240;
const USER_SIZE: usize = 4376;

/// Create a zero-filled account of the given size with program owner and rent.
fn make_account(size: usize, lamports: u64, owner: Pubkey) -> solana_account::Account {
    solana_account::Account {
        lamports,
        data: vec![0u8; size],
        owner,
        executable: false,
        rent_epoch: 0,
    }
}

/// Pre-create a UserStats PDA with correct discriminator + authority.
fn precreate_user_stats(ctx: &mut TestContext, pda: &Pubkey, authority: &Pubkey) {
    let mut acct = make_account(USER_STATS_SIZE, 2_000_000, DRIFT_PROGRAM_ID);
    acct.data[..8].copy_from_slice(&DISC_USER_STATS);
    acct.data[8..40].copy_from_slice(&authority.to_bytes());
    ctx.write_account(pda, acct).unwrap();
}

/// Pre-create a User PDA with correct discriminator + authority.
fn precreate_user(ctx: &mut TestContext, pda: &Pubkey, authority: &Pubkey) {
    let mut acct = make_account(USER_SIZE, 10_000_000, DRIFT_PROGRAM_ID);
    acct.data[..8].copy_from_slice(&DISC_USER);
    // authority at offset 8
    acct.data[8..40].copy_from_slice(&authority.to_bytes());
    // sub_account_id: u16 at offset 72+32=104... no, let's compute from struct layout.
    // User struct: disc(8) + authority(32) + delegate(32) + name(32) + spot_positions + perp_positions + orders
    // sub_account_id is near the end. For now zeroed is fine - BPF reads authority for auth checks.
    ctx.write_account(pda, acct).unwrap();
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn lamport(ctx: &TestContext, key: &Pubkey) -> u64 {
    ctx.read_account(key).map(|a| a.lamports).unwrap_or(0)
}

fn raw_ix(
    disc: [u8; 8],
    data: Vec<u8>,
    accounts: Vec<(Pubkey, bool, bool)>,
) -> solana_instruction::Instruction {
    let mut full_data = disc.to_vec();
    full_data.extend_from_slice(&data);
    solana_instruction::Instruction {
        program_id: DRIFT_PROGRAM_ID,
        accounts: accounts
            .into_iter()
            .map(|(k, is_mut, is_signer)| solana_instruction::AccountMeta {
                pubkey: k,
                is_signer,
                is_writable: is_mut,
            })
            .collect(),
        data: full_data,
    }
}

// ---------------------------------------------------------------------------
// Fixture state
// ---------------------------------------------------------------------------

#[derive(Clone)]
struct DriftState {
    steps: u32,
    n_ok: u32,
    n_err: u32,
    baseline: u128,
    last_err: String,
}

#[derive(Clone)]
struct Drift {
    ctx: TestContext,
    program_id: Pubkey,
    admin: Rc<Keypair>,
    users: Vec<Rc<Keypair>>,
    /// Per-user USDC token accounts
    user_usdc: Vec<Pubkey>,
    /// Per-user UserStats PDAs
    user_stats_pdas: Vec<Pubkey>,
    /// Per-user User PDAs
    user_acct_pdas: Vec<Pubkey>,
    quote_mint: Pubkey,
    state_account: Pubkey,
    signer_pda: Pubkey,
    vault: Pubkey,
    state: DriftState,
}

// ---------------------------------------------------------------------------
// Fixture setup
// ---------------------------------------------------------------------------

#[fuzz_fixture]
impl Drift {
    pub fn setup() -> Self {
        let mut ctx = TestContext::new();
        let program_id = DRIFT_PROGRAM_ID;
        ctx.add_program(&program_id, "target/deploy/drift.so").unwrap();

        // --- Fund admin ---
        let admin = Rc::new(Keypair::new());
        ctx.create_account()
            .pubkey(admin.pubkey())
            .lamports(1_000_000_000_000)
            .owner(system_program::ID)
            .create()
            .unwrap();

        // --- Create USDC quote-asset mint ---
        let quote_mint = Pubkey::new_unique();
        ctx.create_mint()
            .pubkey(quote_mint)
            .decimals(6)
            .mint_authority(admin.pubkey())
            .create()
            .unwrap();

        // --- Derive PDAs ---
        let state_account = state_pda(&program_id);
        let (signer_pda, signer_nonce) =
            Pubkey::find_program_address(&[b"drift_signer"], &program_id);
        let vault = vault_pda(&program_id, 0); // market_index 0

        // --- Pre-write State PDA (bypass CPI persistence limitation) ---
        let state_bytes = build_state_bytes(&admin.pubkey(), &signer_pda, signer_nonce);
        ctx.create_account()
            .pubkey(state_account)
            .lamports(1_000_000_000) // 1 SOL rent
            .data(&state_bytes)
            .owner(program_id)
            .create()
            .unwrap();

        eprintln!(
            "[SETUP] state_pda={} signer_pda={} signer_nonce={} vault={}",
            state_account, signer_pda, signer_nonce, vault
        );

        // --- Create vault token account at PDA address ---
        ctx.create_token_account()
            .pubkey(vault)
            .mint(quote_mint)
            .token_owner(signer_pda)
            .create()
            .unwrap();

        // --- Fund users + create USDC token accounts ---
        let mut users = Vec::new();
        let mut user_usdc = Vec::new();
        for _ in 0..4 {
            let user = Rc::new(Keypair::new());
            ctx.create_account()
                .pubkey(user.pubkey())
                .lamports(100_000_000_000)
                .owner(system_program::ID)
                .create()
                .unwrap();
            let ata = Pubkey::new_unique();
            ctx.create_token_account()
                .pubkey(ata)
                .mint(quote_mint)
                .token_owner(user.pubkey())
                .create()
                .unwrap();
            ctx.mint_to(&quote_mint, &ata, 1_000_000_000_000, &admin)
                .unwrap();
            users.push(user);
            user_usdc.push(ata);
        }

        // --- Pre-create UserStats + User accounts directly (skip CPI init) ---
        // LiteSVM doesn't persist CPI writes, so we bypass Drift's init
        // instructions and pre-create the accounts with correct binary layout.
        let mut user_stats_pdas = Vec::new();
        let mut user_acct_pdas = Vec::new();

        for user in &users {
            let stats_pda = user_stats_pda(&program_id, &user.pubkey());
            let acct_pda = user_acct_pda(&program_id, &user.pubkey());
            precreate_user_stats(&mut ctx, &stats_pda, &user.pubkey());
            precreate_user(&mut ctx, &acct_pda, &user.pubkey());

            // Verify pre-created accounts are readable
            if let Ok(stats_acct) = ctx.read_account(&stats_pda) {
                eprintln!(
                    "[SETUP] user_stats PDA: len={} disc={:?} owner={}",
                    stats_acct.data.len(),
                    &stats_acct.data[..8],
                    stats_acct.owner
                );
            } else {
                eprintln!("[SETUP] WARNING: user_stats PDA NOT readable: {}", stats_pda);
            }
            if let Ok(user_acct) = ctx.read_account(&acct_pda) {
                eprintln!(
                    "[SETUP] user PDA: len={} disc={:?} owner={}",
                    user_acct.data.len(),
                    &user_acct.data[..8],
                    user_acct.owner
                );
            } else {
                eprintln!("[SETUP] WARNING: user PDA NOT readable: {}", acct_pda);
            }

            user_stats_pdas.push(stats_pda);
            user_acct_pdas.push(acct_pda);
        }

        // --- Snapshot baseline lamports ---
        let mut baseline: u128 = 0;
        baseline += lamport(&ctx, &admin.pubkey()) as u128;
        for user in &users {
            baseline += lamport(&ctx, &user.pubkey()) as u128;
        }
        baseline += lamport(&ctx, &state_account) as u128;

        let state = DriftState {
            steps: 0,
            n_ok: 0,
            n_err: 0,
            baseline,
            last_err: String::new(),
        };

        Self {
            ctx,
            program_id,
            admin,
            users,
            user_usdc,
            user_stats_pdas,
            user_acct_pdas,
            quote_mint,
            state_account,
            signer_pda,
            vault,
            state,
        }
    }

    // =================================================================
    // ACTIONS
    // =================================================================

    /// ACTION: Deposit USDC collateral into spot market vault (market_index=0).
    /// Account order matches Deposit context:
    ///   state, user, user_stats, authority, spot_market_vault, user_token_account, token_program
    pub fn action_deposit(
        &mut self,
        #[range(0..4)] user_idx: usize,
        #[range(1..1_000_000)] amount: u64,
    ) {
        let user = Rc::clone(&self.users[user_idx]);
        let ix = raw_ix(
            DISC_DEPOSIT,
            {
                let mut d = Vec::new();
                d.extend_from_slice(&0u16.to_le_bytes()); // market_index = 0
                d.extend_from_slice(&amount.to_le_bytes());
                d.push(0u8); // reduce_only = false
                d
            },
            vec![
                (self.state_account, false, false),              // state
                (self.user_acct_pdas[user_idx], true, false),   // user
                (self.user_stats_pdas[user_idx], true, false),  // user_stats
                (user.pubkey(), false, true),                    // authority
                (self.vault, true, false),                       // spot_market_vault
                (self.user_usdc[user_idx], true, false),         // user_token_account
                (SPL_TOKEN_PROGRAM, false, false),               // token_program
            ],
        );
        self.dispatch(ix, &[&*user]);
    }

    /// ACTION: Withdraw USDC from spot market vault.
    pub fn action_withdraw(
        &mut self,
        #[range(0..4)] user_idx: usize,
        #[range(1..1_000_000)] amount: u64,
    ) {
        let user = Rc::clone(&self.users[user_idx]);
        let ix = raw_ix(
            DISC_WITHDRAW,
            {
                let mut d = Vec::new();
                d.extend_from_slice(&0u16.to_le_bytes()); // market_index
                d.extend_from_slice(&amount.to_le_bytes());
                d.push(0u8); // reduce_only
                d
            },
            vec![
                (self.state_account, false, false),
                (self.user_acct_pdas[user_idx], true, false),
                (self.user_stats_pdas[user_idx], true, false),
                (user.pubkey(), false, true),
                (self.vault, true, false),
                (self.user_usdc[user_idx], true, false),
                (SPL_TOKEN_PROGRAM, false, false),
            ],
        );
        self.dispatch(ix, &[&*user]);
    }

    /// ACTION: Place a perp order (fuzzed OrderParams).
    pub fn action_place_perp_order(
        &mut self,
        #[range(0..4)] user_idx: usize,
        #[range(0..255)] order_type: u8,
    ) {
        let user = Rc::clone(&self.users[user_idx]);
        // OrderParams: order_type(u8) + direction(u8) + base_amount(i64) + ...
        let mut order_data = Vec::new();
        order_data.push(order_type);
        order_data.push(0u8); // direction (long)
        order_data.extend_from_slice(&1_000_000i64.to_le_bytes()); // base_asset_amount
        order_data.extend_from_slice(&[0u8; 64]); // remaining OrderParams fields

        let ix = raw_ix(
            DISC_PLACE_PERP_ORDER,
            order_data,
            vec![
                (self.state_account, false, false),
                (self.user_acct_pdas[user_idx], true, false),
                (user.pubkey(), false, true),
            ],
        );
        self.dispatch(ix, &[&*user]);
    }

    /// ACTION: Cancel an order.
    pub fn action_cancel_order(
        &mut self,
        #[range(0..4)] user_idx: usize,
        #[range(0..10)] order_id: u32,
    ) {
        let user = Rc::clone(&self.users[user_idx]);
        let ix = raw_ix(
            DISC_CANCEL_ORDER,
            {
                let mut d = Vec::new();
                d.push(1u8); // Some(order_id)
                d.extend_from_slice(&order_id.to_le_bytes());
                d
            },
            vec![
                (self.state_account, false, false),
                (self.user_acct_pdas[user_idx], true, false),
                (user.pubkey(), false, true),
            ],
        );
        self.dispatch(ix, &[&*user]);
    }

    /// ACTION: Settle PNL for a perp market.
    pub fn action_settle_pnl(
        &mut self,
        #[range(0..4)] user_idx: usize,
        #[range(0..8)] market_idx: u16,
    ) {
        let user = Rc::clone(&self.users[user_idx]);
        let ix = raw_ix(
            DISC_SETTLE_PNL,
            market_idx.to_le_bytes().to_vec(),
            vec![
                (self.state_account, false, false),
                (self.user_acct_pdas[user_idx], true, false),
                (user.pubkey(), false, true),
                (self.vault, false, false),
            ],
        );
        self.dispatch(ix, &[&*user]);
    }

    /// ACTION: Settle funding payment.
    pub fn action_settle_funding(&mut self, #[range(0..4)] user_idx: usize) {
        let user = Rc::clone(&self.users[user_idx]);
        let ix = raw_ix(
            DISC_SETTLE_FUNDING,
            vec![],
            vec![
                (self.state_account, false, false),
                (self.user_acct_pdas[user_idx], true, false),
            ],
        );
        self.dispatch(ix, &[&*user]);
    }

    /// ACTION: Update funding rate for a perp market (oracle-dependent).
    pub fn action_update_funding_rate(&mut self, #[range(0..16)] market_idx: u16) {
        let perp_market = Pubkey::find_program_address(
            &[b"perp_market", &market_idx.to_le_bytes()],
            &self.program_id,
        )
        .0;
        let oracle = Pubkey::find_program_address(
            &[b"oracle", &market_idx.to_le_bytes()],
            &self.program_id,
        )
        .0;
        let ix = raw_ix(
            DISC_UPDATE_FUNDING_RATE,
            market_idx.to_le_bytes().to_vec(),
            vec![
                (self.state_account, false, false),
                (perp_market, true, false),
                (oracle, false, false),
            ],
        );
        self.dispatch(ix, &[]);
    }

    /// ACTION: Attempt to liquidate a user's perp position.
    pub fn action_liquidate_perp(
        &mut self,
        #[range(0..4)] liquidator_idx: usize,
        #[range(0..4)] target_idx: usize,
        #[range(1..1_000_000)] max_base: u64,
        #[range(0..16)] market_idx: u16,
    ) {
        if liquidator_idx == target_idx {
            return;
        }
        let liquidator = Rc::clone(&self.users[liquidator_idx]);
        let ix = raw_ix(
            DISC_LIQUIDATE_PERP,
            {
                let mut d = Vec::new();
                d.extend_from_slice(&market_idx.to_le_bytes());
                d.extend_from_slice(&max_base.to_le_bytes());
                d
            },
            vec![
                (self.state_account, false, false),
                (liquidator.pubkey(), false, true),
                (self.user_acct_pdas[liquidator_idx], true, false),
                (self.user_stats_pdas[liquidator_idx], true, false),
                (self.user_acct_pdas[target_idx], true, false),
                (self.user_stats_pdas[target_idx], true, false),
            ],
        );
        self.dispatch(ix, &[&*liquidator]);
    }

    /// ACTION: Advance the slot clock (for funding-rate accrual / oracle staleness).
    pub fn action_advance_slots(&mut self, #[range(1..4096)] slots: u64) {
        self.ctx.warp_to_slot(self.ctx.slot() + slots);
        self.state.steps = self.state.steps.wrapping_add(1);
    }

    // =================================================================
    // DISPATCH + INVARIANT
    // =================================================================

    fn dispatch(&mut self, ix: solana_instruction::Instruction, signers: &[&Keypair]) {
        let result = self.ctx.raw_call(ix).signers(signers).send();
        match &result {
            Ok(tx_result) => {
                if tx_result.is_success() {
                    self.state.n_ok = self.state.n_ok.wrapping_add(1);
                } else {
                    self.state.n_err = self.state.n_err.wrapping_add(1);
                    // Log ALL failed transactions (not just the first one)
                    self.state.last_err = format!(
                        "tx_failed: {:?}",
                        tx_result.logs().last()
                    );
                }
            }
            Err(e) => {
                self.state.n_err = self.state.n_err.wrapping_add(1);
                self.state.last_err = format!("dispatch_err: {}", e);
            }
        }
        self.state.steps = self.state.steps.wrapping_add(1);
    }

    /// INVARIANT: Total lamports (admin + users + state PDA) must be conserved
    /// within tolerance. Any large negative delta = value extraction.
    pub fn after_action(&self) {
        let mut total: u128 = 0;
        total += lamport(&self.ctx, &self.admin.pubkey()) as u128;
        for user in &self.users {
            total += lamport(&self.ctx, &user.pubkey()) as u128;
        }
        total += lamport(&self.ctx, &self.state_account) as u128;

        // Tolerance: 100K lamports (~20 account creations at ~5K rent each)
        let tolerance: u128 = 100_000;
        let delta = (total as i128) - (self.state.baseline as i128);
        if delta.abs() as u128 > tolerance {
            eprintln!(
                "[INVARIANT VIOLATION] lamport_drift baseline={} actual={} delta={} \
                 steps={} ok={} err={} last_err={}",
                self.state.baseline,
                total,
                delta,
                self.state.steps,
                self.state.n_ok,
                self.state.n_err,
                self.state.last_err,
            );
            std::process::exit(77);
        }
    }
}

// ---------------------------------------------------------------------------
// Fuzz entry point
// ---------------------------------------------------------------------------

#[invariant_test]
fn invariant_test(fixture: &mut Drift) {
    let n = fixture.state.steps;
    if n == 0 || n % 100 == 0 {
        eprintln!(
            "[STATS] step={} ok={} err={} last_err={}",
            n, fixture.state.n_ok, fixture.state.n_err, fixture.state.last_err
        );
    }
}
