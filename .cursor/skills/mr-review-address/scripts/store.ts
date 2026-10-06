/**
 * Filesystem operations for MR review tracking (no direct AI access to JSON).
 */

import * as fs from 'node:fs';
import * as path from 'node:path';

import type {
  AddressPayload,
  CheckAllResult,
  CommentRecord,
  CommentStatus,
  DispositionCounts,
  InitPayload,
  ReviewState,
} from './types';

const REVIEW_ROOT = '.ai/gitlab/review';

export function sanitizeBranch(branch: string): string {
  return branch.replace(/\//g, '-');
}

export function reviewDirName(branch: string, mrIid: number): string {
  return `${sanitizeBranch(branch)}-${mrIid}`;
}

export function defaultReviewRoot(cwd: string, branch: string, mrIid: number): string {
  return path.join(cwd, REVIEW_ROOT, reviewDirName(branch, mrIid));
}

function safeDiscussionFileName(discussionId: string): string {
  if (
    !discussionId ||
    discussionId.includes('/') ||
    discussionId.includes('\\') ||
    discussionId.includes('..')
  ) {
    throw new Error(`Invalid discussion_id: ${discussionId}`);
  }
  return `${discussionId}.json`;
}

export function readReviewState(reviewRoot: string): ReviewState {
  const p = path.join(reviewRoot, 'review-state.json');
  const raw = fs.readFileSync(p, 'utf8');
  return JSON.parse(raw) as ReviewState;
}

export function writeReviewState(reviewRoot: string, state: ReviewState): void {
  const p = path.join(reviewRoot, 'review-state.json');
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, `${JSON.stringify(state, null, 2)}\n`, 'utf8');
}

export function readComment(reviewRoot: string, discussionId: string): CommentRecord {
  const p = path.join(reviewRoot, 'comments', safeDiscussionFileName(discussionId));
  const raw = fs.readFileSync(p, 'utf8');
  return JSON.parse(raw) as CommentRecord;
}

export function writeComment(reviewRoot: string, record: CommentRecord): void {
  const p = path.join(reviewRoot, 'comments', safeDiscussionFileName(record.discussion_id));
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, `${JSON.stringify(record, null, 2)}\n`, 'utf8');
}

export function readAllComments(reviewRoot: string): CommentRecord[] {
  const dir = path.join(reviewRoot, 'comments');
  if (!fs.existsSync(dir)) {
    return [];
  }
  const files = fs.readdirSync(dir).filter((f) => f.endsWith('.json'));
  const out: CommentRecord[] = [];
  for (const f of files) {
    const raw = fs.readFileSync(path.join(dir, f), 'utf8');
    out.push(JSON.parse(raw) as CommentRecord);
  }
  return out.sort((a, b) => a.discussion_id.localeCompare(b.discussion_id));
}

export function archiveIfExists(reviewRoot: string): string | null {
  if (!fs.existsSync(reviewRoot)) {
    return null;
  }
  const parent = path.dirname(reviewRoot);
  const base = path.basename(reviewRoot);
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const archived = path.join(parent, `${base}-previous-${ts}`);
  fs.renameSync(reviewRoot, archived);
  return archived;
}

function toCommentRecord(input: InitPayload['comments'][number]): CommentRecord {
  return {
    discussion_id: input.discussion_id,
    note_id: input.note_id ?? null,
    author: input.author,
    body: input.body,
    file: input.file ?? null,
    old_line: input.old_line ?? null,
    new_line: input.new_line ?? null,
    code_context: input.code_context ?? null,
    resolved_on_gitlab: input.resolved_on_gitlab ?? false,
    status: 'pending',
    disposition: null,
    response: null,
    changes_made: null,
    addressed_at: null,
  };
}

export function initReviewDir(cwd: string, payload: InitPayload): { reviewRoot: string; archivedTo: string | null } {
  const dirName = reviewDirName(payload.branch, payload.mr_iid);
  const reviewRoot = path.join(cwd, REVIEW_ROOT, dirName);
  const archivedTo = archiveIfExists(reviewRoot);

  fs.mkdirSync(path.join(reviewRoot, 'comments'), { recursive: true });

  const now = new Date().toISOString();
  const comments = payload.comments.map(toCommentRecord);
  const total = comments.length;

  const state: ReviewState = {
    project_id: payload.project_id,
    mr_iid: payload.mr_iid,
    mr_url: payload.mr_url,
    branch: payload.branch,
    review_dir_name: dirName,
    fetched_at: now,
    total_comments: total,
    addressed: 0,
    pending: total,
    status: 'in_progress',
  };

  writeReviewState(reviewRoot, state);
  for (const c of comments) {
    writeComment(reviewRoot, c);
  }

  return { reviewRoot, archivedTo };
}

export function updateCommentAddressed(
  reviewRoot: string,
  discussionId: string,
  payload: AddressPayload,
): { state: ReviewState; record: CommentRecord } {
  const record = readComment(reviewRoot, discussionId);
  if (record.status === 'addressed') {
    throw new Error(`Comment ${discussionId} is already addressed`);
  }
  const now = new Date().toISOString();
  const updated: CommentRecord = {
    ...record,
    status: 'addressed',
    disposition: payload.disposition,
    response: payload.response,
    changes_made: payload.changes_made,
    addressed_at: now,
  };
  writeComment(reviewRoot, updated);

  const state = readReviewState(reviewRoot);
  const addressed = state.addressed + 1;
  const pending = Math.max(0, state.pending - 1);
  const next: ReviewState = {
    ...state,
    addressed,
    pending,
  };
  writeReviewState(reviewRoot, next);
  return { state: next, record: updated };
}

export function markComplete(reviewRoot: string): ReviewState {
  const state = readReviewState(reviewRoot);
  const next: ReviewState = { ...state, status: 'complete' };
  writeReviewState(reviewRoot, next);
  return next;
}

export function checkAllAddressed(reviewRoot: string): CheckAllResult {
  const state = readReviewState(reviewRoot);
  const comments = readAllComments(reviewRoot);
  const pendingDiscussionIds = comments
    .filter((c) => c.status !== 'addressed')
    .map((c) => c.discussion_id);
  const addressedCount = comments.filter((c) => c.status === 'addressed').length;
  return {
    ok: pendingDiscussionIds.length === 0,
    pendingDiscussionIds,
    total: comments.length,
    addressedCount,
  };
}

export function getPendingComment(reviewRoot: string): CommentRecord | null {
  const comments = readAllComments(reviewRoot);
  const pending = comments.find((c) => c.status === 'pending');
  return pending ?? null;
}

export function countDispositions(reviewRoot: string): DispositionCounts {
  const comments = readAllComments(reviewRoot);
  const counts: DispositionCounts = {
    agree_implemented: 0,
    better_alternative: 0,
    disagree_defended: 0,
    not_applicable: 0,
  };
  for (const c of comments) {
    if (c.disposition && c.disposition in counts) {
      counts[c.disposition as keyof DispositionCounts] += 1;
    }
  }
  return counts;
}
