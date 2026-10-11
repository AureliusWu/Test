import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {get, waitNative, clickId, startNarrative, visibleNarration} from './pwa-native-browser.mjs';

const target = new URL(process.env.PWA_TARGET_URL || 'https://aureliuswu.github.io/Rain/');
const expectedVersion = (await fs.readFile('VERSION','utf8')).trim();
const expectedRevision = process.env.PWA_EXPECTED_REVISION;
assert.ok(expectedRevision,'PWA_EXPECTED_REVISION must identify the exact tested build');
const require = createRequire(import.meta.url);
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const launch = {headless:true,args:['--enable-webgl','--use-gl=angle','--use-angle=swiftshader']};
if(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE) launch.executablePath=process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;
const browser = await chromium.launch(launch);
const reportDirectory = path.resolve('reports/public-pwa');
await fs.mkdir(reportDirectory,{recursive:true});
const checks=[];
const errors=[];
try {
    const context=await browser.newContext({viewport:{width:1440,height:900}});
    const page=await context.newPage();
    page.on('pageerror',error=>errors.push(error.message));
    async function boot() {
        const start=performance.now();
        await page.goto(target.href,{waitUntil:'domcontentloaded'});
        await page.waitForFunction(()=>!document.getElementById('presplash'),null,{timeout:120000});
        await page.waitForFunction(()=>window.rainOfflineReady===true,null,{timeout:120000});
        await waitNative(page,'bool(renpy.get_screen("main_menu"))');
        await waitNative(page,'not any(renpy.get_ongoing_transition(layer) for layer in (None, "master", "screens"))');
        assert.equal(await get(page,'config.version'),expectedVersion);
        assert.equal(await page.evaluate(()=>window.rainOfflineRevision),expectedRevision);
        const owner=await page.evaluate(async()=>{
            const registration=await navigator.serviceWorker.getRegistration(new URL('./',location.href).href);
            return {scope:registration?.scope,script:registration?.active?.scriptURL,controller:navigator.serviceWorker.controller?.scriptURL};
        });
        const directory=new URL('./',target.href).href;
        assert.equal(owner.scope,directory);
        assert.equal(owner.script,new URL('service-worker.js',directory).href);
        assert.equal(owner.controller,owner.script);
        return Math.round(performance.now()-start);
    }
    const onlineMilliseconds=await boot();
    checks.push('public native menu, exact platform version/revision and own worker scope');
    await page.screenshot({path:path.join(reportDirectory,'public-main-menu.png')});
    await startNarrative(page);
    assert.equal(await get(page,'current_scene'),'p00_entry');
    await clickId(page,'quick_menu','save_open');
    await clickId(page,'save','slot_1');
    await waitNative(page,'renpy.can_load("1-1")');
    await clickId(page,'save','game_return');
    const savedScene=await get(page,'current_scene');
    const savedText=await get(page,visibleNarration);
    checks.push('actual public Start and native Save slot 1');
    await context.setOffline(true);
    const offlineSamples=[];
    for(let iteration=0;iteration<3;iteration++) offlineSamples.push(await boot());
    const offlineMilliseconds=[...offlineSamples].sort((a,b)=>a-b)[1];
    assert.equal(await get(page,'renpy.can_load("1-1")'),true);
    await clickId(page,'main_menu','load_open');
    await clickId(page,'load','slot_1');
    if(await get(page,'bool(renpy.get_screen("confirm"))')) await clickId(page,'confirm','confirm_yes');
    await waitNative(page,`current_scene == ${JSON.stringify(savedScene)}`);
    await waitNative(page,`${visibleNarration} == ${JSON.stringify(savedText)}`);
    await page.screenshot({path:path.join(reportDirectory,'public-offline-load.png')});
    checks.push('disconnected public reopen, native Load and preserved saved scene');
    assert.deepEqual(errors,[]);
    const report={status:'passed',target:target.href,version:expectedVersion,revision:expectedRevision,
        checks,online_milliseconds:onlineMilliseconds,offline_milliseconds:offlineMilliseconds,offline_samples_milliseconds:offlineSamples,
        exact_tested_artifact:true,errors,human_physical_device:false};
    await fs.writeFile(path.join(reportDirectory,'acceptance.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report,null,2));
    await context.close();
} finally {await browser.close();}
