#!/usr/bin/env node
/**
 * CLI for MR review local tracking. Do not edit JSON files by hand — use this tool.
 *
 * Usage:
 *   npx tsx review-tracker.ts <command> [args]
 *
 * Commands that need a session path take <reviewDir> = .ai/gitlab/review/{sanitized_branch}-{mr_iid}/
 */

import * as fs from 'node:fs';
import * as path from 'node:path';

import { printError, printJson, printProgress, printSuccess, printSummary, printTable } from './output';
import {
  checkAllAddressed,
  countDispositions,
  getPendingComment,
  initReviewDir,
  markComplete,
  readAllComments,
  readComment,
  readReviewState,
  updateCommentAddressed,
} from './store';
import type { AddressPayload, InitPayload } from './types';

function readStdinSync(): string {
  try {
    return fs.readFileSync(0, 'utf8');
  } catch {
    return '';
  }
}

function parseJson<T>(raw: string, label: string): T {
  try {
    return JSON.parse(raw) as T;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(`${label}: invalid JSON — ${msg}`);
  }
}

function usage(): void {
  process.stdout.write(`MR review tracker — local JSON is managed only via this CLI.

Usage:
  npx tsx {packageRoot}/skills/mr-review-address/scripts/review-tracker.ts <command> [args]

Commands:
  init
    Read InitPayload JSON from stdin. Creates .ai/gitlab/review/<branch>-<mr_iid>/ and comment files.
    No arguments.

  get-state <reviewDir>
    Print review-state.json as JSON.

  list-comments <reviewDir>
    Table of discussion_id, status, file, author (truncated).

  get-comment <reviewDir> <discussion_id>
    Print one comment record as JSON.

  get-pending <reviewDir>
    Print the next pending comment as JSON, or {"pending":null} if none.

  address-comment <reviewDir> <discussion_id>
    Read AddressPayload JSON from stdin. Marks comment addressed and updates counters.

  complete <reviewDir>
    Set session status to complete (after verification).

  check-all-addressed <reviewDir>
    Exit 0 if all comments addressed; exit 1 with pending ids if not.

  status <reviewDir>
    Human-readable progress + disposition counts.

Environment:
  CWD should be the repository root when using relative <reviewDir> paths.
`);
}

function resolveReviewDir(arg: string | undefined): string {
  if (!arg?.trim()) {
    throw new Error('Missing <reviewDir> (e.g. .ai/gitlab/review/feature-dev-foo-42)');
  }
  return path.resolve(process.cwd(), arg);
}

function cmdInit(): void {
  const raw = readStdinSync().trim();
  if (!raw) {
    throw new Error('init requires JSON on stdin (InitPayload)');
  }
  const payload = parseJson<InitPayload>(raw, 'stdin');
  if (!payload.project_id || !payload.mr_url || !payload.branch) {
    throw new Error('init: project_id, mr_url, and branch are required');
  }
  if (typeof payload.mr_iid !== 'number') {
    throw new Error('init: mr_iid must be a number');
  }
  if (!Array.isArray(payload.comments)) {
    throw new Error('init: comments must be an array');
  }

  const { reviewRoot, archivedTo } = initReviewDir(process.cwd(), payload);
  printSuccess(`Initialized review session at ${reviewRoot}`);
  if (archivedTo) {
    printSuccess(`Archived previous directory to ${archivedTo}`);
  }
  printSummary([
    `discussion files written: ${payload.comments.length}`,
    `reviewRoot (use for other commands): ${reviewRoot}`,
  ]);
  printJson('review-state', readReviewState(reviewRoot));
}

function cmdGetState(reviewRoot: string): void {
  const state = readReviewState(reviewRoot);
  printJson('review-state', state);
}

function cmdListComments(reviewRoot: string): void {
  const state = readReviewState(reviewRoot);
  const rows = readAllComments(reviewRoot).map((c) => {
    const bodyPreview =
      c.body.length > 60 ? `${c.body.slice(0, 57)}...` : c.body;
    return [
      c.discussion_id,
      c.status,
      c.file ?? '',
      c.author,
      bodyPreview.replace(/\s+/g, ' '),
    ];
  });
  printTable(['discussion_id', 'status', 'file', 'author', 'body'], rows);
  printProgress(state.addressed, state.total_comments, state.pending);
}

