import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from check_agent_pr import check, latest_claim

class CollaborationTests(unittest.TestCase):
    def setUp(self):
        self.branch="agent/governance-he18-collaboration"
        self.body="Agent-ID: governance\nIssue: #18\nWorktree: ../jaegers-governance\nTests: python -m unittest\nHandoff: review required\n"
        self.event={"pull_request":{"number":23,"head":{"ref":self.branch},"body":self.body}}
        self.paths=["AGENTS.md","docs/AGENT_COLLABORATION_PROTOCOL.md"]
        self.comments=[{"body":"<!-- jaegers-claim:v1 agent=governance branch="+self.branch+" paths=AGENTS.md|docs/AGENT_COLLABORATION_PROTOCOL.md -->"}]
    def test_valid(self): self.assertEqual(check(self.event,self.paths,self.comments,{}),[])
    def test_collision(self): self.assertTrue(any("Overlapping" in x for x in check(self.event,self.paths,self.comments,{19:["AGENTS.md"]})))
    def test_unclaimed_file(self): self.assertTrue(any("outside claimed" in x for x in check(self.event,self.paths+["secret.py"],self.comments,{})))
    def test_missing_claim(self): self.assertTrue(any("Missing named" in x for x in check(self.event,self.paths,[],{})))
    def test_identity(self):
        self.event["pull_request"]["body"]=self.body.replace("governance","antigravity")
        self.assertTrue(any("Agent-ID does not match" in x for x in check(self.event,self.paths,self.comments,{})))
    def test_handoff(self):
        comments=self.comments+[{"body":"<!-- jaegers-handoff:v1 branch="+self.branch+" -->"}]
        self.assertIsNone(latest_claim(comments,self.branch))
    def test_single_digit_issue_reference(self):
        self.event["pull_request"]["body"] = self.body.replace("Issue: #18", "Issue: #9")
        self.assertEqual(check(self.event,self.paths,self.comments,{}),[])

    def test_malformed_issue_reference(self):
        self.event["pull_request"]["body"] = self.body.replace("Issue: #18", "Issue: #abc")
        self.assertTrue(any("Issue must be #NN" in x for x in check(self.event,self.paths,self.comments,{})))

    def test_quoted_handoff_is_not_a_handoff(self):
        quoted = self.comments + [{"body": "Maybe later use `<!-- jaegers-handoff:v1 branch="+self.branch+" -->` (example only)"}]
        self.assertIsNotNone(latest_claim(quoted, self.branch))
        inline = self.comments + [{"body": "Text <!-- jaegers-handoff:v1 branch="+self.branch+" --> is a reference only"}]
        self.assertIsNotNone(latest_claim(inline, self.branch))

    def test_old_pr_claim_exempt(self):
        for number in (20, 22):
            self.event["pull_request"]["number"]=number
            self.assertEqual(check(self.event,self.paths,[],{}),[])


    def test_merged_pr_head_reused(self):
        self.event["pull_request"]["head"]["sha"] = "abc123"
        merged = [{"number": 52, "merged_at": "2026-11-08T00:00:00Z",
                   "head": {"sha": "abc123"}}]
        errors = check(self.event, self.paths, self.comments, {}, merged_prs=merged)
        self.assertTrue(any("already integrated" in x for x in errors))

    def test_not_a_duplicate_if_different_head(self):
        self.event["pull_request"]["head"]["sha"] = "new-unique"
        merged = [{"number": 52, "merged_at": "2026-11-08T00:00:00Z",
                   "head": {"sha": "old-unique"}}]
        self.assertEqual(check(self.event, self.paths, self.comments, {},
                               merged_prs=merged), [])

    def test_ancestor_branch_rejected(self):
        errors = check(self.event, self.paths, self.comments, {}, head_ancestor=True)
        self.assertTrue(any("ancestor" in x for x in errors))

    def test_claim_example_not_live(self):
        example = [{"body": "Quoted example: `" + self.comments[0]["body"] + "`"}]
        self.assertIsNone(latest_claim(example, self.branch))
        self.assertTrue(any("Missing named" in x for x in
                            check(self.event, self.paths, example, {})))

    def test_handoff_then_new_claim(self):
        comments = self.comments + [
            {"body": "<!-- jaegers-handoff:v1 branch=" + self.branch + " -->"},
            {"body": self.comments[0]["body"]},
        ]
        self.assertIsNotNone(latest_claim(comments, self.branch))
        self.assertEqual(check(self.event, self.paths, comments, {}), [])

    def test_multiple_issue_lines_rejected(self):
        self.event["pull_request"]["body"] = self.body + "Issue: #65\n"
        errors = check(self.event, self.paths, self.comments, {})
        self.assertTrue(any("Exactly one" in x for x in errors))

    def test_protected_source_from_wrong_agent(self):
        self.event["pull_request"]["body"] = self.body.replace("Agent-ID: governance",
                                                              "Agent-ID: rogue")
        self.event["pull_request"]["head"]["ref"] = self.branch
        protected = ["Jaeger_Main/House_Edge/jaegers_entry/jaeger_model.py"]
        errors = check(self.event, protected, self.comments, {})
        self.assertTrue(any("require release integrator" in x for x in errors))


    def _copilot_case(self):
        branch = "copilot/fill-genuine-regression-gaps"
        self.event["pull_request"]["head"]["ref"] = branch
        self.event["pull_request"]["body"] = (
            "Agent-ID: copilot-he80\\nIssue: #80\\n"
            "Worktree: GitHub cloud isolated sandbox\\n"
            "Tests: python -m pytest tests/test_he80_asof_metamorphic.py -q\\n"
            "Handoff: human review before merge\\n"
        )
        self.paths = ["Jaeger_Main/House_Edge/tests/test_he80_asof_metamorphic.py"]
        self.comments = [{"body": (
            "<!-- jaegers-claim:v1 agent=copilot-he80 "
            "branch=copilot/fill-genuine-regression-gaps "
            "paths=Jaeger_Main/House_Edge/tests/test_he80_asof_metamorphic.py -->"
        )}]

    def test_copilot_valid_claim_and_metadata(self):
        self._copilot_case()
        self.assertEqual(check(self.event, self.paths, self.comments, {}), [])

    def test_copilot_missing_claim_is_blocked(self):
        self._copilot_case()
        errors = check(self.event, self.paths, [], {})
        self.assertTrue(any("Missing named issue claim" in e for e in errors))

    def test_copilot_wrong_claim_owner_is_blocked(self):
        self._copilot_case()
        self.comments[0]["body"] = self.comments[0]["body"].replace("agent=copilot-he80", "agent=rogue")
        errors = check(self.event, self.paths, self.comments, {})
        self.assertTrue(any("Agent-ID does not match" in e for e in errors))

    def test_copilot_unclaimed_file_is_blocked(self):
        self._copilot_case()
        errors = check(self.event, self.paths + ["Jaeger_Main/House_Edge/research/adapters.py"], self.comments, {})
        self.assertTrue(any("Files outside claimed write scope" in e for e in errors))

    def test_copilot_generated_body_missing_metadata_is_blocked(self):
        self._copilot_case()
        self.event["pull_request"]["body"] = "Fixes #80"
        errors = check(self.event, self.paths, self.comments, {})
        self.assertTrue(any("Missing PR field" in e for e in errors))
        self.assertTrue(any("Issue must be #NN" in e for e in errors))

    def test_copilot_malformed_branch_is_blocked(self):
        self._copilot_case()
        self.event["pull_request"]["head"]["ref"] = "copilot/fill_gaps"
        errors = check(self.event, self.paths, self.comments, {})
        self.assertTrue(any("Branch must" in e for e in errors))

    def test_copilot_duplicate_issue_lines_is_blocked(self):
        self._copilot_case()
        self.event["pull_request"]["body"] += "Issue: #81\\n"
        errors = check(self.event, self.paths, self.comments, {})
        self.assertTrue(any("Exactly one canonical Issue" in e for e in errors))

    def test_copilot_overlapping_other_pr_is_blocked(self):
        self._copilot_case()
        errors = check(self.event, self.paths, self.comments, {79: self.paths})
        self.assertTrue(any("Overlapping open PR" in e for e in errors))

    def test_copilot_protected_champion_still_blocked(self):
        self._copilot_case()
        forbidden = ["Jaeger_Main/House_Edge/jaegers_entry/jaeger_model.py"]
        self.comments[0]["body"] = (
            "<!-- jaegers-claim:v1 agent=copilot-he80 "
            "branch=copilot/fill-genuine-regression-gaps "
            "paths=Jaeger_Main/House_Edge/jaegers_entry/jaeger_model.py -->"
        )
        errors = check(self.event, forbidden, self.comments, {})
        self.assertTrue(any("Champion/organizer source changes" in e for e in errors))

if __name__ == "__main__": unittest.main()
