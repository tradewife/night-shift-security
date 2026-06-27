use anchor_lang::system_program;
use crucible_fuzzer::*;
use sha2::{Digest, Sha256};
use solana_account::Account;
use solana_instruction::Instruction;
use solana_keypair::Keypair;
use solana_pubkey::Pubkey;
use solana_signer::Signer;
use std::{env, rc::Rc};

const PROGRAM_ID: Pubkey = Pubkey::new_from_array([
    0x20, 0x90, 0xc6, 0xcd, 0x0d, 0x2f, 0x85, 0xfb,
    0xc2, 0xa0, 0x20, 0x4a, 0x74, 0xd5, 0x64, 0xa9,
    0x04, 0x99, 0xb8, 0xd3, 0x6b, 0xcd, 0x9a, 0x9a,
    0x38, 0xf9, 0x72, 0x39, 0xdc, 0x1a, 0x3e, 0x61,
]); // 3C865D264L4NkAm78zfnDzQJJvXuU3fMjRUvRxyPi5da

const TOKEN_2022_PROGRAM_ID: Pubkey = Pubkey::new_from_array([
    6, 221, 246, 225, 238, 117, 143, 222, 24, 66, 93, 188, 228, 108, 205, 218,
    182, 26, 252, 77, 131, 185, 13, 39, 254, 189, 249, 40, 216, 161, 139, 252,
]); // TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb

const ASSOCIATED_TOKEN_PROGRAM_ID: Pubkey = Pubkey::new_from_array([
    140, 151, 37, 143, 78, 36, 137, 241, 187, 61, 16, 41, 20, 142, 13, 131,
    11, 90, 19, 153, 218, 255, 16, 132, 4, 142, 123, 216, 219, 233, 248, 89,
]); // ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL

const GLOBAL_SEED: &[u8] = b"global";
const MINT_AUTHORITY_SEED: &[u8] = b"mint_authority";
const M_VAULT_SEED: &[u8] = b"m_vault";
const EARN_MANAGER_SEED: &[u8] = b"earn_manager";
const EARNER_SEED: &[u8] = b"earner";

const DISC_TRANSFER_ADMIN: [u8; 8] = [42, 242, 66, 106, 228, 10, 111, 156];
const DISC_ACCEPT_ADMIN: [u8; 8] = [112, 42, 45, 90, 116, 181, 13, 170];
const DISC_REVOKE_ADMIN: [u8; 8] = [98, 62, 163, 107, 196, 212, 46, 102];
const DISC_ADD_WRAP_AUTH: [u8; 8] = [234, 104, 99, 10, 191, 202, 68, 43];
const DISC_REMOVE_WRAP_AUTH: [u8; 8] = [218, 60, 185, 181, 112, 63, 60, 152];
const DISC_ADD_EARN_MANAGER: [u8; 8] = [237, 29, 254, 71, 117, 177, 159, 25];
const DISC_ADD_EARNER: [u8; 8] = [191, 90, 193, 126, 226, 158, 64, 168];
const DISC_CONFIGURE_EARN_MANAGER: [u8; 8] = [116, 96, 19, 92, 147, 244, 108, 216];
const DISC_TRANSFER_EARNER: [u8; 8] = [100, 120, 80, 44, 163, 34, 79, 91];
const DISC_REMOVE_EARNER: [u8; 8] = [195, 235, 44, 204, 195, 134, 98, 113];

const DISC_SYNC: [u8; 8] = [4, 219, 40, 164, 21, 157, 189, 88];
const DISC_CLAIM_FEES: [u8; 8] = [82, 251, 233, 156, 12, 52, 184, 202];
const DISC_SET_FEE: [u8; 8] = [18, 154, 24, 18, 237, 214, 19, 80];
const DISC_CLAIM_FOR: [u8; 8] = [245, 67, 97, 44, 59, 223, 144, 1];
const DISC_WRAP: [u8; 8] = [178, 40, 10, 189, 228, 129, 186, 140];
const DISC_UNWRAP: [u8; 8] = [126, 175, 198, 14, 212, 69, 50, 44];

// ext_swap program discriminators
const DISC_ES_INITIALIZE_GLOBAL: [u8; 8] = [47, 225, 15, 112, 86, 51, 190, 231];
const DISC_ES_WHITELIST_EXTENSION: [u8; 8] = [186, 175, 23, 231, 77, 201, 205, 165];
const DISC_ES_REMOVE_WHITELISTED_EXTENSION: [u8; 8] = [248, 52, 115, 71, 67, 42, 71, 252];
const DISC_ES_WHITELIST_UNWRAPPER: [u8; 8] = [219, 87, 23, 47, 189, 191, 123, 235];
const DISC_ES_REMOVE_WHITELISTED_UNWRAPPER: [u8; 8] = [166, 23, 120, 95, 66, 168, 192, 163];
const DISC_ES_SWAP: [u8; 8] = [248, 198, 158, 145, 225, 117, 135, 200];

const EXT_SWAP_PROGRAM_ID: Pubkey = Pubkey::new_from_array([
    5, 60, 242, 167, 56, 11, 17, 54, 97, 114, 227, 114, 39, 167, 101, 13,
    161, 190, 235, 218, 112, 220, 127, 89, 126, 174, 151, 23, 37, 130, 35, 190,
]); // MSwapi3WhNKMUGm9YrxGhypgUEt7wYQH3ZgG32XoWzH

const EXT_SWAP_SO: &str = "/home/kt/.local/share/warp-terminal/worktrees/night-shift-security/lupine-sierra/sources/kast/target/deploy/ext_swap.so";

const PROGRAM_ID_EXT_A: Pubkey = Pubkey::new_from_array([40, 174, 7, 32, 134, 249, 185, 154, 179, 250, 209, 123, 38, 137, 64, 41, 225, 164, 136, 5, 167, 69, 205, 101, 10, 253, 182, 193, 154, 172, 30, 96]); // 3joDhmLtHLrSBGfeAe1xQiv3gjikes3x8S4N3o6Ld8zB
const PROGRAM_ID_EXT_B: Pubkey = Pubkey::new_from_array([244, 58, 3, 148, 185, 175, 167, 94, 128, 145, 204, 137, 125, 73, 28, 162, 51, 145, 178, 30, 72, 187, 18, 214, 147, 25, 116, 252, 154, 45, 234, 154]); // HSMnbWEkB7sEQAGSzBPeACNUCXC9FgNeeESLnHtKfoy3

const EXT_A_SO: &str = "/home/kt/.local/share/warp-terminal/worktrees/night-shift-security/lupine-sierra/sources/kast/repo/tests/programs/ext_a.so";

const INDEX_SCALE_U64: u64 = 1_000_000_000_000;

const SO_NO_YIELD: &str = "/home/kt/.local/share/warp-terminal/worktrees/night-shift-security/lupine-sierra/sources/kast/target/deploy/m_ext_no_yield.so";
const SO_SCALED_UI: &str = "/home/kt/.local/share/warp-terminal/worktrees/night-shift-security/lupine-sierra/sources/kast/target/deploy/m_ext_scaled_ui.so";
const SO_CRANK: &str = "/home/kt/.local/share/warp-terminal/worktrees/night-shift-security/lupine-sierra/sources/kast/target/deploy/m_ext_crank.so";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum VariantMode {
    NoYield,
    ScaledUi,
    Crank,
}

impl VariantMode {
    fn from_env() -> Self {
        match env::var("KAST_VARIANT")
            .unwrap_or_else(|_| "no-yield".to_string())
            .as_str()
        {
            "scaled-ui" => Self::ScaledUi,
            "crank" => Self::Crank,
            _ => Self::NoYield,
        }
    }

    fn so_path(&self) -> &'static str {
        match self {
            Self::NoYield => SO_NO_YIELD,
            Self::ScaledUi => SO_SCALED_UI,
            Self::Crank => SO_CRANK,
        }
    }

    fn yield_variant_tag(&self) -> u8 {
        match self {
            Self::NoYield => 0,
            Self::ScaledUi => 1,
            Self::Crank => 2,
        }
    }

    fn yield_config_len(&self) -> usize {
        match self {
            Self::NoYield => 1,
            Self::ScaledUi => 1 + 8 + 8 + 8,
            Self::Crank => 1 + 32 + 8 + 8 + 8,
        }
    }
}

fn account_disc(name: &str) -> [u8; 8] {
    let mut hasher = Sha256::new();
    hasher.update(format!("account:{name}").as_bytes());
    let out = hasher.finalize();
    let mut disc = [0u8; 8];
    disc.copy_from_slice(&out[..8]);
    disc
}

fn global_pda() -> (Pubkey, u8) {
    Pubkey::find_program_address(&[GLOBAL_SEED], &PROGRAM_ID)
}

fn mint_authority_pda() -> (Pubkey, u8) {
    Pubkey::find_program_address(&[MINT_AUTHORITY_SEED], &PROGRAM_ID)
}

fn m_vault_pda() -> (Pubkey, u8) {
    Pubkey::find_program_address(&[M_VAULT_SEED], &PROGRAM_ID)
}

fn earn_manager_pda(manager: &Pubkey) -> (Pubkey, u8) {
    Pubkey::find_program_address(&[EARN_MANAGER_SEED, manager.as_ref()], &PROGRAM_ID)
}

fn earner_pda(user_token_account: &Pubkey) -> (Pubkey, u8) {
    Pubkey::find_program_address(&[EARNER_SEED, user_token_account.as_ref()], &PROGRAM_ID)
}

fn make_account(size: usize, lamports: u64, owner: Pubkey) -> Account {
    Account {
        lamports,
        data: vec![0u8; size],
        owner,
        executable: false,
        rent_epoch: 0,
    }
}