function cmdGetComment(reviewRoot: string, discussionId: string): void {
  const c = readComment(reviewRoot, discussionId);
  printJson('comment', c);
}

function cmdGetPending(reviewRoot: string): void {
  const pending = getPendingComment(reviewRoot);
  printJson('pending', { pending });
}

function cmdAddressComment(reviewRoot: string, discussionId: string): void {
  const raw = readStdinSync().trim();
  if (!raw) {
    throw new Error('address-comment requires JSON on stdin (AddressPayload)');
  }
  const payload = parseJson<AddressPayload>(raw, 'stdin');
  if (!payload.disposition || !payload.response) {
    throw new Error('address-comment: disposition and response are required');
  }
  const { state, record } = updateCommentAddressed(reviewRoot, discussionId, {
    ...payload,
    changes_made: payload.changes_made ?? null,
  });
  printSuccess(
    `Marked ${discussionId} as addressed (${payload.disposition})`,
  );
  printJson('updated_comment', record);
  printJson('review-state', state);
  printProgress(state.addressed, state.total_comments, state.pending);
}

function cmdComplete(reviewRoot: string): void {
  const state = markComplete(reviewRoot);
  printSuccess('Session marked complete');
  printJson('review-state', state);
}

function cmdCheckAllAddressed(reviewRoot: string): void {
  const result = checkAllAddressed(reviewRoot);
  printJson('check', result);
  if (!result.ok) {
    printError(
      `Not all comments addressed. Pending: ${result.pendingDiscussionIds.join(', ')}`,
    );
    process.exitCode = 1;
  } else {
    printSuccess('All comments have status addressed');
  }
}

function cmdStatus(reviewRoot: string): void {
  const state = readReviewState(reviewRoot);
  const counts = countDispositions(reviewRoot);
  printSummary([
    `MR: !${state.mr_iid} — ${state.mr_url}`,
    `Branch: ${state.branch}`,
    `Directory: ${state.review_dir_name}`,
    `Session status: ${state.status}`,
    `Progress: ${state.addressed}/${state.total_comments} addressed, ${state.pending} pending`,
    `Dispositions — agree: ${counts.agree_implemented}, alternative: ${counts.better_alternative}, defended: ${counts.disagree_defended}, n/a: ${counts.not_applicable}`,
  ]);
}

function main(): void {
  const argv = process.argv.slice(2);
  const cmd = argv[0];

  if (!cmd || cmd === '-h' || cmd === '--help') {
    usage();
    process.exit(0);
    return;
  }

  try {
    switch (cmd) {
      case 'init':
        cmdInit();
        break;
      case 'get-state':
        cmdGetState(resolveReviewDir(argv[1]));
        break;
      case 'list-comments':
        cmdListComments(resolveReviewDir(argv[1]));
        break;
      case 'get-comment':
        if (!argv[2]) {
          throw new Error('Usage: get-comment <reviewDir> <discussion_id>');
        }
        cmdGetComment(resolveReviewDir(argv[1]), argv[2]);
        break;
      case 'get-pending':
        cmdGetPending(resolveReviewDir(argv[1]));
        break;
      case 'address-comment':
        if (!argv[2]) {
          throw new Error('Usage: address-comment <reviewDir> <discussion_id>');
        }
        cmdAddressComment(resolveReviewDir(argv[1]), argv[2]);
        break;
      case 'complete':
        cmdComplete(resolveReviewDir(argv[1]));
        break;
      case 'check-all-addressed':
        cmdCheckAllAddressed(resolveReviewDir(argv[1]));
        break;
      case 'status':
        cmdStatus(resolveReviewDir(argv[1]));
        break;
      default:
        printError(`Unknown command: ${cmd}`);
        usage();
        process.exitCode = 1;
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    printError(msg);
    process.exitCode = 1;
  }
}

main();
