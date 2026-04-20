-- 让词典审核队列的 kind 支持 'rejected'，用于「词典管理→驳回同义词」回写场景
ALTER TABLE public.dictionary_review_queue
  DROP CONSTRAINT IF EXISTS dictionary_review_queue_kind_check;

ALTER TABLE public.dictionary_review_queue
  ADD CONSTRAINT dictionary_review_queue_kind_check
  CHECK (kind IN ('new_discovery', 'existing', 'rejected'));

COMMENT ON COLUMN public.dictionary_review_queue.kind IS
  'new_discovery: BERTopic 等离线管线发现；existing: 词典已有词条的别名建议；rejected: 词典管理人工驳回同义词回流';
