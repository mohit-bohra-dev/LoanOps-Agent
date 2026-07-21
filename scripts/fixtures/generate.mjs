/**
 * Generate upstream-shaped Loan Services fixtures with json-schema-faker.
 *
 * Usage (from repo root or this dir):
 *   cd scripts/fixtures && npm install && npm run generate
 *   npm run generate -- --seed 42
 *
 * Determinism: same --seed (default 12345) + seeds.mjs → same fixture files.
 * Uses jsf fixedProbabilities + seeded PRNG, and faker.seed().
 *
 * Writes: data/fixtures/loan_api/{loanId}/{summary,loan,borrowers,payment_schedules,escrows,delinquencies}.json
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { JSONSchemaFaker } from "json-schema-faker";
import { faker } from "@faker-js/faker";
import { SEEDS } from "./seeds.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..", "..");
const SCHEMA_DIR = join(ROOT, "data", "schemas", "loan_api");
const OUT_DIR = join(ROOT, "data", "fixtures", "loan_api");

/** Default RNG seed — override with --seed <n> */
const DEFAULT_SEED = 12345;

function parseSeedArg(argv) {
  const idx = argv.indexOf("--seed");
  if (idx >= 0 && argv[idx + 1] != null) {
    const n = Number(argv[idx + 1]);
    if (!Number.isFinite(n)) {
      throw new Error(`Invalid --seed value: ${argv[idx + 1]}`);
    }
    return Math.trunc(n);
  }
  if (process.env.FIXTURE_SEED) {
    const n = Number(process.env.FIXTURE_SEED);
    if (!Number.isFinite(n)) {
      throw new Error(`Invalid FIXTURE_SEED: ${process.env.FIXTURE_SEED}`);
    }
    return Math.trunc(n);
  }
  return DEFAULT_SEED;
}

