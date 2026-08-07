globalThis.window = globalThis;
await import("../static/free-capacity.js");

const assess = globalThis.VTNFreeCapacity.assess;
const checks = [
  [{ transcript: "知".repeat(845), durationSeconds: 3 * 60 }, "recommended"],
  [{ transcript: "知".repeat(9_000), durationSeconds: 30 * 60 }, "recommended"],
  [{ transcript: "知".repeat(9_001), durationSeconds: 30 * 60 }, "caution"],
  [{ transcript: "知".repeat(13_500), durationSeconds: 45 * 60 }, "caution"],
  [{ transcript: "知".repeat(13_501), durationSeconds: 45 * 60 }, "high_risk"],
  [{ transcript: "知".repeat(3_000), durationSeconds: 60 * 60 }, "high_risk"],
  [{ transcript: "知 识\n".repeat(4_500) }, "recommended"],
  [{ transcript: "" }, "unknown"],
];

for (const [input, expected] of checks) {
  const actual = assess(input);
  if (actual.level !== expected) {
    throw new Error(`expected ${expected}, got ${actual.level}: ${JSON.stringify(input)}`);
  }
}

console.log(JSON.stringify({ ok: true, checks: checks.length }));
