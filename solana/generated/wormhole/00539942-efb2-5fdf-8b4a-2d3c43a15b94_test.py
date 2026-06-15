"""Generated fail-closed Solana verifier for 00539942-efb2-5fdf-8b4a-2d3c43a15b94."""

import json


CANDIDATE = json.loads("""{
  \"actors\": [
    {
      \"constraints\": [
        \"not_authorized\",
        \"funded\"
      ],
      \"role\": \"attacker\"
    }
  ],
  \"campaign_id\": \"semantic-wormhole\",
  \"candidate_id\": \"00539942-efb2-5fdf-8b4a-2d3c43a15b94\",
  \"candidate_schema_version\": 4,
  \"chain\": \"solana\",
  \"entrypoint\": {
    \"file\": \"solana/modules/nft_bridge/program/src/api/transfer.rs\",
    \"kind\": \"solana_instruction\",
    \"line\": 113,
    \"name\": \"transfer_native\",
    \"selector_or_discriminator\": \"0x03d2945ea1460856\"
  },
  \"impact_oracle\": {
    \"measured\": false,
    \"metric\": \"TOKEN_DELTA\",
    \"threshold\": \"non_fee_positive_delta_or_bounded_tvs\"
  },
  \"invariant\": {
    \"expected_violation\": \"value_moves_without_valid_message_or_source_accounting\",
    \"id\": \"bridge_accounting\",
    \"predicate\": \"released_or_minted_assets_require_authorized_source_lock_or_burn\"
  },
  \"provenance\": {
    \"evidence\": [
      \"solana/modules/nft_bridge/program/src/api/transfer.rs\"
    ],
    \"source\": \"semantic_recon\",
    \"trusted\": false
  },
  \"sequence\": [
    {
      \"call\": \"transfer_native\",
      \"params\": {},
      \"sender\": \"attacker\"
    }
  ],
  \"source_ref\": {
    \"file\": \"solana/modules/nft_bridge/program/src/api/transfer.rs\",
    \"repo\": \"sources/wormhole/repo\",
    \"symbol\": \"transfer_native\"
  },
  \"state_bindings\": {
    \"accounts\": {},
    \"contracts\": {},
    \"storage_slots\": {},
    \"token_accounts\": {}
  },
  \"target_pinned\": true,
  \"target_slug\": \"wormhole\"
}""")


def test_candidate_requires_real_bindings():
    print("CANDIDATE_ID:", CANDIDATE["candidate_id"])
    print("TARGET_SLUG:", CANDIDATE["target_slug"])
    print("MEASURED_DELTA_LAMPORTS:0")
    assert CANDIDATE["entrypoint"].get("selector_or_discriminator")
    raise AssertionError("candidate-specific account bindings required before impact proof")
