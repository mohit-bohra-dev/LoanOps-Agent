/**
 * Types for MR review local tracking (review-tracker CLI).
 */

export type ReviewSessionStatus = 'in_progress' | 'complete';

export type CommentStatus = 'pending' | 'in_progress' | 'addressed';

export type Disposition =
  | 'agree_implemented'
  | 'better_alternative'
  | 'disagree_defended'
  | 'not_applicable';

export interface ReviewState {
  project_id: string;
  mr_iid: number;
  mr_url: string;
  branch: string;
  /** Directory name segment: sanitized_branch-mr_iid */
  review_dir_name: string;
  fetched_at: string;
  total_comments: number;
  addressed: number;
  pending: number;
  status: ReviewSessionStatus;
}

export interface CommentRecord {
  discussion_id: string;
  note_id: number | string | null;
  author: string;
  body: string;
  file: string | null;
  old_line: number | null;
  new_line: number | null;
  code_context: string | null;
  resolved_on_gitlab: boolean;
  status: CommentStatus;
  disposition: Disposition | null;
  response: string | null;
  changes_made: string | null;
  addressed_at: string | null;
}

/** One row from Phase 2 before init (AI builds from GitLab MCP). */
export interface InitCommentInput {
  discussion_id: string;
  note_id?: number | string | null;
  author: string;
  body: string;
  file?: string | null;
  old_line?: number | null;
  new_line?: number | null;
  code_context?: string | null;
  resolved_on_gitlab?: boolean;
}

/** stdin JSON for `init` command */
export interface InitPayload {
  project_id: string;
  mr_iid: number;
  mr_url: string;
  /** Source branch name (e.g. feature/dev/foo) */
  branch: string;
  comments: InitCommentInput[];
}

/** stdin JSON for `address-comment` command */
export interface AddressPayload {
  disposition: Disposition;
  response: string;
  changes_made: string | null;
}

export interface CheckAllResult {
  ok: boolean;
  pendingDiscussionIds: string[];
  total: number;
  addressedCount: number;
}

export interface DispositionCounts {
  agree_implemented: number;
  better_alternative: number;
  disagree_defended: number;
  not_applicable: number;
}
