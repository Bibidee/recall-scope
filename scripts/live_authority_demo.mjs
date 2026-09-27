import { createRequire } from "node:module";
import { createHash, generateKeyPairSync, sign as rsaSign } from "node:crypto";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

const cliRoot = join(process.env.APPDATA, "npm", "node_modules", "genlayer");
const cliRequire = createRequire(join(cliRoot, "package.json"));
const [{ createClient }, { studionet }, { privateKeyToAccount }, { CalldataAddress }] = await Promise.all([
  import(pathToFileURL(cliRequire.resolve("genlayer-js"))),
  import(pathToFileURL(cliRequire.resolve("genlayer-js/chains"))),
  import(pathToFileURL(cliRequire.resolve("viem/accounts"))),
  import(pathToFileURL(cliRequire.resolve("genlayer-js/types"))),
]);
const keytar = cliRequire("keytar");

const registryAddress = "0xFDF61b362aEd0aC9D90Aef4117f97DA087AF5187";
const recallScopeAddress = "0x23BAd5BFE52e2748c2ba1b013Ed0795D77e98572";
const accountName = process.env.RECALLSCOPE_ACCOUNT || "fresh-bob";
const cliKey = await keytar.getPassword("genlayer-cli", `account:${accountName}`);
if (!cliKey) throw new Error(`Unlocked CLI keychain entry unavailable for ${accountName}`);
const account = privateKeyToAccount(cliKey);
const client = createClient({
  chain: studionet,
  endpoint: "https://studio.genlayer.com/api",
  account,
});
const addressArg = (value) => new CalldataAddress(Buffer.from(value.slice(2), "hex"));

const json = (value) => JSON.stringify(value, (_, item) => typeof item === "bigint" ? item.toString() : item);
const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
const waitForFinal = async (hash) => {
  for (let attempt = 0; attempt < 180; attempt += 1) {
    await delay(10_000); // six RPC polls/minute, below the Studionet limit
    const tx = await client.getTransaction({ hash });
    const status = tx.statusName || tx.status_name;
    if (["FINALIZED", "UNDETERMINED", "CANCELED"].includes(status)) return tx;
  }
  throw new Error(`Timed out waiting for ${hash}`);
};
const write = async (address, functionName, args) => {
  const hash = await client.writeContract({
    address,
    functionName,
    args,
    consensusMaxRotations: 5,
  });
  const tx = await waitForFinal(hash);
  const status = tx.statusName || tx.status_name;
  const consensus = tx.result_name || tx.resultName;
  const execution = tx.consensus_data?.leader_receipt?.[0]?.execution_result;
  const result = { hash, status, consensus, execution };
  console.log(json({ step: functionName, ...result }));
  if (status !== "FINALIZED" || execution !== "SUCCESS") {
    throw new Error(`${functionName} did not finalize with GenVM SUCCESS: ${json(result)}`);
  }
  return { hash, tx, result };
};
const read = (address, functionName, args = []) => client.readContract({
  address,
  functionName,
  args,
  transactionHashVariant: "latest-final",
});

const info = await read(recallScopeAddress, "get_info");
if (info.version !== "0.2.0" || info.authority_registry.toLowerCase() !== registryAddress.toLowerCase()) {
  throw new Error(`Unexpected RecallScope deployment metadata: ${json(info)}`);
}
const registryInfo = await read(registryAddress, "get_info");
if (registryInfo.version !== "0.2.0" || registryInfo.admin.toLowerCase() !== account.address.toLowerCase()) {
  throw new Error(`Active signer is not the v0.2.0 registry administrator: ${json(registryInfo)}`);
}

const fixtureCommit = "93e557b6a1d922accdd9f24c35684189ded583f0";
const product = {
  url: `https://raw.githubusercontent.com/Bibidee/recall-scope/${fixtureCommit}/evidence/demo-product-record.txt`,
  expected: "0xcfdbf92bcd9dc04f19b37faa0bdf6ea2049038481086806c450be982e7e8f3bf",
};
const notice = {
  url: `https://raw.githubusercontent.com/Bibidee/recall-scope/${fixtureCommit}/evidence/demo-recall-notice.txt`,
  expected: "0xea5615a7076449ea31238834ac20d00dcf1e807dad227b72ebf314e5838ffeb5",
};
for (const artifact of [product, notice]) {
  const response = await fetch(artifact.url, { redirect: "follow" });
  if (!response.ok) throw new Error(`Artifact HTTP ${response.status}: ${artifact.url}`);
  artifact.bytes = Buffer.from(await response.arrayBuffer());
  artifact.actual = `0x${sha256(artifact.bytes)}`;
  new TextDecoder("utf-8", { fatal: true }).decode(artifact.bytes);
  if (artifact.actual !== artifact.expected) throw new Error(`Raw-byte SHA-256 mismatch: ${artifact.url}`);
  console.log(json({ step: "artifact_verified", url: artifact.url, sha256: artifact.actual, bytes: artifact.bytes.length }));
}

