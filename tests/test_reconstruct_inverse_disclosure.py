import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from anlp_project import reconstruct as r


class InverseDisclosureValidationTests(unittest.TestCase):
    def test_candidate_aliases_reject_contradictory_acceptance(self):
        for prompt,scope in [('audit_public_p5','public_disclosure'),('audit_source_disclosure_p3','source_disclosure'),('audit_source_disclosure_p4','source_disclosure')]:
            with self.subTest(prompt=prompt),tempfile.TemporaryDirectory() as d:
                run={'sources':{'0':{'question':'Solve3x+2=14.','final_answer':'4','checked_solution':'3x=12; x=4.'}},
                     'banks':{'b':{'source_index':0,'prompt':'fixture','model':'authored_fixture','output':{
                         'status':'OK','clues':[{'id':'c1','sentence':'The equation is3x+2=14.'}]}}},
                     'audits':{},'responses':{},'evaluations':{},'source_recovery':{},'failures':[]}
                result={'status':'ACCEPT','scope':scope,'direct_question_copy':True,
                    'premise_target_bundle_exposed':False,'complete_solution_exposed':False,
                    'public_quotes':['The equation is3x+2=14.'],'missing_essential_element':'none',
                    'inference_required':'none','reason':'Contradictory malicious acceptance fixture.'}
                args=r.parse_args(['audit','--output',str(Path(d)/'run.json'),'--audit-prompt',prompt,'--bank-prompt','fixture'])
                with patch.object(r,'deepinfra_client',return_value=object()),patch.object(r,'teacher_call',return_value={'content':json.dumps(result)}):
                    r.audit_sources(args,run,[0])
                self.assertEqual(run['audits'],{})
                self.assertEqual(len(run['failures']),1)
                self.assertIn('Acceptance contradicts',run['failures'][0]['error'])
