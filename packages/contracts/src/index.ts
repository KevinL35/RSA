export type ApiEnvelope<T> = {
  code: string
  message: string
  data: T
}

export type {
  InsightTaskCreateBody,
  InsightTaskListResponse,
  InsightTaskPatchBody,
  InsightTaskRow,
  InsightTaskStatus,
} from './insight-tasks'
