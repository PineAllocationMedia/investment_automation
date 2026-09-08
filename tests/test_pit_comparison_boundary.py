import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pit_comparison.boundary import clean_environment


class PITBoundaryTests(unittest.TestCase):
    def probe(self, operation):
        with tempfile.TemporaryDirectory(prefix="pit-boundary-test-") as t:
            root=Path(t).resolve(); worker=root/"worker"; worker.mkdir()
            source=root/"source"; source.mkdir(); (source/"code.py").write_text("# code")
            bundle=root/"bundle"; bundle.mkdir(); (bundle/"input.json").write_text("{}")
            peer=root/"peer"; peer.mkdir(); (peer/"secret").write_text("synthetic private value")
            harness=Path(__file__).resolve().parents[1]
            env=clean_environment(worker)
            code='''
import json,sys,os,socket,subprocess
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from pit_comparison.boundary import Boundary,dependency_roots,platform_roots
root=Path(sys.argv[2]); worker=root/'worker'; source=root/'source'; bundle=root/'bundle'; peer=root/'peer'
b=Boundary(read_roots=[worker,source,bundle,Path(sys.argv[1]),*dependency_roots(),*platform_roots()],writable_root=worker,immutable_roots=[source,bundle],forbidden_roots=[peer])
b.install()
try:
    exec(sys.argv[3])
except Exception:
    pass
print(json.dumps(b.status()))
'''
            result=subprocess.run([sys.executable,"-I","-B","-c",code,str(harness),str(root),operation],
                env=env,cwd=worker,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            return json.loads(result.stdout)

    def test_network_dns_subprocess_and_caught_violation(self):
        attempts=["socket.socket()", "socket.getaddrinfo('example.invalid',443)",
                  "subprocess.run(['/usr/bin/true'])", "os.system('true')", "os.fork()",
                  "import yfinance", "import urllib.request; urllib.request.urlopen('https://example.invalid')"]
        for action in attempts:
            with self.subTest(action=action):
                result=self.probe(action)
                self.assertEqual(result["status"],"CONTAINMENT_FAILED",result)
                self.assertTrue(result["violations"])
                self.assertEqual(result["containment_level"],"APPLICATION_GUARDED")

    def test_read_write_metadata_and_descriptor_boundary(self):
        attempts=["(peer/'secret').read_text()", "(peer/'x').write_text('x')", "(bundle/'input.json').write_text('x')",
                  "(source/'code.py').write_text('x')", "(peer/'secret').stat()", "list(peer.iterdir())",
                  "Path('/etc/passwd').read_text()", "os.read(0,10)", "os.symlink(peer/'secret',worker/'link')",
                  "fd=os.open(source,os.O_RDONLY); os.unlink('code.py',dir_fd=fd)"]
        for action in attempts:
            with self.subTest(action=action):
                self.assertEqual(self.probe(action)["status"],"CONTAINMENT_FAILED")
        self.assertEqual(self.probe("(worker/'scratch').write_text('ok'); (worker/'scratch').read_text()")["status"],"PASSED")

    def test_environment_has_no_application_credentials(self):
        with tempfile.TemporaryDirectory() as t:
            env=clean_environment(Path(t).resolve())
            self.assertFalse(any('TOKEN' in k or 'KEY' in k or k.startswith('INVESTMENT_') for k in env))
            self.assertTrue(all(str(Path(t).resolve()) in env[k] for k in ('HOME','XDG_CACHE_HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','TMPDIR')))