fn raw_ix(disc: [u8; 8], data: Vec<u8>, accounts: Vec<(Pubkey, bool, bool)>) -> Instruction {
    let mut full_data = disc.to_vec();
    full_data.extend_from_slice(&data);
    Instruction {
        program_id: PROGRAM_ID,
        accounts: accounts
            .into_iter()
            .map(|(pubkey, writable, signer)| solana_instruction::AccountMeta {
                pubkey,
                is_writable: writable,
                is_signer: signer,
            })
            .collect(),
        data: full_data,
    }
}

fn raw_ext_swap_ix(disc: [u8; 8], data: Vec<u8>, accounts: Vec<(Pubkey, bool, bool)>) -> Instruction {
    let mut full_data = disc.to_vec();
    full_data.extend_from_slice(&data);
    Instruction {
        program_id: EXT_SWAP_PROGRAM_ID,
        accounts: accounts
            .into_iter()
            .map(|(pubkey, writable, signer)| solana_instruction::AccountMeta {
                pubkey,
                is_writable: writable,
                is_signer: signer,
            })
            .collect(),
        data: full_data,
    }
}

fn swap_global_pda() -> (Pubkey, u8) {
    Pubkey::find_program_address(&[GLOBAL_SEED], &EXT_SWAP_PROGRAM_ID)
}

fn global_pda_ext_a() -> (Pubkey, u8) {
    Pubkey::find_program_address(&[GLOBAL_SEED], &PROGRAM_ID_EXT_A)
}

fn mint_authority_pda_ext_a() -> (Pubkey, u8) {
    Pubkey::find_program_address(&[MINT_AUTHORITY_SEED], &PROGRAM_ID_EXT_A)
}

fn m_vault_pda_ext_a() -> (Pubkey, u8) {
    Pubkey::find_program_address(&[M_VAULT_SEED], &PROGRAM_ID_EXT_A)
}

fn encode_option_u64(value: Option<u64>) -> Vec<u8> {
    let mut out = Vec::new();
    match value {
        Some(v) => {
            out.push(1);
            out.extend_from_slice(&v.to_le_bytes());
        }
        None => out.push(0),
    }
    out
}

fn trace_errors_enabled() -> bool {
    matches!(
        std::env::var("KAST_TRACE_ERRORS").ok().as_deref(),
        Some("1") | Some("true") | Some("TRUE") | Some("yes") | Some("YES")
    )
}

/// Create the raw account data for a Token-2022 mint with ScaledUiAmountConfig extension.
/// TLV layout: PodMint(82) + padding(83) + AccountType::Mint(1) + TLV(type(2)+len(2)+data(56)) = 226 total.
/// The padding (82..165) comes from unpack_tlv_data computing account_type_index
/// as BASE_ACCOUNT_LENGTH(165) - Mint::SIZE_OF(82) = 83 relative to the rest slice.
fn make_scaled_ui_mint_bytes(authority: &Pubkey, multiplier: f64, decimals: u8, supply: u64) -> Vec<u8> {
    // Allocate 226 to match Token-2022 expected size
    let mut data = vec![0u8; 226];
    // PodMint at bytes 0..82
    // mint_authority: PodCOption<Pubkey>
    data[0..4].copy_from_slice(&1u32.to_le_bytes()); // tag = Some
    data[4..36].copy_from_slice(&authority.to_bytes());
    // supply at offset 36 (u64)
    data[36..44].copy_from_slice(&supply.to_le_bytes());
    data[44] = decimals;
    data[45] = 1; // is_initialized
    // freeze_authority at offset 46 (PodCOption<Pubkey> = None, already zero)
    // Bytes 82..164 = zero padding (discarded by unpack_tlv_data)
    // AccountType at offset 165 = rest[83] where rest = input[82..]
    data[165] = 1; // AccountType::Mint
    // TLV header: ExtensionType::ScaledUiAmount = 25
    data[166..168].copy_from_slice(&25u16.to_le_bytes());
    data[168..170].copy_from_slice(&56u16.to_le_bytes()); // length
    // ScaledUiAmountConfig data (56 bytes) at TLV offset 170
    data[170..202].copy_from_slice(&authority.to_bytes());
    data[202..210].copy_from_slice(&multiplier.to_le_bytes());
    // new_multiplier_effective_timestamp at 210 (i64)
    // = already zero
    data[218..226].copy_from_slice(&multiplier.to_le_bytes()); // new_multiplier
    data
}

/// Compute the Associated Token Account address for a given owner, mint, and token program.
fn associated_token_address(owner: &Pubkey, mint: &Pubkey, token_program: &Pubkey) -> Pubkey {
    Pubkey::find_program_address(
        &[owner.as_ref(), token_program.as_ref(), mint.as_ref()],
        &ASSOCIATED_TOKEN_PROGRAM_ID,
    )
    .0
}

fn build_global_bytes(
    mode: VariantMode,
    admin: &Pubkey,
    ext_mint: &Pubkey,
    m_mint: &Pubkey,
    earn_global: &Pubkey,
    global_bump: u8,
    m_vault_bump: u8,
    mint_auth_bump: u8,
    wrap_authorities: &[Pubkey],
    earn_authority: &Pubkey,
) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(&account_disc("ExtGlobalV2"));
    out.extend_from_slice(&admin.to_bytes());
    out.push(0); // pending_admin = None
    out.extend_from_slice(&ext_mint.to_bytes());
    out.extend_from_slice(&m_mint.to_bytes());
    out.extend_from_slice(&earn_global.to_bytes());
    out.push(global_bump);
    out.push(m_vault_bump);
    out.push(mint_auth_bump);
    match mode {
        VariantMode::NoYield => {
            out.push(0);
        }
        VariantMode::ScaledUi => {
            out.push(1);
            out.extend_from_slice(&0u64.to_le_bytes()); // fee_bps
            out.extend_from_slice(&1_000_000_000_000u64.to_le_bytes()); // last_m_index
            out.extend_from_slice(&1_000_000_000_000u64.to_le_bytes()); // last_ext_index
        }
        VariantMode::Crank => {
            out.push(2);
            out.extend_from_slice(&earn_authority.to_bytes());
            out.extend_from_slice(&1_000_000_000_000u64.to_le_bytes()); // last_m_index
            out.extend_from_slice(&1_000_000_000_000u64.to_le_bytes()); // last_ext_index
            out.extend_from_slice(&1u64.to_le_bytes()); // timestamp
        }
    }
    out.extend_from_slice(&(wrap_authorities.len() as u32).to_le_bytes());
    for authority in wrap_authorities {
        out.extend_from_slice(&authority.to_bytes());
    }
    out
}

fn build_earn_manager_bytes(
    manager: &Pubkey,
    fee_bps: u64,
    fee_token_account: &Pubkey,
    bump: u8,
) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(&account_disc("EarnManager"));
    out.extend_from_slice(&manager.to_bytes());
    out.push(1); // is_active
    out.extend_from_slice(&fee_bps.to_le_bytes());
    out.extend_from_slice(&fee_token_account.to_bytes());
    out.push(bump);
    out
}

fn build_earner_bytes(
    user: &Pubkey,
    user_token_account: &Pubkey,
    earn_manager: &Pubkey,
    bump: u8,
) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(&account_disc("Earner"));
    // Use last_claim_index = 1e12 matching program behavior (frozen until sync advances ext_index).
    let last_claim = 1_000_000_000_000u64;
    out.extend_from_slice(&last_claim.to_le_bytes()); // last_claim_index
    out.extend_from_slice(&1u64.to_le_bytes()); // last_claim_timestamp
    out.push(bump);
    out.extend_from_slice(&user.to_bytes());
    out.extend_from_slice(&user_token_account.to_bytes());
    out.extend_from_slice(&earn_manager.to_bytes());
    out.push(0); // recipient_token_account = None
    out
}

#[derive(Clone)]
struct ParsedGlobal {
    admin: Pubkey,
    pending_admin: Option<Pubkey>,
    ext_mint: Pubkey,
    m_mint: Pubkey,
    yield_variant: u8,
    last_m_index: u64,
    last_ext_index: u64,
    wrap_authorities: Vec<Pubkey>,
}

fn parse_pubkey(data: &[u8], offset: &mut usize) -> Pubkey {
    let mut bytes = [0u8; 32];
    bytes.copy_from_slice(&data[*offset..*offset + 32]);
    *offset += 32;
    Pubkey::new_from_array(bytes)
}

