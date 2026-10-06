/**
 * Stdout/stderr helpers for review-tracker CLI (human-readable + JSON blocks).
 */

export function printSuccess(message: string): void {
  process.stdout.write(`OK: ${message}\n`);
}

export function printError(message: string): void {
  process.stderr.write(`ERROR: ${message}\n`);
}

export function printJson(label: string | null, value: unknown): void {
  const json = JSON.stringify(value, null, 2);
  if (label) {
    process.stdout.write(`--- ${label} ---\n`);
  }
  process.stdout.write(`${json}\n`);
}

export function printSummary(lines: string[]): void {
  process.stdout.write('--- Summary ---\n');
  for (const line of lines) {
    process.stdout.write(`${line}\n`);
  }
}

export function printTable(headers: string[], rows: string[][]): void {
  const widths = headers.map((h, i) =>
    Math.max(
      h.length,
      ...rows.map((r) => (r[i] ?? '').length),
    ),
  );
  const sep = widths.map((w) => '-'.repeat(w)).join(' | ');
  const headerLine = headers.map((h, i) => h.padEnd(widths[i])).join(' | ');
  process.stdout.write(`${headerLine}\n`);
  process.stdout.write(`${sep}\n`);
  for (const row of rows) {
    process.stdout.write(
      row.map((cell, i) => (cell ?? '').padEnd(widths[i])).join(' | ') + '\n',
    );
  }
}

export function printProgress(addressed: number, total: number, pending: number): void {
  process.stdout.write(
    `Progress: ${addressed}/${total} addressed, ${pending} pending\n`,
  );
}
