/**
 * NSS campaign probes — Lombard cross-layer v6.51 round 2
 * SIG-XR-003-EVM-DIVERGENCE — Mailbox retry semantics on a revert-throwing handler,
 *   contrasted against the Solana Handled-before-CPI roll-back model.
 *
 * Properties pinned here:
 *   PROP-XR-EVM-006 — Mailbox.deliverAndHandle try/catch semantics:
 *     * A revert-throwing handler does NOT bubble the failure to deliverAndHandle's
 *       caller. The tx reverts are absorbed in the catch; the message remains
 *       `Delivered` (re-attemptable) because `handledPayload[payloadHash]` only flips
 *       to true on success.
 *     * A successful subsequent deliverAndHandle on the same payload still gates
 *       re-delivery via `deliveredPayload[payloadHash]`, but emits a fresh
 *       `MessageHandled` and the handler may observe the body again (no native
 *       per-recipient dedup, an explicit reentrancy-via-replay vector).
 *
 *   PROP-XR-EVM-007 — AssetRouter.changeBascule(address(0)) admin path:
 *     * DEFAULT_ADMIN_ROLE alone can disable the Bascule by routing through
 *       _changeBascule(newVal = 0) inside changeBascule.
 *     * With bascule disabled, _confirmMint skips validateMint entirely,
 *       allowing mint without proof. The same admin role is the acting role
 *       for changeMailbox, changeOracle, setBasculeGmp; this is the single
 *       trust point for the bridge mint path.
 */
import { ethers, network } from 'hardhat';
import { expect } from 'chai';
import { takeSnapshot, SnapshotRestorer } from '@nomicfoundation/hardhat-toolbox/network-helpers';
import {
  Addressable,
  ASSETS_MODULE_ADDRESS,
  BITCOIN_CHAIN_ID,
  BTC_STAKING_MODULE_ADDRESS,
  CHAIN_ID,
  deployContract,
  encode,
  getGMPPayload,
  getPayloadForAction,
  getSignersWithPrivateKeys,
  LEDGER_CHAIN_ID,
  LEDGER_MAILBOX,
  MINT_SELECTOR,
  NEW_VALSET,
  randomBigInt,
  rawSign,
  Signer,
  signPayload
} from '../helpers';
import {
  AssetRouter,
  Consortium,
  GMPBasculeV1,
  GMPHandlerMock,
  IGMPBascule,
  Mailbox,
  StakedLBTC
} from '../typechain-types';

const VERY_BIG_FEE = 9999_9999_9999n;
const TOPIC_MESSAGE_HANDLED = ethers.id('MessageHandled(bytes32,address,bytes)');
const TOPIC_MESSAGE_RECEIVED = ethers.id('MessageReceived(bytes)');
const TOPIC_MESSAGE_HANDLE_ERROR = ethers.id('MessageHandleError(bytes32,address,string,bytes)');

