"""Export audited native evidence and remote image-review copies from Windows CI."""
import base64, hashlib, io, json, os, subprocess, zipfile
from pathlib import Path
from PIL import Image
from tools.story_model import ROOT, load_story
from tools.compile_tests import render_persistence_tests
from tools.build.verify_package import validate_native_report, required_screenshots
from tools.build.verify_upgrade import render_upgrade_writer, render_upgrade_reader, BASELINE_SHA256, BASELINE_VERSION
from tools.build.verify_voice_smoke import prefix_plan, PREFIX_CASES
from tools.build.review_transport import write_bundles

def digest(p):
    with Path(p).open("rb") as f: return hashlib.file_digest(f, "sha256").hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def require(c, message):
    if not c: raise ValueError(message)
def safe(z):
    names=z.namelist()
    require(len(names)==len(set(names)), "Duplicate ZIP entries")
    require(all(not n.startswith(("/", "\\")) and "\\" not in n and ":" not in n and ".." not in n.split("/") for n in names), "Unsafe ZIP entries")
    require(z.testzip() is None, "ZIP CRC failed")

def main():
    require(os.name=="nt", "This exporter requires the actual Windows runner")
    version=(ROOT/"VERSION").read_text().strip(); require(version=="1.2.0", "Wrong version")
    candidate=os.environ["GITHUB_SHA"]; run_id=int(os.environ["GITHUB_RUN_ID"])
    reports=ROOT/"reports"; dist=ROOT/"dist"; story=load_story()
    plan=(ROOT/"game/testcases.rpy").read_text(encoding="utf-8")
    plans={
        "source":(plan,"source-process","screenshots"),
        "standalone":(plan,"package","package/screenshots"),
        "fresh_process":(render_persistence_tests(story),"package/persistence","package/persistence/screenshots"),
        "upgrade_writer":(render_upgrade_writer(story),"upgrade/writer","upgrade/writer/screenshots"),
        "upgrade_reader":(render_upgrade_reader(story),"upgrade/reader","upgrade/reader/screenshots"),
    }
    suites={}; shots=[]
    for scope,(test,process_path,image_path) in plans.items():
        d=reports/process_path
        summary=validate_native_report((d/"stdout.txt").read_text(encoding="utf-8-sig"),test)
        process=read(d/"process.json"); require(process["returncode"]==0 and process["timed_out"] is False,scope+" failed")
        required=required_screenshots(test)
        require(sorted(p.stem for p in (reports/image_path).glob("*.png"))==required,scope+" screenshot set differs")
        recorded=read(reports/("acceptance.json" if scope=="source" else process_path+"/acceptance.json"))
        for key in ("cases","assertions","failed","xfailed","xpassed","skipped","not_run"):
            require(recorded[key]==summary[key],scope+" summary differs")
        require(recorded["screenshots_checked"]==len(required),scope+" image count differs")
        summary.update({"screenshots_checked":len(required),"process":process,"report_sha256":digest(d/"stdout.txt"),
            "report_path":"reports/"+process_path+"/stdout.txt","test_plan_sha256":hashlib.sha256(test.encode()).hexdigest(),"required_screenshots":required})
        suites[scope]=summary
        for name in required:
            p=reports/image_path/(name+".png"); size=(1280,720) if name.startswith("scaled-") else (1920,1080)
            with Image.open(p) as im: im.load(); require(im.size==size,"Wrong PNG dimensions")
            shots.append({"scope":scope,"name":name,"path":"reports/"+image_path+"/"+name+".png","pixels":list(size),"sha256":digest(p)})
    require(len(shots)==174 and [(suites[s]["cases"],suites[s]["assertions"]) for s in plans]
        ==[(36,448),(36,448),(1,16),(1,14),(2,26)],"Native counts differ")
    package=dist/f"BeforeTheRainStops-{version}-win.zip"; package_sha=digest(package); licenses=[]
    require((dist/"SHA256SUMS.txt").read_text(encoding="utf-8-sig").split()==[package_sha,package.name],"Checksum file differs")
    with zipfile.ZipFile(package) as z:
        safe(z); root=f"BeforeTheRainStops-{version}-win/"
        require(all(n.startswith(root) for n in z.namelist()),"Package root differs")
        require(root+"BeforeTheRainStops.exe" in z.namelist(),"EXE missing")
        for name in z.namelist():
            relative=name[len(root):]
            require(not relative.startswith(("game/data/","game/tests/","game/saves/","assets_source/","tools/","tests/","prompts/",".git/","old-game/","game/testcases.")) and not relative.endswith((".onnx",".pt",".pth",".safetensors")),"Private files in package")
        assets=read(ROOT/"game/data/asset_manifest.json")["assets"];require(len(assets)==85,"Asset count differs")
        for a in assets:
            raw=z.read(root+"game/"+a["file"])
            require(hashlib.sha256(raw).hexdigest()==a["sha256"] and raw==(ROOT/"game"/a["file"]).read_bytes(),"Asset differs "+a["id"])
        for path in ("licenses/Kokoro-model-Apache-2.0.txt","licenses/SourceHanSans-OFL.txt","licenses/Qwen3-TTS-Apache-2.0.txt","licenses/RENPY.txt","LICENSE","CREDITS.md"):
            source=(ROOT/path).read_bytes(); packed=z.read(root+path)
            require(source.replace(b"\r\n",b"\n")==packed.replace(b"\r\n",b"\n"),"License differs "+path)
            licenses.append({"path":path,"checkout_sha256":hashlib.sha256(source).hexdigest(),"packaged_sha256":hashlib.sha256(packed).hexdigest(),"comparison":"identical_bytes" if source==packed else "CRLF_to_LF_only"})
        player=z.read(root+"PLAYER_README.txt").decode()
        require(player.replace("\r\n","\n")== (ROOT/"PLAYER_README.txt").read_text() and f"版本：{version}" in player and "鉴赏室" in player,"Player instructions differ")
        info=json.loads(z.read(root+"game/cache/build_info.json")); require(info["version"]==version,"Build version differs")
        pkg={"file":package.name,"size_in_bytes":package.stat().st_size,"sha256":package_sha,"entries":len(z.namelist()),"crc":"passed",
            "test_scripts_in_original_zip":False,"assets_checked":85,"build_info":info,"license_and_credits_documents":licenses}
    upgrade=read(reports/"upgrade/acceptance.json")
    require(upgrade["status"]=="passed" and upgrade["previous_version"]==BASELINE_VERSION and upgrade["current_version"]==version
        and upgrade["package_sha256"]=={"previous":BASELINE_SHA256,"current":package_sha}
        and upgrade["original_packages_unmodified"] is True and upgrade["human_listening"] is False,"Upgrade identity differs")
    smoke=read(reports/"voice-smoke-acceptance.json"); quick=prefix_plan(plan)
    require(smoke["status"]=="passed" and smoke["cases"]==list(PREFIX_CASES) and smoke["prefix_plan_sha256"]==hashlib.sha256(quick.encode()).hexdigest()
        and smoke["original_project_is_unmodified"] is True and smoke["game_copies_and_save_directories_are_separate"] is True and len(smoke["iterations"])==2,"Quick checks differ")
    for i,s in enumerate(smoke["iterations"],1):
        require((s["cases"],s["assertions"],s["screenshots_checked"])==(6,103,29)
            and all(s[k]==0 for k in ("failed","xfailed","xpassed","skipped","not_run")),"Quick suite incomplete")
        validate_native_report((reports/f"source-voice-smoke-prefix-{i}.txt").read_text(encoding="utf-8-sig"),quick)
    voice_sha=digest(ROOT/"docs/evidence/voice-qwen-generation.json")
    require(voice_sha=="5180a9ca16c7a01f502350dcdfadf073da06edcb9b054350d7fdec8c3af7336a","Voice evidence differs")
    baseline=read(reports/"save-name-baseline.json")
    require(baseline["previous_version"]==BASELINE_VERSION and baseline["package_sha256"]==BASELINE_SHA256 and baseline["baseline_is_not_distributed"] is True,"Save-name baseline differs")
    context=read(reports/"ci-context.json")
    require(context=={"commit":candidate,"run_id":str(run_id),"version":version,"audio_driver":"dummy"},"CI context differs")
    preview=dist/f"BeforeTheRainStops-{version}-preview.png"
    preview_shot=next(x for x in shots if x["scope"]=="standalone" and x["name"]=="native-main-menu")
    require(digest(preview)==preview_shot["sha256"],"Preview differs")
    m={"schema_version":1,"status":"technical_passed_visual_pending","version":version,"candidate_commit":candidate,
        "candidate_tree":subprocess.check_output(["git","rev-parse","HEAD^{tree}"],cwd=ROOT,text=True).strip(),
        "run_id":run_id,"engine":"RenPy 8.5.3.26051504","ci_context":context,"suites":suites,"package":pkg,
        "screenshots_count":len(shots),"screenshots":shots,"upgrade":upgrade,"compatibility_baseline":baseline,"voice_smoke":smoke,
        "display":read(reports/"display.json"),"voice_upgrade":{"engine":"Qwen3-TTS 1.7B CustomVoice","speaker":"Serena","recordings":17,
            "generation_sha256":voice_sha,"human_listening":False,"all_recording_bytes_unchanged":True},
        "extras":{"images":5,"music_tracks":3,"unlock_source":"native seen-image and seen-audio persistence",
            "locked_content_hides_titles_and_images":True,"story_state_unchanged_by_gallery":True,
            "music_controls":"play/previous/next/pause/stop/real slider/real mute; stop on leave or Start",
            "music_progress_and_current_title_status":"passed",
            "fresh_process_and_previous_v110_seen_records":"passed"},
        "human_pending":["ordinary_windows","display_dpi","listening","creative_and_freeze","reading_time"],
        "human_acceptance_is_not_claimed":True,"unresolved_machine_issues":[],
        "audit_execution":"Independent package/report audit executed on the Windows runner after all native suites",
        "limits":"Dummy audio; ordinary hardware, Chinese paths, DPI, human listening, reading time and creative finalization remain pending. Old saves cover two representative positions. No Linux UI pass is claimed. New direct image review uses full-resolution JPEG inspection copies bound to original PNG SHA-256."}
    prior_path=ROOT/"docs/evidence/v11-visual-review.json"; prior=read(prior_path)["inspected"]
    old={(x["scope"],x["name"]):x for x in prior}
    planned=[(x["scope"],x["name"]) for x in prior]
    planned += [("standalone",n) for n in required_screenshots(plan) if "-extras-" in n]
    planned += [("fresh_process","native-extras-music-persistent"),("upgrade_reader","native-extras-music-persistent")]
    planned=list(dict.fromkeys(planned))
    require(len(planned)==58,"Visual plan differs")
    items=[];media=[]
    for scope,name in planned:
        shot=next(x for x in shots if x["scope"]==scope and x["name"]==name)
        item=dict(shot); previous=old.get((scope,name))
        if previous and previous["sha256"]==shot["sha256"]:
            item.update({"status":"reuse_candidate","review_method":"exact original PNG SHA-256 match with accepted v1.1.0 visual record",
                "prior_review_file":"docs/evidence/v11-visual-review.json","prior_review_sha256":digest(prior_path),
                "prior_record":{k:previous[k] for k in ("name","scope","path","sha256","review_method","finding")},"finding":previous["finding"]})
        else:
            item.update({"status":"needs_direct_view","review_method":"direct AI inspection of full-resolution JPEG copy from the current original PNG",
                "finding":"","inspection_copy":{"format":"JPEG","quality":95,"pixels":shot["pixels"],"source_png_sha256":shot["sha256"]}})
            with Image.open(ROOT/shot["path"]) as im:
                im.load();buf=io.BytesIO();im.convert("RGB").save(buf,format="JPEG",quality=95,subsampling=0)
            raw=buf.getvalue(); item["inspection_copy"]["sha256"]=hashlib.sha256(raw).hexdigest()
            media.append({"scope":scope,"name":name,"source_png_sha256":shot["sha256"],"jpeg_sha256":hashlib.sha256(raw).hexdigest(),
                "pixels":shot["pixels"],"base64":base64.b64encode(raw).decode("ascii")})
        items.append(item)
    data={"machine":m,"visual":{"version":version,"candidate_commit":candidate,"run_id":run_id,"inspected":items},"media":media}
    blob=json.dumps(data,ensure_ascii=True,separators=(",",":")).encode("ascii")
    (reports/"remote-audit.json").write_bytes(blob)
    transport=write_bundles(data,reports/"remote-review")
    print("Sealed Windows review:",hashlib.sha256(blob).hexdigest(),len(blob),"bytes;",
        len(transport["groups"]),"inspection groups; each base64 log payload <=",
        transport["payload_limit"],"bytes. Full payloads are exported by separate review jobs.",flush=True)

if __name__=="__main__":main()