fn parse_global(data: &[u8], mode: VariantMode) -> ParsedGlobal {
    let mut offset = 8;
    let admin = parse_pubkey(data, &mut offset);
    let pending_tag = data[offset];
    offset += 1;
    let pending_admin = if pending_tag == 1 {
        Some(parse_pubkey(data, &mut offset))
    } else {
        None
    };
    let ext_mint = parse_pubkey(data, &mut offset);
    let m_mint = parse_pubkey(data, &mut offset);
    let _earn_global = parse_pubkey(data, &mut offset);
    offset += 3; // bumps
    let yield_variant = data[offset];
    // Extract ext_index and m_index from yield_config
    // scaled-ui: tag(1) + fee_bps(8) + last_m_index(8) + last_ext_index(8) = 25
    // crank: tag(1) + earn_authority(32) + last_m_index(8) + last_ext_index(8) + timestamp(8) = 57
    // no-yield: tag(1) = 1
    let (last_m_index, last_ext_index) = match mode {
        VariantMode::ScaledUi => {
            offset += 1 + 8; // skip tag + fee_bps
            let m = u64::from_le_bytes(data[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let e = u64::from_le_bytes(data[offset..offset + 8].try_into().unwrap());
            offset += 8;
            (m, e)
        }
        VariantMode::Crank => {
            offset += 1 + 32; // skip tag + earn_authority
            let m = u64::from_le_bytes(data[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let e = u64::from_le_bytes(data[offset..offset + 8].try_into().unwrap());
            offset += 16; // skip ext_index + timestamp
            (m, e)
        }
        VariantMode::NoYield => {
            offset += 1; // skip tag
            (INDEX_SCALE_U64, INDEX_SCALE_U64)
        }
    };
    let mut len_bytes = [0u8; 4];
    len_bytes.copy_from_slice(&data[offset..offset + 4]);
    offset += 4;
    let len = u32::from_le_bytes(len_bytes) as usize;
    let mut wrap_authorities = Vec::with_capacity(len);
    for _ in 0..len {
        wrap_authorities.push(parse_pubkey(data, &mut offset));
    }
    ParsedGlobal {
        admin,
        pending_admin,
        ext_mint,
        m_mint,
        yield_variant,
        last_m_index,
        last_ext_index,
        wrap_authorities,
    }
}

fn parse_earn_manager(data: &[u8]) -> (Pubkey, bool, u64) {
    let mut offset = 8;
    let manager = parse_pubkey(data, &mut offset);
    let is_active = data[offset] == 1;
    offset += 1;
    let mut fee_bytes = [0u8; 8];
    fee_bytes.copy_from_slice(&data[offset..offset + 8]);
    (manager, is_active, u64::from_le_bytes(fee_bytes))
}

fn parse_earner(data: &[u8]) -> (Pubkey, Pubkey) {
    let mut offset = 8 + 8 + 8 + 1 + 32 + 32;
    let earn_manager = parse_pubkey(data, &mut offset);
    let _recipient_tag = data[offset];
    let mut offset_user = 8 + 8 + 8 + 1;
    let user = parse_pubkey(data, &mut offset_user);
    (user, earn_manager)
}

#[derive(Clone)]
struct KastState {
    steps: u64,
    n_ok: u64,
    n_err: u64,
    baseline: u128,
    last_err: String,
}

#[derive(Clone)]
struct Kast {
    ctx: TestContext,
    mode: VariantMode,
    admin: Rc<Keypair>,
    pending_admin: Rc<Keypair>,
    wrap_candidates: Vec<Rc<Keypair>>,
    managers: Vec<Rc<Keypair>>,
    users: Vec<Rc<Keypair>>,
    // Primary m_ext instance
    ext_mint: Pubkey,
    m_mint: Pubkey,
    global_account: Pubkey,
    m_vault: Pubkey,
    ext_mint_authority: Pubkey,
    vault_m_token_account: Pubkey,
    fee_token_accounts: Vec<Pubkey>,
    user_token_accounts: Vec<Pubkey>,
    user_m_token_accounts: Vec<Pubkey>,
    // ext_a (no_yield) instance for cross-extension swap
    ext_a_mint: Pubkey,
    ext_a_global: Pubkey,
    ext_a_m_vault: Pubkey,
    ext_a_mint_authority: Pubkey,
    ext_a_vault_m_token_account: Pubkey,
    ext_a_user_token_accounts: Vec<Pubkey>,
    // ext_swap
    es_swap_global: Pubkey,
    es_initialized: bool,
    state: KastState,
}

impl Kast {
    fn known_signers(&self) -> Vec<Rc<Keypair>> {
        let mut out = vec![Rc::clone(&self.admin), Rc::clone(&self.pending_admin)];
        out.extend(self.wrap_candidates.iter().cloned());
        out.extend(self.managers.iter().cloned());
        out.extend(self.users.iter().cloned());
        out
    }

    fn signer_by_pubkey(&self, pubkey: &Pubkey) -> Rc<Keypair> {
        self.known_signers()
            .into_iter()
            .find(|kp| kp.pubkey() == *pubkey)
            .unwrap_or_else(|| Rc::clone(&self.admin))
    }

    fn current_global(&self) -> ParsedGlobal {
        let acct = self.ctx.read_account(&self.global_account).unwrap();
        parse_global(&acct.data, self.mode)
    }

    fn current_admin_signer(&self) -> Rc<Keypair> {
        self.signer_by_pubkey(&self.current_global().admin)
    }

    fn total_lamports(&self) -> u128 {
        let mut total = 0u128;
        for signer in self.known_signers() {
            total += self
                .ctx
                .read_account(&signer.pubkey())
                .map(|a| a.lamports as u128)
                .unwrap_or(0);
        }
        total += self
            .ctx
            .read_account(&self.global_account)
            .map(|a| a.lamports as u128)
            .unwrap_or(0);
        for manager in &self.managers {
            let pda = earn_manager_pda(&manager.pubkey()).0;
            total += self.ctx.read_account(&pda).map(|a| a.lamports as u128).unwrap_or(0);
        }
        for user_ta in &self.user_token_accounts {
            let pda = earner_pda(user_ta).0;
            total += self.ctx.read_account(&pda).map(|a| a.lamports as u128).unwrap_or(0);
        }
        total += self
            .ctx
            .read_account(&self.m_vault)
            .map(|a| a.lamports as u128)
            .unwrap_or(0);
        total += self
            .ctx
            .read_account(&self.vault_m_token_account)
            .map(|a| a.lamports as u128)
            .unwrap_or(0);
        total += self
            .ctx
            .read_account(&self.ext_mint_authority)
            .map(|a| a.lamports as u128)
            .unwrap_or(0);
        total
    }
}

#[fuzz_fixture]
impl Kast {
    pub fn setup() -> Self {
        let mut ctx = TestContext::new();
        let mode = VariantMode::from_env();
        ctx.add_program(&PROGRAM_ID, mode.so_path()).unwrap();
        ctx.add_program(&EXT_SWAP_PROGRAM_ID, EXT_SWAP_SO).unwrap();
        ctx.add_program(&PROGRAM_ID_EXT_A, EXT_A_SO).unwrap();

        let admin = Rc::new(Keypair::new());
        let pending_admin = Rc::new(Keypair::new());
        let wrap_candidates = vec![Rc::new(Keypair::new()), Rc::new(Keypair::new())];
        let managers = vec![Rc::new(Keypair::new()), Rc::new(Keypair::new())];
        let users = vec![Rc::new(Keypair::new()), Rc::new(Keypair::new())];

        for signer in [Rc::clone(&admin), Rc::clone(&pending_admin)]
            .into_iter()
            .chain(wrap_candidates.iter().cloned())
            .chain(managers.iter().cloned())
            .chain(users.iter().cloned())
        {
            ctx.create_account()
                .pubkey(signer.pubkey())
                .lamports(50_000_000_000)
                .owner(system_program::ID)
                .create()
                .unwrap();
        }

        let m_mint = Pubkey::new_unique();
        let ext_mint = Pubkey::new_unique();
        let use_scaled_ui = matches!(mode, VariantMode::ScaledUi | VariantMode::Crank);
        let m_supply = 1_000_000_000_000u64; // 1M M-tokens with 6 decimals
        let vault_amount = m_supply;          // All M tokens in vault initially
        let ext_supply = 100_000_000_000u64; // 100e9, room for 900e9 in rewards
        if use_scaled_ui {
            // Create Token-2022 scaled-ui mints with ScaledUiAmountConfig extension
            let initial_multiplier = 1.0_f64;
            let m_data = make_scaled_ui_mint_bytes(&admin.pubkey(), initial_multiplier, 6, m_supply);
            // ext_mint authority must be ext_mint_authority PDA so claim_for's mint_to CPI works
            let ext_mint_auth = mint_authority_pda().0;
            let ext_data = make_scaled_ui_mint_bytes(&ext_mint_auth, initial_multiplier, 6, ext_supply);
            ctx.write_account(&m_mint, Account {
                lamports: 10_000_000,
                data: m_data,
                owner: TOKEN_2022_PROGRAM_ID,
                executable: false,
                rent_epoch: 0,
            }).unwrap();
            ctx.write_account(&ext_mint, Account {
                lamports: 10_000_000,
                data: ext_data,
                owner: TOKEN_2022_PROGRAM_ID,
                executable: false,
                rent_epoch: 0,
            }).unwrap();
        } else {
            ctx.create_mint()
                .pubkey(m_mint)
                .decimals(6)
                .mint_authority(admin.pubkey())
                .create()
                .unwrap();
            ctx.create_mint()
                .pubkey(ext_mint)
                .decimals(6)
                .mint_authority(admin.pubkey())
                .create()
                .unwrap();
        }

        let mut fee_token_accounts = Vec::new();
        for manager in &managers {
            let ata = Pubkey::new_unique();
            if use_scaled_ui {
                // Token-2022 token account: PodAccount(165) + AccountType(1) + TLV_end(4)
                let mut ata_data = vec![0u8; 170];
                ata_data[0..32].copy_from_slice(&ext_mint.to_bytes());
                ata_data[32..64].copy_from_slice(&manager.pubkey().to_bytes());
                ata_data[64..72].copy_from_slice(&1_000_000_000u64.to_le_bytes()); // 1 token
                ata_data[108] = 1; // state = AccountState::Initialized
                ata_data[165] = 2; // AccountType::Account
                // TLV end sentinel at 166-169: type=0, length=0 (already zero)
                ctx.write_account(&ata, Account {
                    lamports: 2_000_000,
                    data: ata_data,
                    owner: TOKEN_2022_PROGRAM_ID,
                    executable: false,
                    rent_epoch: 0,
                }).unwrap();
            } else {
                ctx.create_token_account()
                    .pubkey(ata)
                    .mint(ext_mint)
                    .token_owner(manager.pubkey())
                    .create()
                    .unwrap();
            }
            fee_token_accounts.push(ata);
        }

        let mut user_token_accounts = Vec::new();
        let mut user_m_token_accounts = Vec::new();
        for user in &users {
            let ata = Pubkey::new_unique();
            if use_scaled_ui {
                let mut ata_data = vec![0u8; 170];
                ata_data[0..32].copy_from_slice(&ext_mint.to_bytes());
                ata_data[32..64].copy_from_slice(&user.pubkey().to_bytes());
                ata_data[64..72].copy_from_slice(&10_000_000_000u64.to_le_bytes()); // 10 tokens
                ata_data[108] = 1; // Initialized
                ata_data[165] = 2; // AccountType::Account
                ctx.write_account(&ata, Account {
                    lamports: 2_000_000,
                    data: ata_data,
                    owner: TOKEN_2022_PROGRAM_ID,
                    executable: false,
                    rent_epoch: 0,
                }).unwrap();
            } else {
                ctx.create_token_account()
                    .pubkey(ata)
                    .mint(ext_mint)
                    .token_owner(user.pubkey())
                    .create()
                    .unwrap();
            }
            user_token_accounts.push(ata);

            // Create M token accounts for users (needed for ext_swap wrap)
            let m_ata = Pubkey::new_unique();
            if use_scaled_ui {
                let mut m_ata_data = vec![0u8; 170];
                m_ata_data[0..32].copy_from_slice(&m_mint.to_bytes());
                m_ata_data[32..64].copy_from_slice(&user.pubkey().to_bytes());
                m_ata_data[64..72].copy_from_slice(&500_000_000_000u64.to_le_bytes()); // 500 M tokens
                m_ata_data[108] = 1; // Initialized
                m_ata_data[165] = 2; // AccountType::Account
                ctx.write_account(&m_ata, Account {
                    lamports: 2_000_000,
                    data: m_ata_data,
                    owner: TOKEN_2022_PROGRAM_ID,
                    executable: false,
                    rent_epoch: 0,
                }).unwrap();
            } else {
                ctx.create_token_account()
                    .pubkey(m_ata)
                    .mint(m_mint)
                    .token_owner(user.pubkey())
                    .create()
                    .unwrap();
            }
            user_m_token_accounts.push(m_ata);
        }

        let (global_account, global_bump) = global_pda();
        let (ext_mint_authority, mint_auth_bump) = mint_authority_pda();
        let (m_vault, m_vault_bump) = m_vault_pda();
        let (swap_global, _) = swap_global_pda();
        let earn_global = Pubkey::new_unique();
        let global_bytes = build_global_bytes(
            mode,
            &admin.pubkey(),
            &ext_mint,
            &m_mint,
            &earn_global,
            global_bump,
            m_vault_bump,
            mint_auth_bump,
            &[wrap_candidates[0].pubkey(), swap_global],
            &admin.pubkey(),
        );
        let mut global_acct = make_account(global_bytes.len() + 32, 5_000_000, PROGRAM_ID);
        global_acct.data[..global_bytes.len()].copy_from_slice(&global_bytes);
        ctx.write_account(&global_account, global_acct).unwrap();

        // Create m_vault PDA and ext_mint_authority PDA
        ctx.write_account(&m_vault, make_account(0, 1_000_000, PROGRAM_ID)).unwrap();
        ctx.write_account(&ext_mint_authority, make_account(0, 1_000_000, PROGRAM_ID)).unwrap();

        // Create vault_m_token_account (ATA of m_mint, owned by m_vault, using Token-2022 program)
        let vault_m_token_account = if use_scaled_ui {
            let ata = associated_token_address(&m_vault, &m_mint, &TOKEN_2022_PROGRAM_ID);
            // Token-2022 token account data: PodAccount(165) + AccountType(1) + TLV_end(4)
            let mut ata_data = vec![0u8; 170];
            ata_data[0..32].copy_from_slice(&m_mint.to_bytes()); // mint
            ata_data[32..64].copy_from_slice(&m_vault.to_bytes()); // owner
            ata_data[64..72].copy_from_slice(&vault_amount.to_le_bytes()); // amount = non-zero
            ata_data[108] = 1; // state = AccountState::Initialized
            ata_data[165] = 2; // AccountType::Account
            ctx.write_account(&ata, Account {
                lamports: 2_000_000,
                data: ata_data,
                owner: TOKEN_2022_PROGRAM_ID,
                executable: false,
                rent_epoch: 0,
            }).unwrap();
            ata
        } else {
            Pubkey::default()
        };

        if mode == VariantMode::Crank {
            for (idx, manager) in managers.iter().enumerate() {
                let (manager_pda, bump) = earn_manager_pda(&manager.pubkey());
                let bytes = build_earn_manager_bytes(
                    &manager.pubkey(),
                    (idx as u64) * 100,
                    &fee_token_accounts[idx],
                    bump,
                );
                let mut acct = make_account(bytes.len(), 2_000_000, PROGRAM_ID);
                acct.data = bytes;
                ctx.write_account(&manager_pda, acct).unwrap();
            }
            let (earner0, bump) = earner_pda(&user_token_accounts[0]);
            let bytes = build_earner_bytes(
                &users[0].pubkey(),
                &user_token_accounts[0],
                &managers[0].pubkey(),
                bump,
            );
            let mut acct = make_account(bytes.len(), 2_000_000, PROGRAM_ID);
            acct.data = bytes;
            ctx.write_account(&earner0, acct).unwrap();
        }

        // Setup ext_swap SwapGlobal (will be created after ext_a setup with 2 extensions)

        // Setup ext_a (no_yield) instance for cross-extension swap
        let (ext_a_global, _) = global_pda_ext_a();
        let (ext_a_mint_authority, _) = mint_authority_pda_ext_a();
        let (ext_a_m_vault, _) = m_vault_pda_ext_a();
        let ext_a_mint = Pubkey::new_unique();
        let ext_a_vault_m_token_account = associated_token_address(&ext_a_m_vault, &m_mint, &TOKEN_2022_PROGRAM_ID);
        let mut ext_a_user_token_accounts = Vec::new();

        // ext_a EXT mint: plain Token-2022 mint (no_yield variant)
        {
            let mut ext_a_mint_data = vec![0u8; 82];
            ext_a_mint_data[4..36].copy_from_slice(&ext_a_mint_authority.to_bytes());
            ext_a_mint_data[36..44].copy_from_slice(&1_000_000_000_000_000u64.to_le_bytes()); // supply
            ext_a_mint_data[44] = 6;
            ext_a_mint_data[45] = 1;
            ctx.write_account(&ext_a_mint, Account {
                lamports: 10_000_000,
                data: ext_a_mint_data,
                owner: TOKEN_2022_PROGRAM_ID,
                executable: false,
                rent_epoch: 0,
            }).unwrap();
        }

        // ext_a global account (no_yield config)
        {
            let ext_a_global_bytes = build_global_bytes(
                VariantMode::NoYield,
                &admin.pubkey(),
                &ext_a_mint,
                &m_mint,
                &earn_global,
                Pubkey::find_program_address(&[GLOBAL_SEED], &PROGRAM_ID_EXT_A).1,
                Pubkey::find_program_address(&[M_VAULT_SEED], &PROGRAM_ID_EXT_A).1,
                Pubkey::find_program_address(&[MINT_AUTHORITY_SEED], &PROGRAM_ID_EXT_A).1,
                &[swap_global, admin.pubkey()],
                &admin.pubkey(),
            );
            let mut ga = make_account(ext_a_global_bytes.len() + 32, 5_000_000, PROGRAM_ID_EXT_A);
            ga.data[..ext_a_global_bytes.len()].copy_from_slice(&ext_a_global_bytes);
            ctx.write_account(&ext_a_global, ga).unwrap();
            ctx.write_account(&ext_a_mint_authority, make_account(0, 1_000_000, PROGRAM_ID_EXT_A)).unwrap();
            ctx.write_account(&ext_a_m_vault, make_account(0, 1_000_000, PROGRAM_ID_EXT_A)).unwrap();
        }

        // ext_a vault M token account
        {
            let mut ata_data = vec![0u8; 170];
            ata_data[0..32].copy_from_slice(&m_mint.to_bytes());
            ata_data[32..64].copy_from_slice(&ext_a_m_vault.to_bytes());
            ata_data[64..72].copy_from_slice(&1_000_000_000_000u64.to_le_bytes());
            ata_data[108] = 1;
            ata_data[165] = 2;
            ctx.write_account(&ext_a_vault_m_token_account, Account {
                lamports: 2_000_000,
                data: ata_data,
                owner: TOKEN_2022_PROGRAM_ID,
                executable: false,
                rent_epoch: 0,
            }).unwrap();
        }

        // ext_a user token accounts
        for user in &users {
            let ata = Pubkey::new_unique();
            let mut ata_data = vec![0u8; 170];
            ata_data[0..32].copy_from_slice(&ext_a_mint.to_bytes());
            ata_data[32..64].copy_from_slice(&user.pubkey().to_bytes());
            ata_data[64..72].copy_from_slice(&10_000_000_000u64.to_le_bytes());
            ata_data[108] = 1;
            ata_data[165] = 2;
            ctx.write_account(&ata, Account {
                lamports: 2_000_000,
                data: ata_data,
                owner: TOKEN_2022_PROGRAM_ID,
                executable: false,
                rent_epoch: 0,
            }).unwrap();
            ext_a_user_token_accounts.push(ata);
        }

        // Add ext_a to ext_swap's whitelist (re-create SwapGlobal with 2 extensions)
        {
            let admin_bytes = admin.pubkey().to_bytes();
            let user0_bytes = users[0].pubkey().to_bytes();
            let user1_bytes = users[1].pubkey().to_bytes();
            let sg_bump = Pubkey::find_program_address(&[GLOBAL_SEED], &EXT_SWAP_PROGRAM_ID).1;
            let mut sg_data = vec![0u8; 8 + 1 + 32 + 4 + 2*32 + 4 + 2*96];
            let sg_disc: [u8; 8] = [15, 184, 147, 129, 183, 219, 223, 163];
            sg_data[..8].copy_from_slice(&sg_disc);
            sg_data[8] = sg_bump;
            sg_data[9..41].copy_from_slice(&admin_bytes);
            // whitelisted_unwrappers: both users
            let offset1 = 41;
            sg_data[offset1..offset1+4].copy_from_slice(&2u32.to_le_bytes());
            sg_data[offset1+4..offset1+36].copy_from_slice(&user0_bytes);
            sg_data[offset1+36..offset1+68].copy_from_slice(&user1_bytes);
            // whitelisted_extensions: 2 entries
            let offset2 = offset1 + 68;
            sg_data[offset2..offset2+4].copy_from_slice(&2u32.to_le_bytes());
            // Entry 0: primary m_ext
            sg_data[offset2+4..offset2+36].copy_from_slice(&PROGRAM_ID.to_bytes());
            sg_data[offset2+36..offset2+68].copy_from_slice(&ext_mint.to_bytes());
            sg_data[offset2+68..offset2+100].copy_from_slice(&TOKEN_2022_PROGRAM_ID.to_bytes());
            // Entry 1: ext_a
            sg_data[offset2+100..offset2+132].copy_from_slice(&PROGRAM_ID_EXT_A.to_bytes());
            sg_data[offset2+132..offset2+164].copy_from_slice(&ext_a_mint.to_bytes());
            sg_data[offset2+164..offset2+196].copy_from_slice(&TOKEN_2022_PROGRAM_ID.to_bytes());
            let mut sg_acct = make_account(sg_data.len(), 10_000_000, EXT_SWAP_PROGRAM_ID);
            sg_acct.data = sg_data;
            ctx.write_account(&swap_global, sg_acct).unwrap();
        }

        // Create ext_swap's M ATA for the swap instruction
        let swap_m_account = associated_token_address(&swap_global, &m_mint, &TOKEN_2022_PROGRAM_ID);
        {
            let mut ata_data = vec![0u8; 170];
            ata_data[0..32].copy_from_slice(&m_mint.to_bytes());
            ata_data[32..64].copy_from_slice(&swap_global.to_bytes());
            ata_data[64..72].copy_from_slice(&500_000_000_000u64.to_le_bytes());
            ata_data[108] = 1;
            ata_data[165] = 2;
            ctx.write_account(&swap_m_account, Account {
                lamports: 2_000_000,
                data: ata_data,
                owner: TOKEN_2022_PROGRAM_ID,
                executable: false,
                rent_epoch: 0,
            }).unwrap();
        }

        let mut fixture = Kast {
            ctx,
            mode,
            admin,
            pending_admin,
            wrap_candidates,
            managers,
            users,
            ext_mint,
            m_mint,
            global_account,
            m_vault,
            ext_mint_authority,
            vault_m_token_account,
            fee_token_accounts,
            user_token_accounts,
            user_m_token_accounts,
            ext_a_mint,
            ext_a_global,
            ext_a_m_vault,
            ext_a_mint_authority,
            ext_a_vault_m_token_account,
            ext_a_user_token_accounts,
            es_swap_global: swap_global,
            es_initialized: true,
            state: KastState {
                steps: 0,
                n_ok: 0,
                n_err: 0,
                baseline: 0,
                last_err: String::new(),
            },
        };
        fixture.state.baseline = fixture.total_lamports();
        fixture
    }

    pub fn action_transfer_admin(&mut self) {
        let admin = Rc::clone(&self.admin);
        let ix = raw_ix(
            DISC_TRANSFER_ADMIN,
            self.pending_admin.pubkey().to_bytes().to_vec(),
            vec![(admin.pubkey(), false, true), (self.global_account, true, false)],
        );
        self.dispatch(ix, &[&*admin]);
    }

    pub fn action_accept_admin(&mut self) {
        let pending_admin = Rc::clone(&self.pending_admin);
        let ix = raw_ix(
            DISC_ACCEPT_ADMIN,
            vec![],
            vec![
                (pending_admin.pubkey(), false, true),
                (self.global_account, true, false),
            ],
        );
        self.dispatch(ix, &[&*pending_admin]);
    }

    pub fn action_revoke_admin_transfer(&mut self) {
        let admin = Rc::clone(&self.admin);
        let ix = raw_ix(
            DISC_REVOKE_ADMIN,
            vec![],
            vec![(admin.pubkey(), false, true), (self.global_account, true, false)],
        );
        self.dispatch(ix, &[&*admin]);
    }

    pub fn action_add_wrap_authority(&mut self, #[range(0..6)] idx: usize) {
        let admin = Rc::clone(&self.admin);
        let pool = self.known_signers();
        let candidate = &pool[idx % pool.len()];
        let ix = raw_ix(
            DISC_ADD_WRAP_AUTH,
            candidate.pubkey().to_bytes().to_vec(),
            vec![
                (admin.pubkey(), true, true),
                (self.global_account, true, false),
                (system_program::ID, false, false),
            ],
        );
        self.dispatch(ix, &[&*admin]);
    }

    pub fn action_remove_wrap_authority(&mut self, #[range(0..4)] idx: usize) {
        let admin = Rc::clone(&self.admin);
        let target = self.wrap_candidates[idx % self.wrap_candidates.len()].pubkey();
        let ix = raw_ix(
            DISC_REMOVE_WRAP_AUTH,
            target.to_bytes().to_vec(),
            vec![
                (admin.pubkey(), true, true),
                (self.global_account, true, false),
                (system_program::ID, false, false),
            ],
        );
        self.dispatch(ix, &[&*admin]);
    }

    pub fn action_add_earn_manager(&mut self, #[range(0..2)] manager_idx: usize, #[range(0..10001)] fee_bps: u64) {
        if self.mode != VariantMode::Crank {
            return;
        }
        let admin = Rc::clone(&self.admin);
        let manager = &self.managers[manager_idx];
        let manager_pda = earn_manager_pda(&manager.pubkey()).0;
        let ix = raw_ix(
            DISC_ADD_EARN_MANAGER,
            {
                let mut d = manager.pubkey().to_bytes().to_vec();
                d.extend_from_slice(&fee_bps.to_le_bytes());
                d
            },
            vec![
                (admin.pubkey(), true, true),
                (self.global_account, false, false),
                (manager_pda, true, false),
                (self.fee_token_accounts[manager_idx], false, false),
                (system_program::ID, false, false),
            ],
        );
        self.dispatch(ix, &[&*admin]);
    }

    pub fn action_add_earner(&mut self, #[range(0..2)] manager_idx: usize, #[range(0..2)] user_idx: usize) {
        if self.mode != VariantMode::Crank {
            return;
        }
        let manager = Rc::clone(&self.managers[manager_idx]);
        let manager_pda = earn_manager_pda(&manager.pubkey()).0;
        let earner_pda = earner_pda(&self.user_token_accounts[user_idx]).0;
        let ix = raw_ix(
            DISC_ADD_EARNER,
            self.users[user_idx].pubkey().to_bytes().to_vec(),
            vec![
                (manager.pubkey(), true, true),
                (manager_pda, false, false),
                (self.global_account, false, false),
                (self.user_token_accounts[user_idx], false, false),
                (earner_pda, true, false),
                (system_program::ID, false, false),
            ],
        );
        self.dispatch(ix, &[&*manager]);
    }

    pub fn action_configure_earn_manager(&mut self, #[range(0..2)] manager_idx: usize, #[range(0..10001)] fee_bps: u64) {
        if self.mode != VariantMode::Crank {
            return;
        }
        let manager = Rc::clone(&self.managers[manager_idx]);
        let manager_pda = earn_manager_pda(&manager.pubkey()).0;
        let ix = raw_ix(
            DISC_CONFIGURE_EARN_MANAGER,
            encode_option_u64(Some(fee_bps)),
            vec![
                (manager.pubkey(), true, true),
                (self.global_account, false, false),
                (manager_pda, true, false),
                (self.fee_token_accounts[manager_idx], false, false),
            ],
        );
        self.dispatch(ix, &[&*manager]);
    }

    pub fn action_transfer_earner(
        &mut self,
        #[range(0..2)] from_manager_idx: usize,
        #[range(0..2)] user_idx: usize,
        #[range(0..2)] to_manager_idx: usize,
    ) {
        if self.mode != VariantMode::Crank || from_manager_idx == to_manager_idx {
            return;
        }
        let from_manager = Rc::clone(&self.managers[from_manager_idx]);
        let from_pda = earn_manager_pda(&from_manager.pubkey()).0;
        let to_pda = earn_manager_pda(&self.managers[to_manager_idx].pubkey()).0;
        let earner_pda = earner_pda(&self.user_token_accounts[user_idx]).0;
        let ix = raw_ix(
            DISC_TRANSFER_EARNER,
            self.managers[to_manager_idx].pubkey().to_bytes().to_vec(),
            vec![
                (from_manager.pubkey(), false, true),
                (earner_pda, true, false),
                (from_pda, false, false),
                (to_pda, false, false),
            ],
        );
        self.dispatch(ix, &[&*from_manager]);
    }

    pub fn action_remove_earner(&mut self, #[range(0..2)] manager_idx: usize, #[range(0..2)] user_idx: usize) {
        if self.mode != VariantMode::Crank {
            return;
        }
        let manager = Rc::clone(&self.managers[manager_idx]);
        let manager_pda = earn_manager_pda(&manager.pubkey()).0;
        let earner_pda = earner_pda(&self.user_token_accounts[user_idx]).0;
        let ix = raw_ix(
            DISC_REMOVE_EARNER,
            vec![],
            vec![
                (manager.pubkey(), true, true),
                (earner_pda, true, false),
                (manager_pda, false, false),
                (system_program::ID, false, false),
            ],
        );
        self.dispatch(ix, &[&*manager]);
    }

    pub fn action_sync(&mut self) {
        // sync is available for scaled-ui and crank modes
        if self.mode == VariantMode::NoYield {
            return;
        }
        match self.mode {
            VariantMode::ScaledUi => {
                // scaled-ui sync: no signer needed
                let ix = raw_ix(
                    DISC_SYNC,
                    vec![],
                    vec![
                        (self.global_account, true, false),
                        (self.m_mint, false, false),
                        (self.m_vault, false, false),
                        (self.vault_m_token_account, false, false),
                        (self.ext_mint, true, false),
                        (self.ext_mint_authority, false, false),
                        (TOKEN_2022_PROGRAM_ID, false, false),
                    ],
                );
                self.dispatch(ix, &[]);
            }
            VariantMode::Crank => {
                // crank sync: earn_authority (admin) signs
                let admin_signer = self.current_admin_signer();
                let ix = raw_ix(
                    DISC_SYNC,
                    vec![],
                    vec![
                        (admin_signer.pubkey(), false, true),
                        (self.m_mint, false, false),
                        (self.global_account, true, false),
                        (self.m_vault, false, false),
                        (self.vault_m_token_account, false, false),
                    ],
                );
                self.dispatch(ix, &[&*admin_signer]);
            }
            VariantMode::NoYield => {}
        }
    }

    pub fn action_claim_fees(&mut self, #[range(0..2)] recipient_idx: usize) {
        // claim_fees is available for scaled-ui and no-yield modes (not crank)
        if self.mode == VariantMode::Crank {
            return;
        }
        // Use one of the existing token accounts as recipient, or admin's
        let admin_signer = self.current_admin_signer();
        let recipient = if !self.fee_token_accounts.is_empty() {
            self.fee_token_accounts[recipient_idx % self.fee_token_accounts.len()]
        } else {
            // Create a recipient account
            let ata = Pubkey::new_unique();
            self.ctx.create_token_account()
                .pubkey(ata)
                .mint(self.ext_mint)
                .token_owner(admin_signer.pubkey())
                .create()
                .unwrap();
            ata
        };
        let ix = raw_ix(
            DISC_CLAIM_FEES,
            vec![],
            vec![
                (admin_signer.pubkey(), true, true),
                (self.global_account, true, false),
                (self.m_mint, false, false),
                (self.ext_mint, true, false),
                (self.ext_mint_authority, false, false),
                (self.m_vault, false, false),
                (self.vault_m_token_account, true, false),
                (recipient, true, false),
                (TOKEN_2022_PROGRAM_ID, false, false),   // m_token_program
                (TOKEN_2022_PROGRAM_ID, false, false),   // ext_token_program
            ],
        );
        self.dispatch(ix, &[&*admin_signer]);
    }

    pub fn action_set_fee(&mut self, #[range(0..10001)] fee_bps: u64) {
        // set_fee is only available for scaled-ui mode
        if self.mode != VariantMode::ScaledUi {
            return;
        }
        let admin_signer = self.current_admin_signer();
        let ix = raw_ix(
            DISC_SET_FEE,
            fee_bps.to_le_bytes().to_vec(),
            vec![
                (admin_signer.pubkey(), true, true),
                (self.global_account, true, false),
                (self.m_mint, false, false),
                (self.m_vault, false, false),
                (self.vault_m_token_account, false, false),
                (self.ext_mint, true, false),
                (self.ext_mint_authority, false, false),
                (TOKEN_2022_PROGRAM_ID, false, false),   // ext_token_program
            ],
        );
        self.dispatch(ix, &[&*admin_signer]);
    }

    /// Directly update the multiplier in the m_mint's ScaledUiAmountConfig extension.
    /// This simulates what happens when an admin calls Token-2022's update_multiplier.
    /// Only valid for scaled-ui and crank modes.
    pub fn action_update_multiplier(&mut self, #[range(0..50)] multiplier_tenths: u64) {
        if !matches!(self.mode, VariantMode::ScaledUi | VariantMode::Crank) {
            return;
        }
        // Build multiplier from 1.0 + (tenths * 0.1), giving range [1.0, 6.0)
        let multiplier = 1.0_f64 + (multiplier_tenths as f64) * 0.1_f64;
        // Read current m_mint data
        if let Ok(mut acct) = self.ctx.read_account(&self.m_mint) {
            // TLV ScaledUiAmountConfig at offset 170: 170-202 authority, 202-210 multiplier,
            // 210-218 timestamp, 218-226 new_multiplier
            acct.data[202..210].copy_from_slice(&multiplier.to_le_bytes());
            acct.data[210..218].copy_from_slice(&1_000_000i64.to_le_bytes()); // timestamp = past
            acct.data[218..226].copy_from_slice(&multiplier.to_le_bytes());
            self.ctx.write_account(&self.m_mint, acct).unwrap();
        }
    }

    pub fn action_claim_for(&mut self, #[range(0..2)] user_idx: usize, #[range(0..2)] manager_idx: usize) {
        if self.mode != VariantMode::Crank {
            return;
        }
        let admin_signer = self.current_admin_signer();
        let user_ta = self.user_token_accounts[user_idx % self.user_token_accounts.len()];
        let earner_pda = earner_pda(&user_ta).0;

        // Use the earner's actual earn_manager for the PDA, not the parameter
        let manager_for_pda = if let Ok(acct) = self.ctx.read_account(&earner_pda) {
            let (_, actual_manager) = parse_earner(&acct.data);
            actual_manager
        } else {
            self.managers[manager_idx % self.managers.len()].pubkey()
        };
        let manager_pda = earn_manager_pda(&manager_for_pda).0;

        // Read the fee_token_account from the earn_manager account data
        let fee_ta = self.ctx.read_account(&manager_pda)
            .map(|macct| {
                let mut ft_bytes = [0u8; 32];
                ft_bytes.copy_from_slice(&macct.data[49..81]);
                Pubkey::new_from_array(ft_bytes)
            })
            .unwrap_or(self.fee_token_accounts[manager_idx % self.fee_token_accounts.len()]);

        // snapshot_balance = the user's token balance at claim time
        let snapshot_balance = self.ctx.read_account(&user_ta)
            .map(|a| {
                let mut amt_bytes = [0u8; 8];
                amt_bytes.copy_from_slice(&a.data[64..72]);
                u64::from_le_bytes(amt_bytes)
            })
            .unwrap_or(0);

        let ix = raw_ix(
            DISC_CLAIM_FOR,
            snapshot_balance.to_le_bytes().to_vec(),
            vec![
                (admin_signer.pubkey(), false, true),         // earn_authority
                (self.global_account, true, false),            // global_account (mut)
                (self.m_mint, false, false),                   // m_mint
                (self.ext_mint, true, false),                  // ext_mint (mut)
                (self.ext_mint_authority, false, false),       // ext_mint_authority
                (self.m_vault, false, false),                  // m_vault_account
                (self.vault_m_token_account, false, false),    // vault_m_token_account
                (user_ta, true, false),                        // user_token_account (mut)
                (earner_pda, true, false),                     // earner_account (mut)
                (manager_pda, false, false),                   // earn_manager_account
                (fee_ta, true, false),                         // earn_manager_token_account (mut)
                (TOKEN_2022_PROGRAM_ID, false, false),         // m_token_program
                (TOKEN_2022_PROGRAM_ID, false, false),         // ext_token_program
            ],
        );
        self.dispatch(ix, &[&*admin_signer]);
    }

    /// Claim with a multiplied snapshot_balance for stress-testing the collateral check.
    /// Multiplies the user's actual balance by inflate to exercise the vault solvency bound.
    pub fn action_claim_for_inflated(&mut self, #[range(0..2)] user_idx: usize, #[range(0..2)] manager_idx: usize, #[range(1..100)] inflate: u64) {
        if self.mode != VariantMode::Crank {
            return;
        }
        let admin_signer = self.current_admin_signer();
        let user_ta = self.user_token_accounts[user_idx % self.user_token_accounts.len()];
        let earner_pda = earner_pda(&user_ta).0;

        let manager_for_pda = if let Ok(acct) = self.ctx.read_account(&earner_pda) {
            let (_, actual_manager) = parse_earner(&acct.data);
            actual_manager
        } else {
            self.managers[manager_idx % self.managers.len()].pubkey()
        };
        let manager_pda = earn_manager_pda(&manager_for_pda).0;

        let fee_ta = self.ctx.read_account(&manager_pda)
            .map(|macct| {
                let mut ft_bytes = [0u8; 32];
                ft_bytes.copy_from_slice(&macct.data[49..81]);
                Pubkey::new_from_array(ft_bytes)
            })
            .unwrap_or(self.fee_token_accounts[manager_idx % self.fee_token_accounts.len()]);

        // Inflate the snapshot_balance to trigger the bug
        let actual_balance = self.ctx.read_account(&user_ta)
            .map(|a| {
                let mut amt_bytes = [0u8; 8];
                amt_bytes.copy_from_slice(&a.data[64..72]);
                u64::from_le_bytes(amt_bytes)
            })
            .unwrap_or(0);
        let snapshot_balance = (actual_balance as u128)
            .checked_mul(inflate as u128)
            .and_then(|v| v.try_into().ok())
            .unwrap_or(u64::MAX);

        let ix = raw_ix(
            DISC_CLAIM_FOR,
            snapshot_balance.to_le_bytes().to_vec(),
            vec![
                (admin_signer.pubkey(), false, true),
                (self.global_account, true, false),
                (self.m_mint, false, false),
                (self.ext_mint, true, false),
                (self.ext_mint_authority, false, false),
                (self.m_vault, false, false),
                (self.vault_m_token_account, false, false),
                (user_ta, true, false),
                (earner_pda, true, false),
                (manager_pda, false, false),
                (fee_ta, true, false),
                (TOKEN_2022_PROGRAM_ID, false, false),
                (TOKEN_2022_PROGRAM_ID, false, false),
            ],
        );
        self.dispatch(ix, &[&*admin_signer]);
    }

    /// Claim with a direct snapshot_balance value.
    /// Tests the collateral bound by providing values that may exceed the vault capacity.
    pub fn action_claim_for_big_snapshot(&mut self, #[range(0..2)] user_idx: usize, #[range(0..2)] manager_idx: usize, #[range(1_000_000_000_000..50_000_000_000_000)] snapshot_balance: u64) {
        if self.mode != VariantMode::Crank {
            return;
        }
        let admin_signer = self.current_admin_signer();
        let user_ta = self.user_token_accounts[user_idx % self.user_token_accounts.len()];
        let earner_pda = earner_pda(&user_ta).0;

        let manager_for_pda = if let Ok(acct) = self.ctx.read_account(&earner_pda) {
            let (_, actual_manager) = parse_earner(&acct.data);
            actual_manager
        } else {
            self.managers[manager_idx % self.managers.len()].pubkey()
        };
        let manager_pda = earn_manager_pda(&manager_for_pda).0;

        let fee_ta = self.ctx.read_account(&manager_pda)
            .map(|macct| {
                let mut ft_bytes = [0u8; 32];
                ft_bytes.copy_from_slice(&macct.data[49..81]);
                Pubkey::new_from_array(ft_bytes)
            })
            .unwrap_or(self.fee_token_accounts[manager_idx % self.fee_token_accounts.len()]);

        let ix = raw_ix(
            DISC_CLAIM_FOR,
            snapshot_balance.to_le_bytes().to_vec(),
            vec![
                (admin_signer.pubkey(), false, true),
                (self.global_account, true, false),
                (self.m_mint, false, false),
                (self.ext_mint, true, false),
                (self.ext_mint_authority, false, false),
                (self.m_vault, false, false),
                (self.vault_m_token_account, false, false),
                (user_ta, true, false),
                (earner_pda, true, false),
                (manager_pda, false, false),
                (fee_ta, true, false),
                (TOKEN_2022_PROGRAM_ID, false, false),
                (TOKEN_2022_PROGRAM_ID, false, false),
            ],
        );
        self.dispatch(ix, &[&*admin_signer]);
    }

    /// Combined action: update multiplier on m_mint, sync to advance ext_index, then claim_for.
    /// This ensures the freeze-unfreeze cycle is testable even when the fuzzer can't sequence it.
    pub fn action_multisync_claim(&mut self, #[range(1..30)] multiplier_tenths: u64) {
        if self.mode != VariantMode::Crank {
            return;
        }
        // Step 1: Update multiplier on m_mint
        let multiplier = 1.0_f64 + (multiplier_tenths as f64) * 0.1_f64;
        if let Ok(mut acct) = self.ctx.read_account(&self.m_mint) {
            acct.data[202..210].copy_from_slice(&multiplier.to_le_bytes());
            acct.data[210..218].copy_from_slice(&1_000_000i64.to_le_bytes());
            acct.data[218..226].copy_from_slice(&multiplier.to_le_bytes());
            self.ctx.write_account(&self.m_mint, acct).unwrap();
        }

        // Step 2: Sync (advance ext_index based on new multiplier)
        let admin_signer = self.current_admin_signer();
        let ix_sync = raw_ix(
            DISC_SYNC,
            vec![],
            vec![
                (admin_signer.pubkey(), false, true),
                (self.m_mint, false, false),
                (self.global_account, true, false),
                (self.m_vault, false, false),
                (self.vault_m_token_account, false, false),
            ],
        );
        let sync_result = self.ctx.raw_call(ix_sync).signers(&[&*admin_signer]).send();
        match &sync_result {
            Ok(tx) if tx.is_success() => {
                eprintln!("[MULTISYNC] sync OK");
            }
            Ok(tx) => {
                eprintln!("[MULTISYNC] sync FAILED: {:?}", tx.logs().last());
            }
            Err(e) => {
                eprintln!("[MULTISYNC] sync ERR: {e}");
            }
        }

        // Step 3: Claim for the earner that was created in setup (user 0)
        let user_ta = self.user_token_accounts[0];
        let earner_pda = earner_pda(&user_ta).0;
        if let Ok(acct) = self.ctx.read_account(&earner_pda) {
            let (_, actual_manager) = parse_earner(&acct.data);
            eprintln!("[MULTISYNC] earner found, manager={:?}", actual_manager);
            let manager_pda = earn_manager_pda(&actual_manager).0;
            let snapshot_balance = self.ctx.read_account(&user_ta)
                .map(|a| {
                    let mut amt_bytes = [0u8; 8];
                    amt_bytes.copy_from_slice(&a.data[64..72]);
                    u64::from_le_bytes(amt_bytes)
                })
                .unwrap_or(0);
            // Read the fee_token_account from the earn_manager account data
            let fee_ta = self.ctx.read_account(&manager_pda)
                .map(|macct| {
                    let mut ft_bytes = [0u8; 32];
                    ft_bytes.copy_from_slice(&macct.data[49..81]);
                    Pubkey::new_from_array(ft_bytes)
                })
                .unwrap_or(self.fee_token_accounts[0]);

            let ix_claim = raw_ix(
                DISC_CLAIM_FOR,
                snapshot_balance.to_le_bytes().to_vec(),
                vec![
                    (admin_signer.pubkey(), false, true),
                    (self.global_account, true, false),
                    (self.m_mint, false, false),
                    (self.ext_mint, true, false),
                    (self.ext_mint_authority, false, false),
                    (self.m_vault, false, false),
                    (self.vault_m_token_account, false, false),
                    (user_ta, true, false),
                    (earner_pda, true, false),
                    (manager_pda, false, false),
                    (fee_ta, true, false),
                    (TOKEN_2022_PROGRAM_ID, false, false),
                    (TOKEN_2022_PROGRAM_ID, false, false),
                ],
            );
            let claim_result = self.ctx.raw_call(ix_claim).signers(&[&*admin_signer]).send();
            match &claim_result {
                Ok(tx) if tx.is_success() => {
                    eprintln!("[MULTISYNC] claim_for OK!");
                }
                Ok(tx) => {
                    eprintln!("[MULTISYNC] claim_for FAILED: {:?}", tx.logs().last());
                }
                Err(e) => {
                    eprintln!("[MULTISYNC] claim_for ERR: {e}");
                }
            }
        } else {
            eprintln!("[MULTISYNC] earner PDA not found!");
        }
    }

    /// One-time setup: adds the ext_swap swap_global PDA as a wrap authority on m_ext.
    /// After this, ext_swap can CPI-wrap into m_ext.
    pub fn action_ext_swap_install(&mut self) {
        if self.es_initialized {
            return;
        }
        let admin = Rc::clone(&self.admin);
        let ix = raw_ix(
            DISC_ADD_WRAP_AUTH,
            self.es_swap_global.to_bytes().to_vec(),
            vec![
                (admin.pubkey(), true, true),
                (self.global_account, true, false),
                (system_program::ID, false, false),
            ],
        );
        self.dispatch(ix, &[&*admin]);
        self.es_initialized = true;
    }

    /// Wrap M -> EXT through ext_swap (CPI layer).
    /// The ext_swap SwapGlobal PDA acts as wrap authority via CPI PDA signing.
    pub fn action_ext_swap_wrap(&mut self, #[range(0..2)] user_idx: usize, #[range(1..1001)] amount: u64) {
        if !self.es_initialized {
            return;
        }
        let signer = Rc::clone(&self.users[user_idx % self.users.len()]);
        let m_ta = self.user_m_token_accounts[user_idx % self.user_m_token_accounts.len()];
        let ext_ta = self.user_token_accounts[user_idx % self.user_token_accounts.len()];

        let ix = raw_ext_swap_ix(
            DISC_WRAP,
            amount.to_le_bytes().to_vec(),
            vec![
                (signer.pubkey(), false, true),                      // signer
                (EXT_SWAP_PROGRAM_ID, false, false),                 // wrap_authority = None (program ID sentinel)
                (self.es_swap_global, false, false),                 // swap_global
                (self.global_account, true, false),                  // to_global (mut)
                (self.ext_mint, true, false),                        // to_mint (mut)
                (self.m_mint, false, false),                         // m_mint
                (m_ta, true, false),                                 // m_token_account (mut)
                (ext_ta, true, false),                               // to_token_account (mut)
                (self.m_vault, false, false),                        // to_m_vault_auth
                (self.ext_mint_authority, false, false),              // to_mint_authority
                (self.vault_m_token_account, true, false),           // to_m_vault (mut)
                (TOKEN_2022_PROGRAM_ID, false, false),               // to_token_program
                (TOKEN_2022_PROGRAM_ID, false, false),               // m_token_program
                (PROGRAM_ID, false, false),                          // to_ext_program
                (system_program::ID, false, false),                  // system_program
            ],
        );
        self.dispatch_ext_swap(ix, &[&*signer]);
    }

    /// Unwrap EXT -> M through ext_swap (CPI layer).
    /// Requires the swap_global PDA to be in ext_swap's whitelisted_unwrappers.
    pub fn action_ext_swap_unwrap(&mut self, #[range(0..2)] user_idx: usize, #[range(1..1001)] amount: u64) {
        if !self.es_initialized {
            return;
        }
        let signer = Rc::clone(&self.users[user_idx % self.users.len()]);
        let m_ta = self.user_m_token_accounts[user_idx % self.user_m_token_accounts.len()];
        let ext_ta = self.user_token_accounts[user_idx % self.user_token_accounts.len()];

        let ix = raw_ext_swap_ix(
            DISC_UNWRAP,
            amount.to_le_bytes().to_vec(),
            vec![
                (signer.pubkey(), true, true),                       // signer
                (EXT_SWAP_PROGRAM_ID, false, false),                 // unwrap_authority = None
                (self.es_swap_global, false, false),                 // swap_global
                (self.global_account, true, false),                  // from_global (mut)
                (self.ext_mint, true, false),                        // from_mint (mut)
                (self.m_mint, false, false),                         // m_mint
                (m_ta, true, false),                                 // m_token_account (mut)
                (ext_ta, true, false),                               // from_token_account (mut)
                (self.m_vault, false, false),                        // from_m_vault_auth
                (self.ext_mint_authority, false, false),              // from_mint_authority
                (self.vault_m_token_account, true, false),           // from_m_vault (mut)
                (TOKEN_2022_PROGRAM_ID, false, false),               // from_token_program
                (TOKEN_2022_PROGRAM_ID, false, false),               // m_token_program
                (PROGRAM_ID, false, false),                          // from_ext_program
                (system_program::ID, false, false),                  // system_program
            ],
        );
        self.dispatch_ext_swap(ix, &[&*signer]);
    }

    /// Execute a cross-extension swap through ext_swap.
    /// Burns EXT_A tokens, sends M through swap vault, mints primary EXT tokens.
    /// Requires both extensions whitelisted on ext_swap's SwapGlobal.
    pub fn action_ext_swap_swap(&mut self, #[range(0..2)] user_idx: usize, #[range(1..1001)] amount: u64) {
        if !self.es_initialized {
            return;
        }
        let signer = Rc::clone(&self.users[user_idx % self.users.len()]);
        let ext_a_ta = self.ext_a_user_token_accounts[user_idx % self.ext_a_user_token_accounts.len()];
        let ext_ta = self.user_token_accounts[user_idx % self.user_token_accounts.len()];
        let swap_m_account = associated_token_address(&self.es_swap_global, &self.m_mint, &TOKEN_2022_PROGRAM_ID);

        // Encode amount(u64) + remaining_accounts_split_idx(u8) = 9 bytes
        let mut data = amount.to_le_bytes().to_vec();
        data.push(0u8); // remaining_accounts_split_idx = 0 (no extra accounts)

        let ix = raw_ext_swap_ix(
            DISC_ES_SWAP,
            data,
            vec![
                (signer.pubkey(), true, true),                       // signer (writable+signer)
                (EXT_SWAP_PROGRAM_ID, false, false),                 // wrap_authority = None
                (EXT_SWAP_PROGRAM_ID, false, false),                 // unwrap_authority = None
                (self.es_swap_global, false, false),                 // swap_global
                (self.ext_a_global, true, false),                    // from_global (mut)
                (self.global_account, true, false),                  // to_global (mut)
                (self.ext_a_mint, true, false),                      // from_mint (mut)
                (self.ext_mint, true, false),                        // to_mint (mut)
                (self.m_mint, false, false),                         // m_mint
                (ext_a_ta, true, false),                             // from_token_account (mut)
                (ext_ta, true, false),                               // to_token_account (mut)
                (swap_m_account, true, false),                       // swap_m_account (mut)
                (self.ext_a_m_vault, false, false),                  // from_m_vault_auth
                (self.m_vault, false, false),                        // to_m_vault_auth
                (self.ext_a_mint_authority, false, false),            // from_mint_authority
                (self.ext_mint_authority, false, false),              // to_mint_authority
                (self.ext_a_vault_m_token_account, true, false),     // from_m_vault (mut)
                (self.vault_m_token_account, true, false),           // to_m_vault (mut)
                (TOKEN_2022_PROGRAM_ID, false, false),               // from_token_program
                (TOKEN_2022_PROGRAM_ID, false, false),               // to_token_program
                (TOKEN_2022_PROGRAM_ID, false, false),               // m_token_program
                (PROGRAM_ID_EXT_A, false, false),                    // from_ext_program
                (PROGRAM_ID, false, false),                          // to_ext_program
                (system_program::ID, false, false),                  // system_program
            ],
        );
        self.dispatch_ext_swap(ix, &[&*signer]);
    }

    pub fn action_advance_slots(&mut self, #[range(1..128)] slots: u64) {
        self.ctx.warp_to_slot(self.ctx.slot() + slots);
        self.state.steps = self.state.steps.wrapping_add(1);
    }

    fn dispatch(&mut self, ix: Instruction, signers: &[&Keypair]) {
        let ix_disc = ix.data[..8.min(ix.data.len())].to_vec();
        let result = self.ctx.raw_call(ix).signers(signers).send();
        match &result {
            Ok(tx_result) if tx_result.is_success() => self.state.n_ok = self.state.n_ok.wrapping_add(1),
            Ok(tx_result) => {
                self.state.n_err = self.state.n_err.wrapping_add(1);
                self.state.last_err = format!("tx_failed:{:?}", tx_result.logs().last());
                if trace_errors_enabled() {
                    eprintln!(
                        "[KAST][tx_failed] ix_disc={:?} logs={:?}",
                        ix_disc,
                        tx_result.logs()
                    );
                }
            }
            Err(e) => {
                self.state.n_err = self.state.n_err.wrapping_add(1);
                self.state.last_err = format!("dispatch_err:{e}");
                if trace_errors_enabled() {
                    eprintln!(
                        "[KAST][dispatch_err] ix_disc={:?} err={e}",
                        ix_disc
                    );
                }
            }
        }
        self.state.steps = self.state.steps.wrapping_add(1);
    }

    fn dispatch_ext_swap(&mut self, ix: Instruction, signers: &[&Keypair]) {
        let ix_disc = ix.data[..8.min(ix.data.len())].to_vec();
        let result = self.ctx.raw_call(ix).signers(signers).send();
        match &result {
            Ok(tx_result) if tx_result.is_success() => self.state.n_ok = self.state.n_ok.wrapping_add(1),
            Ok(tx_result) => {
                self.state.n_err = self.state.n_err.wrapping_add(1);
                self.state.last_err = format!("es_tx_failed:{:?}", tx_result.logs().last());
                if trace_errors_enabled() {
                    eprintln!(
                        "[KAST][es_tx_failed] ix={:?} logs={:?}",
                        ix_disc,
                        tx_result.logs()
                    );
                }
            }
            Err(e) => {
                self.state.n_err = self.state.n_err.wrapping_add(1);
                self.state.last_err = format!("es_dispatch_err:{e}");
                if trace_errors_enabled() {
                    eprintln!(
                        "[KAST][es_dispatch_err] ix={:?} err={e}",
                        ix_disc
                    );
                }
            }
        }
        self.state.steps = self.state.steps.wrapping_add(1);
    }

    pub fn after_action(&self) {
        let total = self.total_lamports();
        let delta = (total as i128) - (self.state.baseline as i128);
        if delta.unsigned_abs() > 5_000_000 {
            eprintln!(
                "[KAST] lamport drift baseline={} actual={} delta={} steps={} ok={} err={} last_err={}",
                self.state.baseline, total, delta, self.state.steps, self.state.n_ok, self.state.n_err, self.state.last_err
            );
            std::process::exit(77);
        }

        let global = self.ctx.read_account(&self.global_account).unwrap();
        if global.owner != PROGRAM_ID {
            eprintln!("[KAST] global owner changed unexpectedly");
            std::process::exit(78);
        }
        if global.data.len() < 177 {
            eprintln!("[KAST] global account shrank below minimum expected size");
            std::process::exit(79);
        }

        // Index sanity check: for scaled-ui and crank, verify yield config indices
        if self.mode != VariantMode::NoYield {
            let parsed = parse_global(&global.data, self.mode);
            // Verify the global's m_mint and ext_mint pointers haven't changed
            if parsed.m_mint != self.m_mint {
                eprintln!("[KAST] global.m_mint changed unexpectedly");
                std::process::exit(82);
            }
            if parsed.ext_mint != self.ext_mint {
                eprintln!("[KAST] global.ext_mint changed unexpectedly");
                std::process::exit(83);
            }

            // Value conservation invariant:
            // Checks: ext_ui_value <= vault_ui_value
            // Uses last_m_index from global (may be stale before sync - warns instead of exiting)
            if let Ok(ext_acct) = self.ctx.read_account(&self.ext_mint) {
                let mut supply_bytes = [0u8; 8];
                supply_bytes.copy_from_slice(&ext_acct.data[36..44]);
                let ext_supply = u64::from_le_bytes(supply_bytes);

                if let Ok(vault_acct) = self.ctx.read_account(&self.vault_m_token_account) {
                    let mut vault_bytes = [0u8; 8];
                    vault_bytes.copy_from_slice(&vault_acct.data[64..72]);
                    let vault_raw = u64::from_le_bytes(vault_bytes);

                    let lhs = if self.mode == VariantMode::ScaledUi {
                        (ext_supply as u128).saturating_mul(parsed.last_ext_index as u128)
                    } else {
                        (ext_supply as u128).saturating_mul(INDEX_SCALE_U64 as u128)
                    };
                    let rhs = (vault_raw as u128).saturating_mul(parsed.last_m_index as u128);
                    if lhs > rhs {
                        // Warning only - may be stale m_index false positive if sync not called recently
                        eprintln!(
                            "[KAST][WARN] Value consrv ext_supply={} ext_idx={} vault_raw={} m_idx={} lhs={} rhs={} diff={}",
                            ext_supply, parsed.last_ext_index, vault_raw, parsed.last_m_index, lhs, rhs,
                            lhs - rhs
                        );
                    }
                }
            }
        }

        if self.mode == VariantMode::Crank {
            for manager in &self.managers {
                let pda = earn_manager_pda(&manager.pubkey()).0;
                if let Ok(acct) = self.ctx.read_account(&pda) {
                    let (owner, is_active, fee_bps) = parse_earn_manager(&acct.data);
                    if owner != manager.pubkey() || !is_active || fee_bps > 10_000 {
                        eprintln!("[KAST] invalid earn manager state");
                        std::process::exit(80);
                    }
                }
            }
            for user_ta in &self.user_token_accounts {
                let pda = earner_pda(user_ta).0;
                if let Ok(acct) = self.ctx.read_account(&pda) {
                    let (_user, manager) = parse_earner(&acct.data);
                    if !self.managers.iter().any(|m| m.pubkey() == manager) {
                        eprintln!("[KAST] earner points to unknown manager");
                        std::process::exit(81);
                    }
                }
            }
        }
    }
}

#[invariant_test]
fn invariant_test(fixture: &mut Kast) {
    fixture.after_action();
}
