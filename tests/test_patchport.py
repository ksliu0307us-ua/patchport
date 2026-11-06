import json,os,stat,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest import mock
from patchport.apply import apply_bundle,check_target
from patchport.bundles import BundleError,bundle_from_data,create_bundle,load_bundle,save_bundle,serialize_bundle
from patchport.paths import PathError,safe_target,validate_bundle_path

class PatchTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.before=self.base/"before";self.after=self.base/"after";self.root=self.base/"root";(self.root/"docs").mkdir(parents=True);self.target=self.root/"docs/x.txt"
 def tearDown(self):self.tmp.cleanup()
 def bundle(self,before=b"old\n",after=b"new\n"):
  self.before.write_bytes(before);self.after.write_bytes(after);self.target.write_bytes(before);return create_bundle(self.before,self.after,"docs/x.txt")
 def test_deterministic_roundtrip_unicode_crlf_bom_empty_no_newline(self):
  cases=[(b"",b""),(b"old",b"new"),(b"old\r\n",b"new\r\n"),(b"\xef\xbb\xbfold",b"\xef\xbb\xbfnew"),("old 雪".encode(),"new 雪".encode())]
  for i,(before,after) in enumerate(cases):
   with self.subTest(i=i):
    b=self.bundle(before,after);one=serialize_bundle(b);self.assertEqual(one,serialize_bundle(b));p=self.base/f"{i}.json";save_bundle(p,b);self.assertEqual(load_bundle(p),b);self.assertEqual(load_bundle(p).after_text.encode(),after)
 def test_invalid_utf8_and_nul(self):
  self.before.write_bytes(b"\xff");self.after.write_bytes(b"ok")
  with self.assertRaises(BundleError):create_bundle(self.before,self.after,"x")
  self.before.write_bytes(b"ok");self.after.write_bytes(b"a\0b")
  with self.assertRaises(BundleError):create_bundle(self.before,self.after,"x")
 def test_duplicate_unknown_tampered_hash(self):
  p=self.base/"bad.json";p.write_text('{"schema_version":1,"schema_version":1}',encoding="utf-8")
  with self.assertRaisesRegex(BundleError,"duplicate"):load_bundle(p)
  b=self.bundle();d=json.loads(serialize_bundle(b));d["extra"]=1
  with self.assertRaises(BundleError):bundle_from_data(d)
  d.pop("extra");d["after_sha256"]="0"*64
  with self.assertRaisesRegex(BundleError,"does not match"):bundle_from_data(d)
 def test_invalid_paths(self):
  for p in ("","/x","../x","a/../x","a\\x","C:/x","//server/share","a//b",".git/config","a/.GIT/x"):
   with self.subTest(p=p),self.assertRaises(PathError):validate_bundle_path(p)
 def test_symlink_rejection_when_supported(self):
  link=self.root/"link"
  try:link.symlink_to(self.root/"docs",target_is_directory=True)
  except OSError as e:self.skipTest(f"symlink unavailable: {e}")
  with self.assertRaises(PathError):safe_target(self.root,"link/x.txt")
 def test_ready_apply_permissions_and_already_no_rewrite(self):
  b=self.bundle();os.chmod(self.target,0o640);expected_mode=stat.S_IMODE(self.target.stat().st_mode);self.assertEqual(check_target(b,self.root).status,"ready");self.assertEqual(apply_bundle(b,self.root).status,"applied");self.assertEqual(self.target.read_bytes(),b"new\n");self.assertEqual(stat.S_IMODE(self.target.stat().st_mode),expected_mode);stamp=self.target.stat().st_mtime_ns;time.sleep(.01);self.assertEqual(apply_bundle(b,self.root).status,"already_applied");self.assertEqual(self.target.stat().st_mtime_ns,stamp)
 def test_conflict_missing_nonfile_and_dry_run(self):
  b=self.bundle();original=self.target.read_bytes();r=apply_bundle(b,self.root,True);self.assertEqual(r.status,"ready");self.assertIn("---",r.diff);self.assertEqual(self.target.read_bytes(),original);self.target.write_bytes(b"other");self.assertEqual(apply_bundle(b,self.root).status,"conflict");self.target.unlink();self.assertEqual(check_target(b,self.root).status,"conflict");self.target.mkdir();self.assertEqual(check_target(b,self.root).status,"conflict")
 def test_baseline_change_rechecked_and_temp_cleaned(self):
  b=self.bundle();import patchport.apply as module;original=module._write_temp
  def mutate(target,data,mode):
   temp=original(target,data,mode);target.write_bytes(b"concurrent");return temp
  with mock.patch("patchport.apply._write_temp",side_effect=mutate):self.assertEqual(apply_bundle(b,self.root).status,"conflict")
  self.assertEqual(list(self.target.parent.glob(".patchport-*.tmp")),[]);self.assertEqual(self.target.read_bytes(),b"concurrent")
 def test_replace_failure_cleans_temp(self):
  b=self.bundle()
  with mock.patch("patchport.apply.os.replace",side_effect=OSError("injected")):
   with self.assertRaisesRegex(OSError,"injected"):apply_bundle(b,self.root)
  self.assertEqual(list(self.target.parent.glob(".patchport-*.tmp")),[]);self.assertEqual(self.target.read_bytes(),b"old\n")
 def test_existing_bundle_preserved(self):
  b=self.bundle();p=self.base/"out.json";p.write_text("sentinel")
  with self.assertRaises(FileExistsError):save_bundle(p,b)
  self.assertEqual(p.read_text(),"sentinel")

class CliTests(unittest.TestCase):
 def test_workflow_exit_codes_json_and_preservation(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);before=root/"b";after=root/"a";before.write_bytes(b"old");after.write_bytes(b"new");work=root/"work";(work/"docs").mkdir(parents=True);target=work/"docs/x";target.write_bytes(b"old");bundle=root/"p.json";env=os.environ.copy();src=Path(__file__).resolve().parents[1];env["PYTHONPATH"]=str(src)+((os.pathsep+env["PYTHONPATH"]) if env.get("PYTHONPATH") else "")
   def run(*a):return subprocess.run([sys.executable,"-m","patchport",*map(str,a)],cwd=root,env=env,text=True,encoding="utf-8",capture_output=True)
   self.assertEqual(run("make",before,after,"--path","docs/x","--output",bundle).returncode,0);self.assertEqual(run("inspect",bundle,"--format","json").returncode,0);self.assertEqual(json.loads(run("check",bundle,"--root",work,"--format","json").stdout)["status"],"ready");original=target.read_bytes();self.assertEqual(run("apply",bundle,"--root",work,"--dry-run").returncode,0);self.assertEqual(target.read_bytes(),original);self.assertEqual(run("apply",bundle,"--root",work).returncode,0);self.assertEqual(run("apply",bundle,"--root",work).returncode,0);target.write_bytes(b"conflict");self.assertEqual(run("check",bundle,"--root",work).returncode,1)

if __name__=="__main__":unittest.main()
