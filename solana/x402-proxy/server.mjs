#!/usr/bin/env node
/**
 * Local JSON-RPC proxy → QuickNode x402 Solana mainnet.
 *
 * Exposes plain HTTP so solana-test-validator --url and NSS solana_rpc_available()
 * work without API keys. Wallet auth + x402 payment handled by @quicknode/x402.
 *
 * Env:
 *   X402_PROXY_PORT          — listen port (default 18989; avoids NSS API test port 18789)
 *   X402_PROXY_HOST          — bind address (default 127.0.0.1)
 *   X402_BASE_URL            — x402 gateway (default https://x402.quicknode.com)
 *   X402_RPC_NETWORK         — upstream slug (default solana-mainnet)
 *   X402_PAYMENT_NETWORK     — CAIP-2 payment chain (default solana devnet for free tier)
 *   X402_PAYMENT_MODEL       — credit-drawdown | pay-per-request (default credit-drawdown)
 *   SOLANA_KEYPAIR_FILE      — path to id.json (default ./.wallet/id.json, not system id.json)
 *   SOLANA_KEYPAIR           — inline JSON array (overrides file; CI secret pattern)
 */

import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PROXY_ROOT = dirname(fileURLToPath(import.meta.url));
const DEFAULT_KEYPAIR = join(PROXY_ROOT, ".wallet", "id.json");
import { createKeyPairSignerFromBytes } from "@solana/signers";
import { createQuicknodeX402Client } from "@quicknode/x402";

const HOST = process.env.X402_PROXY_HOST || "127.0.0.1";
const PORT = Number(process.env.X402_PROXY_PORT || "18989");
const BASE_URL = (process.env.X402_BASE_URL || "https://x402.quicknode.com").replace(/\/$/, "");
const RPC_NETWORK = process.env.X402_RPC_NETWORK || "solana-mainnet";
const PAYMENT_NETWORK =
  process.env.X402_PAYMENT_NETWORK || "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1";
const PAYMENT_MODEL = process.env.X402_PAYMENT_MODEL || "credit-drawdown";
const UPSTREAM = `${BASE_URL}/${RPC_NETWORK}`;

async function loadKeypairSigner() {
  let raw;
  if (process.env.SOLANA_KEYPAIR?.trim()) {
    raw = process.env.SOLANA_KEYPAIR.trim();
  } else {
    const file = process.env.SOLANA_KEYPAIR_FILE || DEFAULT_KEYPAIR;
    raw = readFileSync(file, "utf8");
  }

  const bytes = Uint8Array.from(JSON.parse(raw));
  if (bytes.length !== 64) {
    throw new Error(`Expected 64-byte Solana keypair, got ${bytes.length}`);
  }
  return createKeyPairSignerFromBytes(bytes);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

async function main() {
  const svmSigner = await loadKeypairSigner();
  const client = await createQuicknodeX402Client({
    baseUrl: BASE_URL,
    network: PAYMENT_NETWORK,
    svmSigner,
    siwxSigner: svmSigner,
    paymentModel: PAYMENT_MODEL,
    preAuth: PAYMENT_MODEL === "credit-drawdown",
  });

  const server = createServer(async (req, res) => {
    if (req.method === "GET" && req.url === "/health") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: true, upstream: UPSTREAM, paymentNetwork: PAYMENT_NETWORK }));
      return;
    }

    if (req.method !== "POST") {
      res.writeHead(405, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "POST JSON-RPC only" }));
      return;
    }

    try {
      const body = await readBody(req);
      const upstream = await client.fetch(UPSTREAM, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      const text = await upstream.text();
      res.writeHead(upstream.status, {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
      });
      res.end(text);
    } catch (err) {
      res.writeHead(502, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "x402_upstream_failed", message: String(err?.message || err) }));
    }
  });

  server.listen(PORT, HOST, () => {
    console.error(
      `nss-x402-proxy wallet ${svmSigner.address} → http://${HOST}:${PORT} → ${UPSTREAM}`,
    );
    console.error(`payment ${PAYMENT_NETWORK} model=${PAYMENT_MODEL} (1M free credits/mo per wallet)`);
    console.error(`export SOLANA_MAINNET_RPC_URL=http://${HOST}:${PORT}`);
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});