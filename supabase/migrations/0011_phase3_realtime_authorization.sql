-- Maps to: ENG-011, SEC-013

ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS realtime_job_progress_subscribe ON realtime.messages;
DROP POLICY IF EXISTS realtime_job_progress_publish ON realtime.messages;

CREATE POLICY realtime_job_progress_subscribe
ON realtime.messages
FOR SELECT
TO authenticated
USING (
  realtime.messages.extension = 'broadcast'
  AND EXISTS (
    SELECT 1
    FROM public.media_jobs
    WHERE public.media_jobs.progress_topic = realtime.topic()
      AND public.media_jobs.owner_user_id = auth.uid()
  )
);

CREATE POLICY realtime_job_progress_publish
ON realtime.messages
FOR INSERT
TO service_role
WITH CHECK (
  realtime.messages.extension = 'broadcast'
  AND realtime.topic() LIKE 'job_progress:%'
);
