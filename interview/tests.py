from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from interview.models import GPTQuestion, Interview, UserAnswer
from result.models import Result
from resume.models import Resume
from user.models import User

FAKE_FEEDBACK = {
    "overall_feedback": [{"content": "지원자의 답변은 논리적입니다."}, {"score": [15, 14, 13, 12, 16]}],
    "answer_feedback": [{"question": "Q", "answer": "A", "feedback": "좋습니다."}],
    "behavior_feedback": {"behavior_data": [], "feedback_data": "시선 처리가 안정적입니다."},
}


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class InterviewResultAsyncTest(TestCase):
    """피드백 생성이 요청에서 분리되어 Celery 작업으로 처리되는지 검증한다."""

    def setUp(self):
        self.user = User.objects.create_user(email="tester@example.com", nickname="tester", password="pw")
        self.user.save()
        resume = Resume.objects.create(user=self.user, filename="resume.pdf", file_url="https://example.com/r.pdf")
        self.interview = Interview.objects.create(user=self.user, resume=resume, questions_count=3)
        q = GPTQuestion.objects.create(interview=self.interview, content="자기소개 해주세요.")
        UserAnswer.objects.create(question=q, content="안녕하세요.")
        self.result = Result.objects.create(
            interview=self.interview,
            video_url="https://example.com/v.webm",
            behavior_data=[{"event": "gaze", "duration": 3}],
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = f"/api/apps/result/{self.interview.id}"

    @patch("interview.tasks.generate_feedback", return_value=FAKE_FEEDBACK)
    def test_post_returns_202_then_get_returns_feedback(self, mock_generate):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            res = self.client.post(self.url)

        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data["status"], "PENDING")
        self.assertEqual(len(callbacks), 1)  # 커밋 후에 작업이 한 번 발행됨
        mock_generate.assert_called_once()

        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "DONE")
        self.assertIn("종합피드백", res.data["feedback"])

    @patch("interview.views.generate_feedback_task.delay")
    def test_duplicate_post_enqueues_only_once(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            first = self.client.post(self.url)
        with self.captureOnCommitCallbacks(execute=True):
            second = self.client.post(self.url)

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(second.data["status"], "PENDING")
        mock_delay.assert_called_once_with(self.result.id)

    @patch("interview.tasks.generate_feedback", return_value=FAKE_FEEDBACK)
    def test_post_after_done_returns_existing_result(self, mock_generate):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url)
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            res = self.client.post(self.url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "DONE")
        self.assertEqual(len(callbacks), 0)
        mock_generate.assert_called_once()

    @patch("interview.tasks.generate_feedback", return_value=None)
    def test_gpt_failure_retries_then_marks_failed_and_allows_requeue(self, mock_generate):
        from interview.tasks import generate_feedback_task

        with patch("interview.views.generate_feedback_task.delay"):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(self.url)

        # 워커가 받은 첫 실행(재시도 0회): 실패하면 PENDING으로 되돌리고 재시도를 예약한다.
        from celery.exceptions import Retry
        with self.assertRaises(Retry):  # 재시도 예약 신호
            generate_feedback_task.apply(args=[self.result.id], retries=0)
        self.result.refresh_from_db()
        self.assertEqual(self.result.feedback_status, "PENDING")

        # 마지막 재시도(재시도 2회째)도 실패하면 FAILED로 끝난다.
        generate_feedback_task.apply(args=[self.result.id], retries=2)
        self.result.refresh_from_db()
        self.assertEqual(self.result.feedback_status, "FAILED")
        self.assertEqual(mock_generate.call_count, 2)

        res = self.client.get(self.url)
        self.assertEqual(res.data["status"], "FAILED")

        # 실패한 결과는 다시 요청하면 새 작업이 발행된다.
        with patch("interview.views.generate_feedback_task.delay") as mock_delay:
            with self.captureOnCommitCallbacks(execute=True):
                res = self.client.post(self.url)
        self.assertEqual(res.status_code, 202)
        mock_delay.assert_called_once()

    def test_task_skips_when_not_pending(self):
        from interview.tasks import generate_feedback_task

        Result.objects.filter(id=self.result.id).update(feedback_status="PROCESSING")
        with patch("interview.tasks.generate_feedback") as mock_generate:
            generate_feedback_task.delay(self.result.id)  # 중복 전달된 메시지 상황
        mock_generate.assert_not_called()

    def test_get_before_request_returns_404(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 404)

    def test_other_users_interview_is_not_found(self):
        other = User.objects.create_user(email="other@example.com", nickname="o", password="pw")
        other.save()
        client = APIClient()
        client.force_authenticate(other)
        res = client.post(self.url)
        self.assertEqual(res.status_code, 404)
