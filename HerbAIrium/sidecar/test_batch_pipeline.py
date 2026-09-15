import asyncio
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import server
import utils
from models.configuration import Configuration
from models.metadata import Metadata


PARSE_RESULT = json.dumps({
    "recordNumber": "1",
    "family": "Rosaceae",
    "scientificName": "Rosa woodsii",
    "scientificNameAuthorship": "",
    "eventDate": "2020-01-01",
    "country": "United States",
    "stateProvince": "Colorado",
    "County": "",
    "Locality": "",
    "decimalLatitude": None,
    "decimalLongitude": None,
    "recordedBy": "Collector",
    "associatedCollectors": [],
    "minimumElevationInMeters": None,
})


def _save_metadata(path: str, *, ocr_result=None, ai_result=None) -> None:
    metadata = Metadata(image_path=path)
    metadata.ocr_result = ocr_result
    metadata.ai_result = ai_result
    metadata.save()


async def _batch_events(configuration: Configuration) -> list[dict]:
    events = []
    async for chunk in server._batch_stream(configuration, "provider"):
        events.append(json.loads(chunk.removeprefix("data: ").strip()))
    return events


class FakeBatchClient:
    TERMINAL_STATUSES = {"completed", "failed", "expired", "cancelled"}

    def __init__(
        self,
        *,
        fail_ocr_ids=None,
        stay_running=False,
        reported_completed=0,
        create_delay=0,
        create_started=None,
    ):
        self.fail_ocr_ids = set(fail_ocr_ids or [])
        self.stay_running = stay_running
        self.reported_completed = reported_completed
        self.create_delay = create_delay
        self.create_started = create_started
        self.uploads = {}
        self.upload_stages = []
        self.cancelled = []
        self.deleted_files = []
        self._next_id = 0

    def upload_file(self, path: str) -> str:
        file_id = f"file-{self._next_id}"
        self._next_id += 1
        lines = [
            json.loads(line)
            for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.uploads[file_id] = lines
        self.upload_stages.append(lines[0]["custom_id"].split("-", 1)[0])
        return file_id

    def create_batch(self, input_file_id: str) -> dict:
        if self.create_started is not None:
            self.create_started.set()
        if self.create_delay:
            time.sleep(self.create_delay)
        batch_id = f"batch-{input_file_id}"
        return {
            "id": batch_id,
            "status": "in_progress" if self.stay_running else "completed",
            "input_file_id": input_file_id,
            "output_file_id": f"output-{input_file_id}",
            "request_counts": {
                "completed": (
                    self.reported_completed
                    if self.stay_running
                    else len(self.uploads[input_file_id])
                ),
                "total": len(self.uploads[input_file_id]),
            },
        }

    def retrieve_batch(self, batch_id: str) -> dict:
        input_file_id = batch_id.removeprefix("batch-")
        return self.create_batch(input_file_id)

    def download_file(self, file_id: str) -> str:
        input_file_id = file_id.removeprefix("output-")
        output = []
        for request in self.uploads[input_file_id]:
            custom_id = request["custom_id"]
            if custom_id in self.fail_ocr_ids:
                output.append({
                    "custom_id": custom_id,
                    "response": None,
                    "error": {"message": "OCR failed"},
                })
                continue
            content = "transcription" if custom_id.startswith("ocr-") else PARSE_RESULT
            output.append({
                "custom_id": custom_id,
                "response": {
                    "status_code": 200,
                    "body": {
                        "choices": [{"message": {"content": content}}],
                    },
                },
                "error": None,
            })
        return "\n".join(json.dumps(result) for result in output)

    def cancel_batch(self, batch_id: str) -> None:
        self.cancelled.append(batch_id)

    def delete_file(self, file_id: str) -> None:
        self.deleted_files.append(file_id)


class BatchPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        server._batch_lock = asyncio.Lock()

    def test_invalid_parse_output_is_not_marked_complete(self):
        with tempfile.TemporaryDirectory() as workspace:
            image_path = str(Path(workspace, "pending.jpg"))
            Path(image_path).touch()
            _save_metadata(image_path, ocr_result="text")
            configuration = Configuration(workspace_folder=workspace)

            with patch.object(
                utils,
                "llm_parse_transcription",
                return_value="not valid json",
            ):
                with self.assertRaisesRegex(ValueError, "invalid JSON"):
                    utils.llm_parse_transcription_and_save_results(
                        image_path,
                        configuration,
                    )

            self.assertIsNone(Metadata(image_path=image_path).ai_result)

    def test_economy_batch_limits_scale_with_workspace_size(self):
        mebibyte = 1024 * 1024
        self.assertEqual(server._economy_batch_limits(50), (25 * mebibyte, 1_000))
        self.assertEqual(server._economy_batch_limits(500), (50 * mebibyte, 5_000))
        self.assertEqual(
            server._economy_batch_limits(2_000),
            (100 * mebibyte, 20_000),
        )
        self.assertEqual(
            server._economy_batch_limits(10_000),
            (190 * mebibyte, 50_000),
        )

    async def test_fast_mode_pipelines_parse_before_all_ocr_finishes(self):
        with tempfile.TemporaryDirectory() as workspace:
            fast = str(Path(workspace, "fast.jpg"))
            slow = str(Path(workspace, "slow.jpg"))
            Path(fast).touch()
            Path(slow).touch()
            configuration = Configuration(workspace_folder=workspace)
            configuration.ocr_concurrency = 2
            configuration.parse_concurrency = 1
            timestamps = {}
            timestamp_lock = threading.Lock()

            async def fake_inference(
                _self,
                _client,
                temperature,
                pdf_path=None,
                text=None,
            ):
                if pdf_path:
                    await asyncio.sleep(0.02 if pdf_path == fast else 0.15)
                    with timestamp_lock:
                        timestamps[f"ocr_done:{pdf_path}"] = time.perf_counter()
                    return "text"
                with timestamp_lock:
                    timestamps.setdefault(
                        f"parse_start:{text}",
                        time.perf_counter(),
                    )
                return PARSE_RESULT

            with patch.object(
                server.DeepinfraClient,
                "async_inference",
                fake_inference,
            ):
                events = []
                async for chunk in server._batch_stream(configuration, "realtime"):
                    events.append(
                        json.loads(chunk.removeprefix("data: ").strip())
                    )

            self.assertLess(
                timestamps["parse_start:text"],
                timestamps[f"ocr_done:{slow}"],
            )
            self.assertEqual(events[-1]["ocr_ok"], 2)
            self.assertEqual(events[-1]["llm_ok"], 2)

    async def test_fast_mode_cancellation_does_not_wait_for_request_timeout(self):
        with tempfile.TemporaryDirectory() as workspace:
            pending = str(Path(workspace, "pending.jpg"))
            Path(pending).touch()
            configuration = Configuration(workspace_folder=workspace)
            request_started = asyncio.Event()

            async def slow_inference(
                _self,
                _client,
                temperature,
                pdf_path=None,
                text=None,
            ):
                request_started.set()
                await asyncio.sleep(60)
                return "text"

            with patch.object(
                server.DeepinfraClient,
                "async_inference",
                slow_inference,
            ):
                stream = server._batch_stream(configuration, "realtime")
                event = json.loads(
                    (await anext(stream)).removeprefix("data: ").strip()
                )
                self.assertEqual(event["status"], "running")
                self.assertIn(": 0/1 complete; 0s", event["message"])
                await asyncio.wait_for(request_started.wait(), timeout=0.5)

                started_at = time.perf_counter()
                await stream.aclose()
                elapsed = time.perf_counter() - started_at

            self.assertLess(elapsed, 0.5)

    async def test_submits_ocr_then_parse_provider_batches(self):
        with tempfile.TemporaryDirectory() as workspace:
            complete = str(Path(workspace, "complete.jpg"))
            ocr_only = str(Path(workspace, "ocr-only.jpg"))
            pending = str(Path(workspace, "pending.jpg"))
            for path in (complete, ocr_only, pending):
                Path(path).touch()
            _save_metadata(complete, ocr_result="text", ai_result=PARSE_RESULT)
            _save_metadata(ocr_only, ocr_result="text")
            configuration = Configuration(workspace_folder=workspace)
            fake_batch = FakeBatchClient()

            with patch.object(
                server,
                "DeepinfraBatchClient",
                return_value=fake_batch,
            ):
                events = await _batch_events(configuration)

            summary = events[-1]
            self.assertEqual(fake_batch.upload_stages, ["ocr", "llm"])
            self.assertEqual(len(fake_batch.uploads["file-0"]), 1)
            self.assertEqual(len(fake_batch.uploads["file-1"]), 2)
            self.assertEqual(summary["ocr_ok"], 1)
            self.assertEqual(summary["ocr_skipped"], 2)
            self.assertEqual(summary["llm_ok"], 2)
            self.assertEqual(summary["llm_skipped"], 1)
            self.assertCountEqual(
                fake_batch.deleted_files,
                ["file-0", "output-file-0", "file-1", "output-file-1"],
            )

    async def test_ocr_failure_is_not_included_in_parse_batch(self):
        with tempfile.TemporaryDirectory() as workspace:
            failing = str(Path(workspace, "a-failing.jpg"))
            passing = str(Path(workspace, "b-passing.jpg"))
            Path(failing).touch()
            Path(passing).touch()
            configuration = Configuration(workspace_folder=workspace)
            fake_batch = FakeBatchClient(fail_ocr_ids={"ocr-0"})

            with patch.object(
                server,
                "DeepinfraBatchClient",
                return_value=fake_batch,
            ):
                events = await _batch_events(configuration)

            summary = events[-1]
            self.assertEqual(len(fake_batch.uploads["file-1"]), 1)
            self.assertEqual(summary["ocr_fail"], 1)
            self.assertEqual(summary["ocr_ok"], 1)
            self.assertEqual(summary["llm_ok"], 1)
            self.assertEqual(summary["llm_blocked"], 1)

    async def test_large_stages_are_split_into_multiple_provider_batches(self):
        with tempfile.TemporaryDirectory() as workspace:
            first = str(Path(workspace, "first.jpg"))
            second = str(Path(workspace, "second.jpg"))
            Path(first).touch()
            Path(second).touch()
            configuration = Configuration(workspace_folder=workspace)
            fake_batch = FakeBatchClient()

            with (
                patch.object(
                    server,
                    "DeepinfraBatchClient",
                    return_value=fake_batch,
                ),
                patch.object(server, "MAX_BATCH_REQUESTS", 1),
            ):
                events = await _batch_events(configuration)

            self.assertEqual(
                fake_batch.upload_stages,
                ["ocr", "ocr", "llm", "llm"],
            )
            self.assertEqual(events[-1]["ocr_ok"], 2)
            self.assertEqual(events[-1]["llm_ok"], 2)

    async def test_corrupt_metadata_does_not_abort_other_images(self):
        with tempfile.TemporaryDirectory() as workspace:
            corrupt = str(Path(workspace, "corrupt.jpg"))
            pending = str(Path(workspace, "pending.jpg"))
            Path(corrupt).touch()
            Path(pending).touch()
            Path(corrupt).with_suffix(".json").write_text("{invalid", encoding="utf-8")
            configuration = Configuration(workspace_folder=workspace)
            fake_batch = FakeBatchClient()

            with patch.object(
                server,
                "DeepinfraBatchClient",
                return_value=fake_batch,
            ):
                events = await _batch_events(configuration)

            self.assertEqual(events[-1]["metadata_fail"], 1)
            self.assertTrue(any(
                event.get("filename") == "corrupt.jpg"
                and event.get("status") == "error"
                for event in events
            ))

    async def test_cancellation_cancels_provider_batch(self):
        with tempfile.TemporaryDirectory() as workspace:
            pending = str(Path(workspace, "pending.jpg"))
            Path(pending).touch()
            configuration = Configuration(workspace_folder=workspace)
            fake_batch = FakeBatchClient(
                stay_running=True,
                reported_completed=1,
            )

            with (
                patch.object(
                    server,
                    "DeepinfraBatchClient",
                    return_value=fake_batch,
                ),
                patch.object(server, "BATCH_POLL_SECONDS", 60),
                patch.object(server, "BATCH_CANCEL_POLL_ATTEMPTS", 1),
                patch.object(server, "BATCH_CANCEL_POLL_SECONDS", 0),
            ):
                stream = server._batch_stream(configuration, "provider")
                event = {}
                while event.get("provider_status") != "in_progress":
                    event = json.loads(
                        (await anext(stream)).removeprefix("data: ").strip()
                    )
                self.assertEqual(event["status"], "running")
                self.assertEqual(event["provider_status"], "in_progress")
                self.assertEqual(event["completed_operations"], 1)
                self.assertIn("waiting", event["message"])
                await stream.aclose()

            self.assertEqual(fake_batch.cancelled, ["batch-file-0"])

    async def test_cancellation_during_batch_creation_tracks_new_job(self):
        with tempfile.TemporaryDirectory() as workspace:
            pending = str(Path(workspace, "pending.jpg"))
            Path(pending).touch()
            configuration = Configuration(workspace_folder=workspace)
            create_started = threading.Event()
            fake_batch = FakeBatchClient(
                create_delay=0.1,
                create_started=create_started,
            )

            with patch.object(
                server,
                "DeepinfraBatchClient",
                return_value=fake_batch,
            ), patch.object(
                server,
                "BATCH_CANCEL_POLL_ATTEMPTS",
                1,
            ), patch.object(
                server,
                "BATCH_CANCEL_POLL_SECONDS",
                0,
            ):
                stream = server._batch_stream(configuration, "provider")
                for expected_status in ("preparing", "uploading"):
                    event = json.loads(
                        (await anext(stream)).removeprefix("data: ").strip()
                    )
                    self.assertEqual(event["provider_status"], expected_status)
                next_event = asyncio.create_task(anext(stream))
                self.assertTrue(
                    await asyncio.to_thread(create_started.wait, 0.5)
                )
                next_event.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await next_event
                await stream.aclose()

            self.assertEqual(fake_batch.cancelled, ["batch-file-0"])


if __name__ == "__main__":
    unittest.main()
