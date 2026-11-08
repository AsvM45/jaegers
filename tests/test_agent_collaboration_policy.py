import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from check_agent_pr import check, latest_claim

class CollaborationTests(unittest.TestCase):
    def setUp(self):
        self.branch="agent/governance-he18-collaboration"
        self.body="Agent-ID: governance\nIssue: #18\nWorktree: ../jaegers-governance\nTests: python -m unittest\nHandoff: review required\n"
        self.event={"pull_request":{"number":22,"head":{"ref":self.branch},"body":self.body}}
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
    def test_old_pr_claim_exempt(self):
        self.event["pull_request"]["number"]=20
        self.assertEqual(check(self.event,self.paths,[],{}),[])

if __name__ == "__main__": unittest.main()