describe('NSS PROP-XR-EVM-006 / PROP-XR-EVM-007 (cross-layer divergence)', function () {
  this.timeout(180_000);

  let owner: Signer,
    notary1: Signer,
    notary2: Signer,
    mintReporter: Signer,
    trustedSigner: Signer,
    signer1: Signer,
    signer2: Signer,
    dCaller: Signer;
  let consortium: Consortium & Addressable;
  let smailbox: Mailbox & Addressable;
  let dmailbox: Mailbox & Addressable;
  let handlerMock: GMPHandlerMock & Addressable;
  let lChainId: string;
  let sMailboxBytes: string;
  let snapshot: SnapshotRestorer;

  before(async () => {
    await network.provider.request({ method: 'hardhat_reset', params: [] });
    [owner, notary1, notary2, mintReporter, trustedSigner, signer1, signer2, dCaller] =
      await getSignersWithPrivateKeys();

    const { chainId } = await ethers.provider.getNetwork();
    lChainId = encode(['uint256'], [chainId]);

    consortium = await deployContract<Consortium & Addressable>('Consortium', [owner.address], true, {
      initializer: 'initialize',
      unsafeAllow: ['missing-initializer-call', 'incorrect-initializer-order']
    });
    consortium.address = await consortium.getAddress();
    await consortium
      .connect(owner)
      .setInitialValidatorSet(
        getPayloadForAction([1, [notary1.publicKey, notary2.publicKey], [1, 1], 2, 1], NEW_VALSET)
      );

    smailbox = await deployContract<Mailbox & Addressable>(
      'Mailbox',
      [owner.address, consortium.address, 0n, 0n],
      true,
      { initializer: 'initialize', unsafeAllow: ['missing-initializer-call', 'incorrect-initializer-order'] }
    );
    smailbox.address = await smailbox.getAddress();
    sMailboxBytes = encode(['address'], [smailbox.address]);

    dmailbox = await deployContract<Mailbox & Addressable>(
      'Mailbox',
      [owner.address, consortium.address, 0n, 0n],
      true,
      { initializer: 'initialize', unsafeAllow: ['missing-initializer-call', 'incorrect-initializer-order'] }
    );
    dmailbox.address = await dmailbox.getAddress();
    await smailbox.connect(owner).setDefaultMaxPayloadSize(1000);
    await dmailbox.connect(owner).setDefaultMaxPayloadSize(1000);
    await smailbox.connect(owner).enableMessagePath(lChainId, sMailboxBytes, 3);
    await dmailbox.connect(owner).enableMessagePath(lChainId, sMailboxBytes, 2);

    handlerMock = await deployContract<GMPHandlerMock & Addressable>('GMPHandlerMock', [true], false);
    handlerMock.address = await handlerMock.getAddress();

    snapshot = await takeSnapshot();
  });

  describe('PROP-XR-EVM-006 — Mailbox handler revert swallowed, payload re-attemptable', function () {
    let payload: string;
    let proof: string;
    let payloadHash: string;
    let body: string;

    beforeEach(async () => {
      await snapshot.restore();
      const recipient = encode(['address'], [handlerMock.address]);
      body = ethers.hexlify(ethers.toUtf8Bytes('NSS-XR-EVM-006'));
      const tx = await smailbox
        .connect(signer1)
        .send(lChainId, recipient, encode(['address'], [ethers.ZeroAddress]), body, { value: VERY_BIG_FEE });
      const receipt = await tx.wait();
      payload = receipt!.logs.find((l: { fragment?: { name?: string } }) => l.fragment?.name === 'MessageSent')!
        // @ts-expect-error hardhat log args
        .args.payload;
      const signed = await signPayload([notary1, notary2], [true, true], payload);
      proof = signed.proof;
      payloadHash = signed.payloadHash;
    });

    it('handler revert absorbed: deliverAndHandle returns success=false, MessageHandleError emitted, payload remains re-attemptable', async () => {
      await handlerMock.disable();
      // Note: deliverAndHandle uses a try/catch on the handler revert — the
      // EXTERNAL caller tx should NOT revert; only the success flag flips.
      const failTx = await dmailbox.connect(dCaller).deliverAndHandle(payload, proof);
      const failReceipt = await failTx.wait();

      // success flag false is observable through the third return value of deliverAndHandle.
      // emit check (best-effort): MessageHandleError event must fire for the handler revert path,
      // NOT MessageHandled.
      expect(failReceipt).to.not.equal(null);
      const handleErrorEvent = failReceipt!.logs.find((l: any) => l.topics[0] === TOPIC_MESSAGE_HANDLE_ERROR);
      expect(handleErrorEvent, 'expected a MessageHandleError event on the failing path').to.not.equal(undefined);
      const handleSucceededEvent = failReceipt!.logs.find((l: any) => l.topics[0] === TOPIC_MESSAGE_HANDLED);
      expect(handleSucceededEvent, 'must NOT emit MessageHandled when handler reverted').to.equal(undefined);

      // Refresh: enable handler; the same payload must succeed on retry —
      // proves the mailbox does not gate re-delivery on handledPayload.
      await handlerMock.enable();
      const okTx = await dmailbox.connect(dCaller).deliverAndHandle(payload, proof);
      const okReceipt = await okTx.wait();
      const handledEvent = okReceipt!.logs.find((l: any) => l.topics[0] === TOPIC_MESSAGE_HANDLED);
      expect(handledEvent, 'expected a MessageHandled event after retry').to.not.equal(undefined);
      const receivedEvent = okReceipt!.logs.find((l: any) => l.topics[0] === TOPIC_MESSAGE_RECEIVED);
      expect(receivedEvent, 'expected a MessageReceived event after retry').to.not.equal(undefined);
    });

    it('two consecutive retries on same payload: each emits MessageHandled (mailbox does not gate re-attempts post-failure)', async () => {
      // (a) fail path
      await handlerMock.disable();
      await dmailbox.connect(dCaller).deliverAndHandle(payload, proof);

      // (b) succeed path
      await handlerMock.enable();
      const okTx1 = await dmailbox.connect(dCaller).deliverAndHandle(payload, proof);
      const okReceipt1 = await okTx1.wait();
      const handled1 = okReceipt1!.logs.filter((l: any) => l.topics[0] === TOPIC_MESSAGE_HANDLED);
      expect(handled1.length).to.be.gte(1);

      // (c) third call: same payload, same caller; expect a re-handle because
      // the mailbox does NOT gate `deliverAndHandle` on handledPayload. This is
      // the contrast point with Solana's atomic Handled-before-CPI model.
      const okTx2 = await dmailbox.connect(dCaller).deliverAndHandle(payload, proof);
      const okReceipt2 = await okTx2.wait();
      const handled2 = okReceipt2!.logs.filter((l: any) => l.topics[0] === TOPIC_MESSAGE_HANDLED);
      expect(handled2.length).to.be.gte(1, 'expected another MessageHandled — mailbox re-runs handler on re-delivery');
      const received2 = okReceipt2!.logs.filter((l: any) => l.topics[0] === TOPIC_MESSAGE_RECEIVED);
      expect(received2.length).to.be.gte(1, 'handler ran twice on re-delivery — mailbox does not gate');
    });
  });

  describe('PROP-XR-EVM-007 — AssetRouter.changeBascule(address(0)) disables mint validation', function () {
    let arSnapshot: SnapshotRestorer;
    let stakedLbtc: StakedLBTC & Addressable;
    let mailbox: Mailbox & Addressable;
    let gmpBascule: GMPBasculeV1 & Addressable;
    let assetRouter: AssetRouter & Addressable;
    let stakedLbtcBytes: string;
    let assetRouterBytes: string;

    before(async () => {
      const { chainId: c } = await ethers.provider.getNetwork();
      const lcid = encode(['uint256'], [c]);

      stakedLbtc = await deployContract<StakedLBTC & Addressable>(
        'StakedLBTC',
        [owner.address, owner.address, 0n],
        true,
        { initializer: 'initialize', unsafeAllow: ['missing-initializer-call', 'incorrect-initializer-order'] }
      );
      stakedLbtc.address = await stakedLbtc.getAddress();
      stakedLbtcBytes = encode(['address'], [stakedLbtc.address]);

      const consForAr = await deployContract<Consortium & Addressable>('Consortium', [owner.address], true, {
        initializer: 'initialize',
        unsafeAllow: ['missing-initializer-call', 'incorrect-initializer-order']
      });
      consForAr.address = await consForAr.getAddress();
      await consForAr
        .connect(owner)
        .setInitialValidatorSet(
          getPayloadForAction([1, [notary1.publicKey, notary2.publicKey], [1, 1], 2, 1], NEW_VALSET)
        );

      mailbox = await deployContract<Mailbox & Addressable>(
        'Mailbox',
        [owner.address, consForAr.address, 0n, 0n],
        true,
        { initializer: 'initialize', unsafeAllow: ['missing-initializer-call', 'incorrect-initializer-order'] }
      );
      mailbox.address = await mailbox.getAddress();
      await mailbox.connect(owner).enableMessagePath(LEDGER_CHAIN_ID, LEDGER_MAILBOX, 3);

      gmpBascule = await deployContract<GMPBasculeV1 & Addressable>(
        'GMPBasculeV1',
        [owner.address, owner.address, mintReporter.address, ethers.ZeroAddress, 10n, trustedSigner.address],
        false
      );
      gmpBascule.address = await gmpBascule.getAddress();

      assetRouter = await deployContract<AssetRouter & Addressable>(
        'AssetRouter',
        [owner.address, 0n, LEDGER_CHAIN_ID, BITCOIN_CHAIN_ID, mailbox.address, gmpBascule.address],
        true,
        { initializer: 'initialize', unsafeAllow: ['missing-initializer-call', 'incorrect-initializer-order'] }
      );
      assetRouter.address = await assetRouter.getAddress();
      assetRouterBytes = encode(['address'], [assetRouter.address]);

      const mintValidatorRole = await gmpBascule.MINT_VALIDATOR_ROLE();
      await gmpBascule.connect(owner).grantRole(mintValidatorRole, assetRouter.address);
      await stakedLbtc.connect(owner).grantRole(await stakedLbtc.MINTER_ROLE(), assetRouter.address);
      await mailbox.connect(owner).setSenderConfig(assetRouter.address, 2000, true);

      arSnapshot = await takeSnapshot();
    });

    beforeEach(async () => {
      await arSnapshot.restore();
    });

    async function buildMintPayload(recipient: string, amount: bigint, msgNonce: number) {
      const body = getPayloadForAction(
        [stakedLbtcBytes, encode(['address'], [recipient]), amount],
        MINT_SELECTOR
      );
      const payload = getGMPPayload(
        LEDGER_MAILBOX,
        LEDGER_CHAIN_ID,
        CHAIN_ID,
        msgNonce,
        BTC_STAKING_MODULE_ADDRESS,
        assetRouterBytes,
        assetRouterBytes,
        body
      );
      const { proof } = await signPayload([notary1, notary2], [true, true], payload);
      return { payload, proof, body, amount };
    }

    it('changeBascule(address(0)) succeeds under DEFAULT_ADMIN_ROLE — bascule disables', async () => {
      // Confirm bascule currently set
      expect(await assetRouter.bascule()).to.be.equal(await gmpBascule.getAddress());

      // DEFAULT_ADMIN_ROLE alone is sufficient. Note: when `changeBascule(0)` is
      // called, the actual emitted event chain exposes empty-old/new in the
      // AssetRouter_BasculeChanged event.
      const tx = await assetRouter.connect(owner).changeBascule(ethers.ZeroAddress);
      const receipt = await tx.wait();
      expect(receipt).to.not.equal(null);

      // After change: view returns 0.
      expect(await assetRouter.bascule()).to.be.equal(ethers.ZeroAddress);
    });

    it('with bascule disabled, mint proceeds without MINT_VALIDATOR report', async () => {
      // First confirm: with bascule enabled, mint WITHOUT report reverts.
      let amount = randomBigInt(6);
      let nonce = Number(randomBigInt(4));
      let { payload, proof } = await buildMintPayload(signer1.address, amount, nonce);
      await expect(assetRouter.connect(signer1).mint(payload, proof)).to.be.revertedWithCustomError(
        assetRouter,
        'AssetRouter_MintProcessingError'
      );

      // Admin disables bascule.
      await assetRouter.connect(owner).changeBascule(ethers.ZeroAddress);

      // Same payload, no report, same nonce should now succeed — bypasses
      // Bascule.validateMint entirely because address(bascule_) == 0 short-circuits.
      const supplyBefore = await stakedLbtc.totalSupply();
      const ok = await assetRouter.connect(signer1).mint(payload, proof);
      const okR = await ok.wait();
      expect(okR).to.not.equal(null);
      expect((await stakedLbtc.totalSupply()) - supplyBefore).to.eq(amount);
    });

    it('non-admin caller is rejected on changeBascule', async () => {
      await expect(assetRouter.connect(signer1).changeBascule(ethers.ZeroAddress)).to.be.reverted;
    });
  });
});
