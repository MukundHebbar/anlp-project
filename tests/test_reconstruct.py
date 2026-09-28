import json
import contextlib
import io
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from anlp_project.reconstruct import (
    choose_clues,
    extract_json_object,
    partition_sources,
    public_evidence,
    render_template,
    stable_hash,
    validate_bank,
    validate_evaluation,
    validate_student,
    parse_args,
    accepted_bank,
    condition_evidence,
    has_generated_thinking,
    parse_student_response,
    materialize_disclosure,
    validate_disclosure,
    is_grounded_success,
    is_scored_success,
    reserve_teacher_request,
    audit_sources,
)


class ReconstructTests(unittest.TestCase):
    def test_extracts_plain_or_fenced_json(self) -> None:
        self.assertEqual(extract_json_object('{"x": 1}'), {"x": 1})
        self.assertEqual(extract_json_object('answer\n```json\n{"x": 2}\n```'), {"x": 2})
        self.assertEqual(extract_json_object('{"latex":"\\int_0^1 x dx"}'), {"latex": "\\int_0^1 x dx"})
        self.assertEqual(extract_json_object('{"latex":"\\frac{1}{2} \\times 4"}'), {"latex": "\\frac{1}{2} \\times 4"})

    def test_template_requires_all_values(self) -> None:
        self.assertEqual(render_template("A={{A}}", {"A": "x"}), "A=x")
        with self.assertRaisesRegex(ValueError, "Missing template"):
            render_template("A={{A}} B={{B}}", {"A": "x"})

    def test_bank_allows_one_to_four_honest_clues(self) -> None:
        clue = {"id": "c1", "sentence": "s", "fragment": "f", "hidden_support": "h"}
        parsed = validate_bank({"status": "OK", "clues": [clue], "withheld": "x"})
        self.assertEqual(len(parsed["clues"]), 1)
        with self.assertRaisesRegex(ValueError, "one to four"):
            validate_bank({"status": "OK", "clues": [], "withheld": "x"})

    def test_six_clue_bank_requires_explicit_cap(self) -> None:
        bank = {"status": "OK", "clues": [
            {"id": str(i), "sentence": "s", "fragment": "f", "hidden_support": "h"}
            for i in range(6)]}
        with self.assertRaises(ValueError):
            validate_bank(bank)
        self.assertEqual(len(validate_bank(bank, max_clues=6)["clues"]), 6)
        bank["clues"].append({"id": "6", "sentence": "s", "fragment": "f", "hidden_support": "h"})
        with self.assertRaises(ValueError):
            validate_bank(bank, max_clues=6)

    def test_disclosure_levels_materialize_as_normal_bank(self) -> None:
        value = validate_disclosure(
            {
                "status": "OK",
                "clues": [
                    {
                        "id": "c1",
                        "low": {"sentence": "low", "fragment": "l"},
                        "medium": {"sentence": "medium", "fragment": "m"},
                        "high": {"sentence": "high", "fragment": "h"},
                        "hidden_support": "support",
                        "low_equals_medium": False,
                        "medium_equals_high": False,
                    }
                ],
            }
        )
        bank = materialize_disclosure(value, "high")
        self.assertEqual(bank["clues"][0]["sentence"], "high")

    def test_public_evidence_excludes_hidden_support(self) -> None:
        clues = [{"id": "c1", "sentence": "visible", "fragment": "v", "hidden_support": "secret"}]
        evidence = public_evidence("7", clues)
        self.assertIn("visible", json.dumps(evidence))
        self.assertNotIn("secret", json.dumps(evidence))
        self.assertNotIn("c1", json.dumps(evidence))

    def test_control_conditions_do_not_require_a_bank(self) -> None:
        source = {
            "source_index": 7,
            "question": "Find x.",
            "final_answer": "2",
            "checked_solution": "Use the relation x + 1 = 3. Therefore x = 2.",
        }
        answer_only = condition_evidence(
            source, "answer_only", bank=None, clue_count=1, clue_seed=1, style="sentence"
        )
        self.assertEqual(answer_only["clues"], [])
        full = condition_evidence(
            source, "full_solution", bank=None, clue_count=1, clue_seed=1, style="sentence"
        )
        self.assertIn("x + 1", full["rendered_clues"])

    def test_clue_selection_is_deterministic_and_nested_by_count(self) -> None:
        bank = {
            "clues": [
                {"id": f"c{i}", "sentence": str(i), "fragment": str(i), "hidden_support": str(i)}
                for i in range(1, 5)
            ]
        }
        two = choose_clues(bank, 2, 42)
        four = choose_clues(bank, 4, 42)
        self.assertEqual(two, four[:2])
        self.assertEqual(two, choose_clues(bank, 2, 42))

    def test_anchor_selection_preserves_first_clue(self) -> None:
        bank = {
            "clues": [
                {"id": f"c{i}", "sentence": str(i), "fragment": str(i), "hidden_support": str(i)}
                for i in range(1, 5)
            ]
        }
        selected = choose_clues(bank, 3, 42, "anchor_first")
        self.assertEqual(selected[0]["id"], "c1")
        self.assertEqual(selected, choose_clues(bank, 3, 42, "anchor_first"))
        self.assertEqual(selected[:2], choose_clues(bank, 2, 42, "anchor_first"))

    def test_partition_is_balanced_and_complete(self) -> None:
        records = []
        index = 0
        for topic in ("Algebra", "Number Theory", "Discrete Mathematics", "Calculus"):
            for _ in range(15):
                records.append({"source_index": index, "broad_topic": topic, "difficulty": 5})
                index += 1
        partitions = partition_sources(records, 7)
        self.assertEqual(len(partitions["D1"]), 12)
        self.assertEqual(len(partitions["D2"]), 12)
        self.assertEqual(len(partitions["C"]), 24)
        self.assertEqual(len(partitions["reserve"]), 12)
        all_indices = sum(partitions.values(), [])
        self.assertEqual(len(all_indices), len(set(all_indices)))

    def test_role_cue_preserves_base_evidence_order(self) -> None:
        clues = [{"id":f"c{i}","sentence":str(i),"fragment":str(i),"hidden_support":str(i)} for i in range(4)]
        role = {"id":"role","sentence":"An extremal size.","fragment":"Extremal size","hidden_support":"Source"}
        expected = choose_clues({"clues":clues},4,42)
        augmented = {"clues":clues+[role],"role_cue_id":"role"}
        self.assertEqual(choose_clues(augmented,5,42),expected+[role])
        with self.assertRaisesRegex(ValueError,"complete bank"):
            choose_clues(augmented,4,42)

    def test_student_and_evaluation_schemas(self) -> None:
        student = validate_student({"question": "Q?", "justification": "Because", "assumptions": []})
        self.assertEqual(student["question"], "Q?")
        evaluation = validate_evaluation({"status": "scored", "score": 3, "reason": "valid"})
        self.assertEqual(evaluation["score"], 3)
        with self.assertRaisesRegex(ValueError, "null"):
            validate_evaluation({"status": "needs_review", "score": 2, "reason": "unknown"})

    def test_grounded_success_requires_substantive_checks(self) -> None:
        value = {
            "status": "scored",
            "score": 4,
            "well_posed": True,
            "answer_correct": True,
            "shortcut": False,
            "clue_checks": [{"compatible": True, "grounding": "explicit"}],
        }
        self.assertTrue(is_grounded_success(value))
        value["clue_checks"][0]["grounding"] = "unsupported"
        self.assertFalse(is_grounded_success(value))
        self.assertTrue(is_scored_success(value))

    def test_tolerant_student_parser_marks_format_error(self) -> None:
        exact, exact_error = parse_student_response(
            '{"question":"Q?","justification":"Because","assumptions":[]}'
        )
        self.assertFalse(exact_error)
        self.assertEqual(exact["question"], "Q?")
        fallback, fallback_error = parse_student_response("Question: Q?\nJustification: Because")
        self.assertTrue(fallback_error)
        self.assertEqual(fallback["justification"], "Because")

    def test_generated_thinking_detection_ignores_empty_template_tag(self) -> None:
        self.assertFalse(has_generated_thinking({"content": "<think></think>{}", "reasoning": None}))
        self.assertTrue(has_generated_thinking({"content": "<think>hidden</think>{}", "reasoning": None}))
        self.assertTrue(has_generated_thinking({"content": "{}", "reasoning": "hidden"}))

    def test_parser_recovers_missing_assumption_bracket_without_rewriting_content(self) -> None:
        malformed = '{"justification":"The calculation is 2+2=4.","assumptions":["Positive integers.","No other constraints.","question":"What is 2+2?"}'
        parsed, format_error = parse_student_response(malformed)
        self.assertTrue(format_error)
        self.assertEqual(parsed["question"], "What is 2+2?")
        self.assertEqual(parsed["justification"], "The calculation is 2+2=4.")
        self.assertEqual(parsed["assumptions"], ["Positive integers.", "No other constraints."])

    def test_hash_changes_with_configuration(self) -> None:
        self.assertNotEqual(stable_hash({"prompt": "a"}), stable_hash({"prompt": "b"}))

    def test_reasoning_effort_uses_provider_enum(self) -> None:
        args = parse_args(["init", "--reasoning-effort", "high"])
        self.assertEqual(args.reasoning_effort, "high")
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parse_args(["init", "--reasoning-effort", "64"])

    def test_student_requires_an_accepted_audit(self) -> None:
        run = {
            "banks": {"bank": {"source_index": 1, "output": {"status": "OK", "clues": []}}},
            "audits": {},
        }
        with self.assertRaisesRegex(ValueError, "No accepted"):
            accepted_bank(run, 1)
        run["audits"]["audit"] = {
            "source_index": 1,
            "bank_key": "bank",
            "output": {"status": "ACCEPT"},
        }
        self.assertEqual(accepted_bank(run, 1)[0], "bank")
        run["audits"]["revised_audit"] = {
            "source_index": 1, "bank_key": "bank", "output": {"status": "REJECT"}
        }
        with self.assertRaisesRegex(ValueError, "No accepted"):
            accepted_bank(run, 1)

    def test_teacher_budget_reservation_blocks_before_request(self) -> None:
        run = {"banks": {}, "audits": {}, "evaluations": {}, "source_recovery": {}}
        with self.assertRaisesRegex(RuntimeError, "cost cap"):
            reserve_teacher_request(run, "x" * 1000, 10_000, 0.001)

    def test_required_audits_are_conjunctive_not_last_accept_wins(self) -> None:
        run = {'metadata': {'required_bank_audits': {'convert_p2': ['support', 'public']}},
               'banks': {'b': {'source_index': 1, 'prompt': 'convert_p2', 'output': {'status': 'OK'}}},
               'audits': {'p': {'source_index': 1, 'bank_key': 'b', 'prompt': 'public', 'output': {'status': 'ACCEPT'}}}}
        with self.assertRaises(ValueError):
            accepted_bank(run, 1, 'convert_p2')
        run['audits']['s'] = {'source_index': 1, 'bank_key': 'b', 'prompt': 'support', 'output': {'status': 'REJECT'}}
        run['audits']['p2'] = {'source_index': 1, 'bank_key': 'b', 'prompt': 'public', 'output': {'status': 'ACCEPT'}}
        with self.assertRaises(ValueError):
            accepted_bank(run, 1, 'convert_p2')
        run['audits']['s2'] = {'source_index': 1, 'bank_key': 'b', 'prompt': 'support', 'output': {'status': 'ACCEPT'}}
        self.assertEqual(accepted_bank(run, 1, 'convert_p2')[0], 'b')

    def test_fixed_prefix_cannot_be_reshuffled_or_silently_shortened(self) -> None:
        bank = {'clues':[{'id':'c1'},{'id':'c2'}], 'fixed_order_ids':['c2','c1'], 'fixed_order_seed':7}
        self.assertEqual([c['id'] for c in choose_clues(bank,2,7)],['c2','c1'])
        for count,seed in [(1,7),(2,8)]:
            with self.assertRaises(ValueError):
                choose_clues(bank,count,seed)
        with self.assertRaises(ValueError):
            choose_clues(bank,2,7,'anchor_first')

    def test_public_disclosure_auditor_never_receives_private_source(self) -> None:
        run = {"sources":{"1":{"question":"PRIVATE_QUESTION","checked_solution":"PRIVATE_SOLUTION","final_answer":"7"}},
               "banks":{"b":{"source_index":1,"prompt":"role_augmented","output":{"status":"OK","clues":[
                   {"id":"c1","sentence":"Public observation.","fragment":"Public","hidden_support":"PRIVATE_SUPPORT"}]}}},
               "audits":{},"failures":[]}
        def respond(client,prompt,*args):
            self.assertIn("Public observation.",prompt)
            self.assertNotIn("PRIVATE_",prompt)
            return {"content":'{"status":"ACCEPT","reason":"Partial."}',"usage":{}}
        with tempfile.TemporaryDirectory() as tmp:
            args=parse_args(["audit","--audit-prompt","audit_role_p3","--bank-prompt","role_augmented", "--output",str(Path(tmp)/"run.json")])
            with patch("anlp_project.reconstruct.deepinfra_client"), patch("anlp_project.reconstruct.teacher_call",side_effect=respond), contextlib.redirect_stdout(io.StringIO()):
                audit_sources(args,run,[1])
            self.assertEqual(len(run["audits"]),1)
            self.assertEqual(run["failures"],[])


if __name__ == "__main__":
    unittest.main()