// The synthetic signing key exists only in this process. Only its public modulus
// is registered; neither key material nor a private-key file is emitted or saved.
const { publicKey, privateKey } = generateKeyPairSync("rsa", {
  modulusLength: 2048,
  publicExponent: 65537,
  publicKeyEncoding: { type: "spki", format: "pem" },
  privateKeyEncoding: { type: "pkcs8", format: "pem" },
});
const jwk = createRequire(import.meta.url)("node:crypto").createPublicKey(publicKey).export({ format: "jwk" });
const modulus = Buffer.from(jwk.n, "base64url").toString("hex");
if (modulus.length !== 512) throw new Error("Generated key is not a 2048-bit RSA modulus");
const authorityId = `DEMO-AUTH-${Date.now()}`;
const registration = await write(registryAddress, "register_authority", [
  authorityId,
  "Fictional RecallScope Demonstration Authority (not a real authority)",
  `0x${modulus}`,
  "raw.githubusercontent.com",
  "ZZ",
  "Northstar Demo Heater",
]);
const registered = await read(registryAddress, "get_authority", [authorityId]);
const fingerprint = `0x${sha256(Buffer.from(modulus, "ascii"))}`;
if (!registered.active || registered.signer_fingerprint.toLowerCase() !== fingerprint.toLowerCase()) {
  throw new Error(`Registry record did not match the generated public key: ${json(registered)}`);
}
console.log(json({
  step: "authority_registered",
  authorityId,
  signerFingerprint: fingerprint,
  active: registered.active,
  revision: registered.revision,
  domains: registered.domains,
  markets: registered.markets,
  products: registered.products,
}));

const caseId = `live-authority-demo-${Date.now()}`;
const productName = "Northstar Demo Heater";
const model = "H-TEST-1";
const batch = "DEMO-RECALL-001";
const market = "ZZ";
const recallReference = "DEMO-RECALL-001";
const issuedAt = Math.floor(Date.now() / 1000) - 300;
const expiresAt = issuedAt + 7 * 24 * 60 * 60;
const fields = [
  "RECALLSCOPE_AUTHORITY_MANIFEST_V1",
  "61999",
  recallScopeAddress.toLowerCase(),
  registryAddress.toLowerCase(),
  caseId,
  authorityId,
  String(registered.revision),
  notice.actual.toLowerCase(),
  productName,
  model,
  batch,
  market,
  String(issuedAt),
  String(expiresAt),
  recallReference,
];
const manifestBytes = Buffer.concat(fields.map((field) => {
  const bytes = Buffer.from(field, "utf8");
  return Buffer.concat([Buffer.from(`${bytes.length}:`, "ascii"), bytes]);
}));
const manifestHash = `0x${sha256(manifestBytes)}`;
const manifestSignature = `0x${rsaSign("RSA-SHA256", manifestBytes, privateKey).toString("hex")}`;
const summary = "Fictional demo only: the signed notice says this exact Northstar Demo Heater model and batch in market ZZ must stop use because of a simulated overheating hazard.";
console.log(json({
  step: "live_case_parameters",
  chainId: 61999,
  recallScope: recallScopeAddress,
  registry: registryAddress,
  caseId,
  authorityId,
  proposer: account.address,
  consumer: account.address,
  productUrl: product.url,
  productHash: product.actual,
  noticeUrl: notice.url,
  noticeHash: notice.actual,
  manifestHash,
  signerFingerprint: fingerprint,
  issuedAt,
  expiresAt,
  summary,
}));

const proposal = await write(recallScopeAddress, "submit_authority_bound_case", [
  caseId,
  productName,
  model,
  batch,
  market,
  addressArg(account.address),
  product.url,
  product.actual,
  notice.url,
  notice.actual,
  "",
  "",
  summary,
  authorityId,
  recallReference,
  BigInt(issuedAt),
  BigInt(expiresAt),
  manifestSignature,
]);
const pending = await read(recallScopeAddress, "get_case", [caseId, addressArg(account.address)]);
console.log(json({ step: "pending_case", caseId, state: pending }));
if (pending.status !== "pending" || pending.evidence_mode !== "AUTHORITY_BOUND" || !pending.authority_verified) {
  throw new Error(`Authority-bound case was not stored as expected: ${json(pending)}`);
}

const review = await write(recallScopeAddress, "review_case", [caseId, addressArg(account.address)]);
const reviewed = await read(recallScopeAddress, "get_case", [caseId, addressArg(account.address)]);
const action = await read(recallScopeAddress, "is_authoritative_action_required_for", [
  caseId, addressArg(account.address), productName, model, batch, market,
]);
console.log(json({ step: "reviewed_case", caseId, proposalTx: proposal.hash, reviewTx: review.hash, state: reviewed, authoritativeActionRequired: action }));
if (reviewed.status !== "recall_applies" || Number(reviewed.confidence) < 75 || action !== true) {
  console.log(json({ step: "safe_stop", reason: "live semantic consensus did not produce a positive authoritative result; no acknowledgement submitted" }));
  process.exitCode = 2;
} else {
  const acknowledgement = await write(recallScopeAddress, "acknowledge_action", [caseId, addressArg(account.address)]);
  const finalState = await read(recallScopeAddress, "get_case", [caseId, addressArg(account.address)]);
  console.log(json({ step: "final_case", caseId, acknowledgementTx: acknowledgement.hash, state: finalState }));
  if (finalState.status !== "acknowledged") throw new Error(`Expected acknowledged final state, received ${json(finalState)}`);
  const revocation = await write(registryAddress, "revoke_authority", [authorityId]);
  const revokedState = await read(recallScopeAddress, "get_case", [caseId, addressArg(account.address)]);
  const afterRevocation = await read(recallScopeAddress, "is_authoritative_action_required_for", [
    caseId, addressArg(account.address), productName, model, batch, market,
  ]);
  console.log(json({
    step: "post_demo_revocation",
    revocationTx: revocation.hash,
    caseStatus: revokedState.status,
    authorityStatus: revokedState.authority_status,
    authoritativeActionRequired: afterRevocation,
  }));
  if (revokedState.status !== "acknowledged" || afterRevocation !== false) {
    throw new Error("Revocation did not preserve history while disabling future authority-gated action");
  }
}