/** Mulberry32 — deterministic PRNG in [0, 1) for jsf `random` option. */
function mulberry32(seed) {
  let t = seed >>> 0;
  return function random() {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

function configureRandomness(baseSeed) {
  // @faker-js/faker (used via jsf.extend)
  faker.seed(baseSeed);

  // json-schema-faker 0.5.x: pass seeded random() + fixedProbabilities
  // (website v0.6 `generate(schema, { seed })` API not in this package version)
  JSONSchemaFaker.reset();
  JSONSchemaFaker.extend("faker", () => faker);
  JSONSchemaFaker.option({
    alwaysFakeOptionals: true,
    fillProperties: false,
    useDefaultValue: true,
    fixedProbabilities: true,
    ignoreMissingRefs: true,
    random: mulberry32(baseSeed),
  });
}

function loadSchema(name) {
  return JSON.parse(readFileSync(join(SCHEMA_DIR, name), "utf8"));
}

function addMonths(iso, n) {
  const datePart = String(iso).split("T")[0];
  const [y, m, d] = datePart.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1 + n, d));
  const yyyy = dt.getUTCFullYear();
  const mm = String(dt.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(dt.getUTCDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}T00:00:00`;
}

function buildBorrower(seed, borrowerId) {
  return {
    BorrowerId: borrowerId,
    LoanId: seed.loanId,
    BorrowerOrdinal: 1,
    BorrowerFirstName: seed.firstName,
    BorrowerLastName: seed.lastName,
    BorrowerMiddleName: "",
    BorrowerUnparsedName: `${seed.firstName} ${seed.lastName}`,
    BorrowerMailingLocality: "Synthetic City",
    BorrowerMailingRegion: seed.state,
    BorrowerMailingPostalCode: "00000",
    BorrowerEmailAddress: `${seed.firstName.toLowerCase()}.${seed.lastName.toLowerCase()}@example.test`,
    BorrowerPrimaryPhoneNumber: "5550100",
    ObligorFlag: true,
  };
}

function buildSchedules(seed) {
  const rows = [];
  for (let i = 0; i < seed.scheduleMonths; i++) {
    const due = addMonths(seed.nextDue, i);
    const principal = Math.round(seed.monthlyPi * 0.35 * 100) / 100;
    const interest = Math.round((seed.monthlyPi - principal) * 100) / 100;
    rows.push({
      PaymentScheduleId: seed.loanId * 10 + i,
      LoanId: seed.loanId,
      NextPaymentDueDate: seed.nextDue,
      PaymentDueMonth: due,
      TotalPaymentAmount: Math.round((seed.monthlyPi + seed.monthlyEscrow) * 100) / 100,
      PendingEscrowPaymentAmount: seed.monthlyEscrow,
      InterestRate: seed.rate,
      MonthlyPaymentAmount: seed.monthlyPi,
      MonthlyPaymentPrincipalAmount: principal,
      MonthlyPaymentInterestAmount: interest,
      MonthlyCountyTaxAmount: Math.round(seed.monthlyEscrow * 0.6 * 100) / 100,
      MonthlyHazardInsuranceAmount: Math.round(seed.monthlyEscrow * 0.4 * 100) / 100,
      QuotedLateChargeFeeAmount: 35.0,
      LateChargeGraceEndDate: addMonths(due, 0).replace(/T.*/, "T00:00:00"),
    });
  }
  return rows;
}

function applySummaryOverrides(raw, seed, borrower) {
  return {
    ...raw,
    LoanId: seed.loanId,
    LoanActiveFlag: seed.active,
    EscrowFlag: seed.escrowed,
    PaidOffFlag: false,
    ChargedOffFlag: false,
    UnpaidPrincipalBalanceAmount: seed.balance,
    NextPaymentDueDate: seed.nextDue,
    LastPaymentReceivedDate: seed.lastPayment,
    CurrentInterestRate: seed.rate,
    CurrentMonthlyPaymentAmount: seed.monthlyPi,
    CurrentEscrowMonthlyPaymentAmount: seed.monthlyEscrow,
    CurrentTotalMonthlyPaymentAmount:
      Math.round((seed.monthlyPi + seed.monthlyEscrow) * 100) / 100,
    MortgageTypeDescription: seed.product,
    PropertyRegion: seed.state,
    MailingRegion: seed.state,
    LoanMaturityDate: seed.maturity,
    InvestorName: seed.investor,
    DelinquentPaymentCount: seed.delinquentCount,
    DelinquentAtBoardingFlag: false,
    LossMitigationTemplateDescription: seed.lossMit,
    ForeclosureStatusDescription: seed.active ? null : "Removed",
    BankruptcyStatusDescription: "not mapped",
    EscrowBalanceAmount: seed.escrowed ? 1500.0 : 0.0,
    LastEscrowAnalysisDate: seed.lastPayment,
    MonthlyCountyTaxAmount: Math.round(seed.monthlyEscrow * 0.6 * 100) / 100,
    MonthlyHazardInsuranceAmount: Math.round(seed.monthlyEscrow * 0.4 * 100) / 100,
    MonthlyMortgageInsuranceAmount: 0.0,
    MonthlyOverageShortageAmount: 20.0,
    PaymentScheduleDueMonth: seed.nextDue,
    BorrowerSummary: [borrower],
  };
}

function applyRecordOverrides(raw, seed) {
  return {
    ...raw,
    LoanId: seed.loanId,
    ActiveFlag: seed.active,
    EscrowFlag: seed.escrowed,
    UnpaidPrincipalBalanceAmount: seed.balance,
    NextPaymentDueDate: seed.nextDue,
    LastPaymentReceivedDate: seed.lastPayment,
    CurrentInterestRate: seed.rate,
    CurrentMonthlyPaymentAmount: seed.monthlyPi,
    CurrentEscrowMonthlyPaymentAmount: seed.monthlyEscrow,
    CurrentTotalMonthlyPaymentAmount:
      Math.round((seed.monthlyPi + seed.monthlyEscrow) * 100) / 100,
    DelinquentPaymentCount: seed.delinquentCount,
    EscrowBalanceAmount: seed.escrowed ? 1500.0 : 0.0,
    LoanMaturityDate: seed.maturity,
  };
}

async function generateLoan(seed, schemas) {
  const borrowerId = 900000 + (seed.loanId % 100000);
  const borrower = buildBorrower(seed, borrowerId);

  const summaryRaw = JSONSchemaFaker.generate(schemas.summary);
  const recordRaw = JSONSchemaFaker.generate(schemas.record);
  const escrowRaw = JSONSchemaFaker.generate(schemas.escrow);

  const summary = applySummaryOverrides(summaryRaw, seed, borrower);
  const loan = applyRecordOverrides(recordRaw, seed);
  const borrowers = [borrower];
  const payment_schedules = buildSchedules(seed);

  const escrows = (Array.isArray(escrowRaw) ? escrowRaw : [escrowRaw]).map((row, i) => ({
    ...row,
    EscrowId: 2000000 + i,
    LoanId: seed.loanId,
    LastEscrowAnalysisDate: seed.lastPayment,
    LastEscrowAnalysisOverShortAmount: 20.0,
    InterestOnEscrowFlag: false,
  }));

  const delinquencies =
    seed.delinquencyCode == null
      ? []
      : [
          {
            DelinquencyId: 300000 + (seed.loanId % 1000),
            LoanId: seed.loanId,
            DelinquencyCode: seed.delinquencyCode,
            GraceDays: 15,
            DelinquentPaymentBalanceAmount:
              Math.round((seed.monthlyPi + seed.monthlyEscrow) * 100) / 100,
          },
        ];

  return { summary, loan, borrowers, payment_schedules, escrows, delinquencies };
}

function writeLoan(loanId, payloads) {
  const dir = join(OUT_DIR, String(loanId));
  mkdirSync(dir, { recursive: true });
  for (const [name, data] of Object.entries(payloads)) {
    writeFileSync(join(dir, `${name}.json`), JSON.stringify(data, null, 2) + "\n", "utf8");
  }
  console.log(`wrote ${dir}`);
}

async function main() {
  const baseSeed = parseSeedArg(process.argv.slice(2));
  configureRandomness(baseSeed);
  console.log(`Using RNG seed: ${baseSeed} (override with --seed N or FIXTURE_SEED)`);

  const schemas = {
    summary: loadSchema("loan-summary.schema.json"),
    record: loadSchema("loan-record.schema.json"),
    escrow: loadSchema("escrow.schema.json"),
  };

  // Inline $ref for borrower item so jsf does not need remote resolve
  const borrowerItem = loadSchema("borrower-item.schema.json");
  schemas.summary.properties.BorrowerSummary = {
    type: "array",
    items: borrowerItem,
  };

  mkdirSync(OUT_DIR, { recursive: true });

  for (const seed of SEEDS) {
    // Per-loan sub-seed: stable across runs, different across loans
    const loanSeed = (baseSeed ^ (seed.loanId >>> 0)) >>> 0;
    configureRandomness(loanSeed);
    const payloads = await generateLoan(seed, schemas);
    writeLoan(seed.loanId, payloads);
  }

  console.log(`Generated ${SEEDS.length} loan fixture sets under ${OUT_DIR}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
